import os
import warnings
from dataclasses import dataclass
from glob import glob
from time import perf_counter_ns
from typing import Tuple

import dask
import dask.array as da
import numpy as np
import psutil
from astropy.io import fits
from astropy.nddata import block_reduce
from astropy.wcs import WCS, FITSFixedWarning
from xarray import Dataset, open_zarr

from carta_backend import proto as CARTA
from carta_backend.config.config import TILE_SHAPE
from carta_backend.file.utils import (get_file_type, get_header_from_xradio,
                                      load_data)
from carta_backend.log import logger
from carta_backend.tile import layer_to_mip

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


@dataclass
class FileData:
    data: np.ndarray | da.Array | Dataset
    header: fits.Header
    wcs: WCS
    file_type: int
    hdu_index: int
    img_shape: Tuple[int, int]
    memmap: np.ndarray | Dataset | None
    hist_on: bool
    data_size: float  # Unit: MiB
    frame_size: float  # Unit: MiB


class FileManager:
    def __init__(self, client=None):
        self.files = {}
        self.cache = {}
        self.client = client

    async def open(self, file_id, file_path, hdu_index=None):
        if file_id in self.files:
            clog.error(f"File ID '{file_id}' already exists.")
            return None

        file_type = get_file_type(file_path)

        if file_type == CARTA.FileType.FITS:
            filedata = get_fits_FileData(file_id, file_path, hdu_index)
        elif file_type == CARTA.FileType.CASA:
            filedata = await get_zarr_FileData(file_id, file_path, self.client)

        self.files[file_id] = filedata

    def get(self, file_id):
        """Retrieve an opened file's data and header."""
        if file_id not in self.files:
            clog.error(f"File ID '{file_id}' not found.")
            return None
        return self.files[file_id]

    async def get_slice(self, file_id, channel, stokes, time=0,
                        layer=None, mip=1, coarsen_func="nanmean",
                        use_memmap=False):
        # Convert layer to mip
        if layer is not None:
            mip = layer_to_mip(
                layer,
                image_shape=self.files[file_id].img_shape,
                tile_shape=TILE_SHAPE)

        # Generate names
        name = f"{file_id}_{channel}_{stokes}_{time}_{mip}"
        frame_name = f"{file_id}_{channel}_{stokes}_{time}"
        clog.debug(f"Getting slice for {name}")

        clog.debug(f"Cache keys: {list(self.cache.keys())}")

        # Check cache
        if name in list(self.cache.keys()):
            clog.debug(f"Using cached data for {name}")
            return self.cache[name]
        else:
            # This means that the user is viewing another channel/stokes
            # so we can clear the cache of previous channel/stokes
            for key in list(self.cache.keys()):
                if not key.startswith(frame_name) and channel is not None:
                    clog.debug(f"Clearing cache for {key}")
                    del self.cache[key]

        # If the frame size is less than half of the available memory,
        # load the full frame into memory
        frame_size = self.files[file_id].frame_size
        available_mem = psutil.virtual_memory().available / 1024**2

        if isinstance(channel, int) and (frame_size <= (available_mem * 0.5)):
            use_memmap = True

        full_frame_name = f"{file_id}_{channel}_{stokes}_{time}_1"

        # Check cache
        if full_frame_name in list(self.cache.keys()):
            clog.debug(f"Using cached data for {full_frame_name}")
            data = self.cache[full_frame_name]
        else:
            if use_memmap:
                data = self.files[file_id].memmap
            else:
                data = self.files[file_id].data

            wcs = self.files[file_id].wcs
            data = load_data(data, channel, stokes, time, wcs)

        # Coarsen
        if mip > 1:
            if isinstance(data, da.Array):
                data = da.coarsen(
                    getattr(da, coarsen_func),
                    data,
                    {0: mip, 1: mip},
                    trim_excess=True)
            elif isinstance(data, np.ndarray):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    data = block_reduce(
                        data, (mip, mip), getattr(np, coarsen_func))
        else:
            if isinstance(data, np.ndarray) and use_memmap:
                data = data[:]

        # Convert to float32 to avoid using dtype >f4
        if isinstance(data, np.ndarray):
            data = data.astype("float32")

        # Load data into memory
        if use_memmap and isinstance(data, da.Array):
            data = await self.client.compute(data)

        # Cache data
        self.cache[name] = data
        return data

    def close(self, file_id):
        """Remove a file from the manager."""
        if file_id in self.files:
            clog.debug(f"Closing file ID '{file_id}'.")
            if hasattr(self.files[file_id].data, "close"):
                self.files[file_id].data.close()
            del self.files[file_id]
            # Clear cache
            for key in list(self.cache.keys()):
                if key.startswith(str(file_id)):
                    del self.cache[key]
        elif file_id == -1:
            for file_id in list(self.files.keys()):
                clog.debug(f"Closing file ID '{file_id}'.")
                if hasattr(self.files[file_id].data, "close"):
                    self.files[file_id].data.close()
                del self.files[file_id]
                # Clear cache
                for key in list(self.cache.keys()):
                    if key.startswith(str(file_id)):
                        del self.cache[key]
        else:
            clog.debug(f"File ID '{file_id}' not found.")

    def clear(self):
        """Remove all managed files."""
        self.files.clear()
        self.cache.clear()


