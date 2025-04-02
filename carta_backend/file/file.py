import astropy.io.fits as fits
import dask
import dask.array as da
import numpy as np
from astropy.wcs import WCS
from xarray import open_zarr

from carta_backend import proto as CARTA
from carta_backend.log import logger
from carta_backend.utils import (get_file_type, get_header_from_xradio,
                                 load_data)

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


class FileManager:
    def __init__(self):
        self.files = {}
        self.cache = {}

    def open(self, file_id, file_path, hdu_index=None):
        if file_id in self.files:
            clog.error(f"File ID '{file_id}' already exists.")
            return None

        file_type = get_file_type(file_path)

        if file_type == CARTA.FileType.FITS:
            # Use memmap to read the file
            with fits.open(file_path, memmap=True) as hdul:
                hdu = hdul[hdu_index]
                dtype = np.dtype(hdu.data.dtype)
                shape = hdu.data.shape
                offset = hdu._data_offset
                header = hdu.header
            data = mmap_dask_array(
                filename=file_path,
                shape=shape,
                dtype=dtype,
                offset=offset,
                chunks="auto",
            )
            wcs = WCS(header, fix=False)
            header["PIX_AREA"] = np.abs(np.linalg.det(
                wcs.celestial.pixel_scale_matrix))
        elif file_type == CARTA.FileType.CASA:
            # Currently zarr
            data = open_zarr(file_path)
            header = get_header_from_xradio(data)

        self.files[file_id] = (data, header, file_type, hdu_index)

    def get(self, file_id):
        """Retrieve an opened file's data and header."""
        if file_id not in self.files:
            clog.error(f"File ID '{file_id}' not found.")
            return None
        return self.files[file_id]

    def get_slice(self, file_id, channel, stokes, time=0):
        name = f"{file_id}_{channel}_{stokes}_{time}"
        if name in self.cache:
            return self.cache[name]
        else:
            # This means that the user is viewing another channel/stokes
            # so we can clear the cache of previous channel/stokes
            for key in list(self.cache.keys()):
                if key.startswith(str(file_id)):
                    del self.cache[key]

        data = self.files[file_id][0]
        data = load_data(data, channel, stokes, time)
        self.cache[name] = data
        return data

    def close(self, file_id):
        """Remove a file from the manager."""
        if file_id in self.files:
            clog.debug(f"Closing file ID '{file_id}'.")
            if hasattr(self.files[file_id][0], "close"):
                self.files[file_id][0].close()
            del self.files[file_id]
            # Clear cache
            for key in self.cache.keys():
                if key.startswith(file_id):
                    del self.cache[key]

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
