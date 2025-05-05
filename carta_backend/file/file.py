from dataclasses import dataclass
from time import perf_counter_ns
from typing import Tuple
from weakref import WeakValueDictionary

import astropy.io.fits as fits
import dask
import dask.array as da
import numpy as np
from astropy.nddata import block_reduce
from astropy.wcs import WCS
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
    frames: da.Array | None
    header: fits.Header
    file_type: int
    hdu_index: int
    img_shape: Tuple[int, int]
    memmap: np.ndarray | Dataset | None
    hist_on: bool
    data_size: float  # Unit: MiB
    frame_size: float  # Unit: MiB


class FileManager:
    def __init__(self):
        self.files = {}
        self.cache = WeakValueDictionary()

    def open(self, file_id, file_path, hdu_index=None, client=None):
        if file_id in self.files:
            clog.error(f"File ID '{file_id}' already exists.")
            return None

        file_type = get_file_type(file_path)

        if file_type == CARTA.FileType.FITS:
            filedata = get_fits_FileData(file_id, file_path, hdu_index)
        elif file_type == CARTA.FileType.CASA:
            filedata = get_zarr_FileData(file_id, file_path, client)

        self.files[file_id] = filedata

    def get(self, file_id):
        """Retrieve an opened file's data and header."""
        if file_id not in self.files:
            clog.error(f"File ID '{file_id}' not found.")
            return None
        return self.files[file_id]

    def get_slice(self, file_id, channel, stokes, time=0,
                  layer=None, mip=None, coarsen_func="nanmean",
                  client=None, use_memmap=False):
        if layer is not None:
            mip = layer_to_mip(
                layer,
                image_shape=self.files[file_id].img_shape,
                tile_shape=TILE_SHAPE)

        name = f"{file_id}_{channel}_{stokes}_{time}_{mip}"
        if name in self.cache:
            return self.cache[name]
        else:
            # This means that the user is viewing another channel/stokes/mip
            # so we can clear the cache of previous channel/stokes/mip
            for key in list(self.cache.keys()):
                if key.startswith(str(file_id)):
                    del self.cache[key]

        frame_size = self.files[file_id].frame_size

        if isinstance(channel, int):
            if frame_size <= 132.25:
                data = self.files[file_id].memmap
            else:
                data = self.files[file_id].frames
        else:
            data = self.files[file_id].data

        data = load_data(data, channel, stokes, time)

        if mip is not None and mip > 1:
            if isinstance(data, da.Array):
                data = da.coarsen(
                    getattr(da, coarsen_func),
                    data,
                    {0: mip, 1: mip},
                    trim_excess=True)
            elif isinstance(data, np.ndarray):
                data = block_reduce(
                    data, (mip, mip), getattr(np, coarsen_func))

        if isinstance(data, np.ndarray):
            data = data.astype("float32")

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
    """
    Create a Dask array from raw binary data in :code:`filename`
    by memory mapping.
    This method creates a dask array with the same chunking pattern as
    da.ones(shape, dtype=dtype), and works for arrays of any dimensionality.

    Parameters
    ----------
    filename : str
    shape : tuple
        Total shape of the data in the file
    dtype:
        NumPy dtype of the data in the file
    offset : int, optional
        Skip :code:`offset` bytes from the beginning of the file.
    chunks : int, tuple
        How to chunk the array

    Returns
    -------
    dask.array.Array
        Dask array matching :code:`shape` and :code:`dtype`, backed by
        memory-mapped chunks with the same chunking as
        da.ones(shape, dtype=dtype).
    """
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

    if data.ndim <= 2:
        chunks = "auto"
    elif data.ndim == 3:
        chunks = {0: 1, 1: 1, 2: "auto"}
    elif data.ndim == 4:
        chunks = {0: 1, 1: 1, 2: "auto", 3: "auto"}

    if (chunks != "auto") and (data_size > 132.25):
        t0 = perf_counter_ns()
        frames = mmap_dask_array(
            filename=file_path,
            shape=shape,
            dtype=dtype,
            offset=offset,
            chunks=chunks,
        )
        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Create dask frame array in {dt:.3f} ms "
        msg += f"with chunking: {frames.chunksize}"
        clog.debug(msg)
    else:
        frames = data

    memmap = fits.getdata(file_path, hdu_index, memmap=True)

    filedata = FileData(
        data=data,
        frames=frames,
        header=header,
        file_type=CARTA.FileType.FITS,
        hdu_index=hdu_index,
        img_shape=img_shape,
        memmap=memmap,
        hist_on=False,
        data_size=data_size,
        frame_size=frame_size,
    )
    return filedata


def get_zarr_FileData(file_id, file_path, client=None):
    # Currently zarr
    data = open_zarr(file_path)
    header = get_header_from_xradio(data, client)
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
    frames = data
    memmap = open_zarr(file_path, chunks=None)

    data_size = data.SKY.nbytes / 1024**2
    factor = 1
    for k, v in data.SKY.sizes.items():
        if k not in ["l", "m"]:
            factor *= v
    frame_size = data_size / factor

    filedata = FileData(
        data=data,
        frames=frames,
        header=header,
        file_type=CARTA.FileType.CASA,
        hdu_index=None,
        img_shape=img_shape,
        memmap=memmap,
        hist_on=False,
        data_size=data_size,
        frame_size=frame_size,
    )
    return filedata