@dask.delayed
def mmap_load_chunk(filename, shape, dtype, offset, sl):
    """
    Memory map the given file with overall shape and dtype and return a slice
    specified by :code:`sl`.

    Parameters
    ----------
    filename : str
    shape : tuple
        Total shape of the data in the file
    dtype:
        NumPy dtype of the data in the file
    offset : int
        Skip :code:`offset` bytes from the beginning of the file.
    sl:
        Object that can be used for indexing or slicing a NumPy array to
        extract a chunk

    Returns
    -------
    numpy.memmap or numpy.ndarray
        View into memory map created by indexing with :code:`sl`,
        or NumPy ndarray in case no view can be created using :code:`sl`.
    """
    data = np.memmap(filename, mode='r', shape=shape,
                     dtype=dtype, offset=offset)
    return data[sl]


def mmap_dask_array(filename, shape, dtype, offset=0, chunks="auto"):
    # Create a sample array to get the default chunking
    sample_array = da.empty(shape, dtype=dtype, chunks=chunks)
    chunks = sample_array.chunks

    # Special case for 0-dimensional arrays
    if len(shape) == 0:
        delayed_chunk = mmap_load_chunk(filename, shape, dtype, offset, ())
        return da.from_delayed(delayed_chunk, shape=(), dtype=dtype)

    # Calculate the chunk indices for each dimension
    chunk_indices = []
    for dim_chunks in chunks:
        indices = []
        start = 0
        for size in dim_chunks:
            indices.append((start, start + size))
            start += size
        chunk_indices.append(indices)

    # Function to build a block at specific chunk indices
    def build_block(idx_tuple):
        # Create slices from the chunk indices
        slices = tuple(slice(start, stop) for start, stop in idx_tuple)

        # Calculate the shape of this chunk
        chunk_shape = tuple(stop - start for start, stop in idx_tuple)

        # Create a delayed chunk
        delayed_chunk = mmap_load_chunk(filename, shape, dtype, offset, slices)

        # Create a dask array from the delayed chunk
        return da.from_delayed(delayed_chunk, shape=chunk_shape, dtype=dtype)

    # Create a nested list structure that matches the dimensionality of chunks
    # This is a recursive function to handle any number of dimensions
    def create_nested_blocks(dimension=0, indices=()):
        if dimension == len(chunks):
            # We've reached the right depth, build the block
            return build_block(indices)
        else:
            # Create a list of blocks for this dimension
            blocks_in_dim = []
            for idx in chunk_indices[dimension]:
                new_indices = indices + (idx,)
                blocks_in_dim.append(
                    create_nested_blocks(dimension + 1, new_indices))
            return blocks_in_dim

    # Create the nested structure of blocks
    nested_blocks = create_nested_blocks()

    # Combine all blocks using da.block
    return da.block(nested_blocks)


def get_fits_FileData(file_id, file_path, hdu_index):
    t0 = perf_counter_ns()

    # Read file information
    with fits.open(file_path, memmap=True) as hdul:
        hdu = hdul[hdu_index]
        dtype = np.dtype(hdu.data.dtype)
        shape = hdu.data.shape
        offset = hdu._data_offset
        header = hdu.header

    dt = (perf_counter_ns() - t0) / 1e6
    msg = f"Read file info in {dt:.3f} ms"
    clog.debug(msg)

    t0 = perf_counter_ns()

    # Read file as dask array
    data = mmap_dask_array(
        filename=file_path,
        shape=shape,
        dtype=dtype,
        offset=offset,
        chunks="auto",
    )
    dt = (perf_counter_ns() - t0) / 1e6
    msg = f"Create dask array in {dt:.3f} ms"
    clog.debug(msg)
    t0 = perf_counter_ns()

    # Get and set image information
    wcs = WCS(header, fix=False)
    header["PIX_AREA"] = np.abs(np.linalg.det(
        wcs.celestial.pixel_scale_matrix))
    img_shape = shape[-2:]
    data_size = data.nbytes / 1024**2
    frame_size = data_size / np.prod(data.shape[:-2])

    clog.debug(f"File ID '{file_id}' opened successfully")
    clog.debug(
        f"File dimensions: {shape}, "
        f"chunking: {str(data.chunksize)}")

    memmap = fits.getdata(file_path, hdu_index, memmap=True)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        wcs = WCS(header)

    header["PIX_AREA"] = np.abs(
        np.linalg.det(wcs.celestial.pixel_scale_matrix))

    filedata = FileData(
        data=data,
        header=header,
        wcs=wcs,
        file_type=CARTA.FileType.FITS,
        hdu_index=hdu_index,
        img_shape=img_shape,
        memmap=memmap,
        hist_on=False,
        data_size=data_size,
        frame_size=frame_size,
    )
    return filedata


async def get_zarr_FileData(file_id, file_path, client=None):
    # Read zarr
    data = open_zarr(file_path, chunks="auto")

    # Get header
    header = await get_header_from_xradio(data, client)
    img_shape = [data.sizes['m'], data.sizes['l']]

    # Log file information in separate parts to avoid
    # formatting conflicts
    clog.debug(f"File ID '{file_id}' opened successfully")
    clog.debug(
        f"File dimensions: time={data.sizes.get('time', 'N/A')}, "
        f"frequency={data.sizes.get('frequency', 'N/A')}, "
        f"polarization={data.sizes.get('polarization', 'N/A')}, "
        f"l={data.sizes.get('l', 'N/A')}, "
        f"m={data.sizes.get('m', 'N/A')}")
    clog.debug(f"Chunking: {str(data.SKY.data.chunksize)}")

    # Get unchunked data
    if not zarr_is_chunked(file_path):
        # If zarr is not chunked, read it as a single chunk
        memmap = open_zarr(file_path, chunks=None)
    else:
        memmap = data

    data_size = data.SKY.nbytes / 1024**2
    factor = 1
    for k, v in data.SKY.sizes.items():
        if k not in ["l", "m"]:
            factor *= v
    frame_size = data_size / factor

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        wcs = WCS(header)

    filedata = FileData(
        data=data,
        header=header,
        wcs=wcs,
        file_type=CARTA.FileType.CASA,
        hdu_index=None,
        img_shape=img_shape,
        memmap=memmap,
        hist_on=False,
        data_size=data_size,
        frame_size=frame_size,
    )
    return filedata


def zarr_is_chunked(file):
    chunks = glob(os.path.join(file, "SKY", "*"))
    return len(chunks) > 0
