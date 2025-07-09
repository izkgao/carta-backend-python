import asyncio
import os
import warnings
from dataclasses import dataclass
from glob import glob
from pathlib import Path
from time import perf_counter_ns
from typing import Tuple

import dask.array as da
import numpy as np
import psutil
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from xarray import Dataset, open_zarr

from carta_backend import proto as CARTA
from carta_backend.config.config import TILE_SHAPE
from carta_backend.file.utils import (
    block_reduce_numba,
    get_file_type,
    get_fits_dask_channels_chunks,
    get_header_from_xradio,
    load_data,
    mmap_dask_array,
    read_zarr_slice,
)
from carta_backend.log import logger
from carta_backend.tile import layer_to_mip

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


@dataclass
class FileData:
    file_path: Path
    data: np.ndarray | da.Array | Dataset
    memmap: np.ndarray | Dataset | None
    dask_channels: da.Array | None
    header: fits.Header
    wcs: WCS
    file_type: int
    hdu_index: int
    img_shape: Tuple[int, int]
    hist_on: bool | asyncio.Event
    data_size: float  # Unit: MiB
    frame_size: float  # Unit: MiB


class FileManager:
    def __init__(self, client=None):
        self.files = {}
        self.cache = {}
        self.channel_cache = {}
        self.client = client

        self.avail_mem = (
            psutil.virtual_memory().available / 1024**2
        )  # Unit: MiB

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

    async def get_slice(
        self,
        file_id,
        channel,
        stokes,
        time=0,
        layer=None,
        mip=1,
        coarsen_func="nanmean",
        use_memmap=False,
    ):
        # Convert layer to mip
        if layer is not None:
            mip = layer_to_mip(
                layer,
                image_shape=self.files[file_id].img_shape,
                tile_shape=TILE_SHAPE,
            )

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

        if isinstance(channel, int) and (frame_size <= (self.avail_mem * 0.5)):
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
            data = load_data(
                data=data,
                x=None,
                y=None,
                channel=channel,
                stokes=stokes,
                time=time,
                wcs=wcs,
            )

        # Coarsen
        if mip > 1:
            if isinstance(data, da.Array):
                data = da.coarsen(
                    getattr(da, coarsen_func),
                    data,
                    {0: mip, 1: mip},
                    trim_excess=True,
                )
            elif isinstance(data, np.ndarray):
                data = block_reduce_numba(data, mip)
        else:
            if isinstance(data, np.ndarray) and use_memmap:
                data = data[:]

        # Convert to float32 to avoid using dtype >f4
        if isinstance(data, np.ndarray):
            data = data.astype(np.float32, copy=False)

        # Load data into memory
        if use_memmap and isinstance(data, da.Array):
            data = await self.client.compute(data)

        # Cache data
        self.cache[name] = data
        return data

    def get_channel(
        self,
        file_id: str,
        channel: int,
        stokes: int,
        time: int = 0,
    ):
        # Generate names
        name = f"{file_id}_{channel}_{stokes}_{time}"
        clog.debug(f"Channel cache keys: {list(self.channel_cache.keys())}")
        clog.debug(f"Getting channel for {name}")

        # Check cache
        if name in list(self.channel_cache.keys()):
            clog.debug(f"Using cached data for {name}")
            return self.channel_cache[name]
        else:
            # This means that the user is viewing another channel/stokes
            # so we can clear the channel cache of previous channel/stokes
            for key in list(self.channel_cache.keys()):
                if not key.startswith(name):
                    clog.debug(f"Clearing channel cache for {key}")
                    del self.channel_cache[key]

        # If the frame size is less than half of the available memory,
        # load the full frame into memory
        frame_size = self.files[file_id].frame_size
        if frame_size > (self.avail_mem * 0.5):
            use_dask = True
        else:
            use_dask = False

        # Load data
        file_type = self.files[file_id].file_type
        wcs = self.files[file_id].wcs

        if use_dask:
            # Can be FITS or Zarr
            _data = self.files[file_id].dask_channels
            data = load_data(
                data=_data,
                x=None,
                y=None,
                channel=channel,
                stokes=stokes,
                time=time,
                wcs=wcs,
            )
        else:
            if file_type == CARTA.FileType.FITS:
                _data = self.files[file_id].memmap
                data = load_data(
                    data=_data,
                    x=None,
                    y=None,
                    channel=channel,
                    stokes=stokes,
                    time=time,
                    wcs=wcs,
                )
            elif file_type == CARTA.FileType.CASA:
                file_path = self.files[file_id].file_path
                data = read_zarr_slice(
                    file_path=file_path,
                    time=time,
                    frequency=channel,
                    polarization=stokes,
                    max_workers=2,
                )

        # Convert to float32 to avoid using dtype >f4
        t0 = perf_counter_ns()
        data = data.astype(np.float32, copy=False)

        if isinstance(data, np.ndarray):
            dt = (perf_counter_ns() - t0) / 1e6
            msg = f"Converted to float32 in {dt:.3f} ms"
            clog.debug(msg)

        # Cache data (including dask array)
        self.channel_cache[name] = data
        return data

    def get_channel_mip(
        self,
        file_id: str,
        channel: int,
        stokes: int,
        time: int = 0,
        layer: int | None = None,
        mip: int = 1,
    ):
        # Convert layer to mip
        if layer is not None:
            mip = layer_to_mip(
                layer,
                image_shape=self.files[file_id].img_shape,
                tile_shape=TILE_SHAPE,
            )

        # Generate names
        name = f"{file_id}_{channel}_{stokes}_{time}_{mip}"
        clog.debug(f"Cache keys: {list(self.channel_cache.keys())}")
        clog.debug(f"Getting channel mip for {name}")

        # Check cache
        if name in list(self.channel_cache.keys()):
            clog.debug(f"Using cached data for {name}")
            return self.channel_cache[name]
        else:
            data = self.get_channel(
                file_id=file_id,
                channel=channel,
                stokes=stokes,
                time=time,
            )

        # Downsample data
        if mip > 1:
            if isinstance(data, da.Array):
                data = da.coarsen(
                    da.nanmean,
                    data,
                    {0: mip, 1: mip},
                    trim_excess=True,
                )
            else:
                data = block_reduce_numba(data, mip)

        # Cache data (including dask array)
        self.channel_cache[name] = data
        return data

    def get_all_tiles(
        self,
        file_id: str,
        channel: int,
        stokes: int,
        time: int = 0,
        layer=None,
        mip=1,
    ):
        # Convert layer to mip
        if layer is not None:
            mip = layer_to_mip(
                layer,
                image_shape=self.files[file_id].img_shape,
                tile_shape=TILE_SHAPE,
            )

        # If mip <= 1, return the full frame
        if mip <= 1:
            data = self.get_channel(
                file_id=file_id,
                channel=channel,
                stokes=stokes,
                time=time,
            )
            return data

        # Generate names
        name = f"{file_id}_{channel}_{stokes}_{time}_{mip}"
        frame_name = f"{file_id}_{channel}_{stokes}_{time}"
        clog.debug(f"Getting channel for {name}")
        clog.debug(f"Channel cache keys: {list(self.channel_cache.keys())}")

        # Check cache
        if name in list(self.channel_cache.keys()):
            clog.debug(f"Using cached channel for {name}")
            data = self.channel_cache[frame_name]
        else:
            data = self.get_channel(
                file_id=file_id,
                channel=channel,
                stokes=stokes,
                time=time,
            )

        # Coarsen
        if isinstance(data, da.Array):
            data = da.coarsen(
                da.nanmean,
                data,
                {0: mip, 1: mip},
                trim_excess=True,
            )
        elif isinstance(data, np.ndarray):
            data = block_reduce_numba(data, mip)

        # Convert to float32 to avoid using dtype >f4
        data = data.astype(np.float32, copy=False)

        return data

    def get_point_spectrum(self, file_id, x, y, channel, stokes, time=0):
        data = self.files[file_id].data
        wcs = self.files[file_id].wcs
        data = load_data(
            data=data,
            x=x,
            y=y,
            channel=channel,
            stokes=stokes,
            time=time,
            wcs=wcs,
        )
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


def get_fits_FileData(file_id, file_path, hdu_index):
    t0 = perf_counter_ns()

    # Read file information
    with fits.open(file_path, memmap=True, mode="denywrite") as hdul:
        hdu = hdul[hdu_index]
        dtype = np.dtype(hdu.data.dtype)
        shape = hdu.data.shape
        offset = hdu._data_offset
        header = hdu.header

    dt = (perf_counter_ns() - t0) / 1e6
    msg = f"Read file info in {dt:.3f} ms"
    clog.debug(msg)

    # Create WCS
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        wcs = WCS(header)

    # Create dask array
    t0 = perf_counter_ns()
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

    # Create dask channels
    t0 = perf_counter_ns()
    chunks = get_fits_dask_channels_chunks(wcs)
    dask_channels = mmap_dask_array(
        filename=file_path,
        shape=shape,
        dtype=dtype,
        offset=offset,
        chunks=chunks,
    )
    dt = (perf_counter_ns() - t0) / 1e6
    msg = f"Create dask channels array in {dt:.3f} ms"
    clog.debug(msg)

    # Get and set image information
    header["PIX_AREA"] = np.abs(
        np.linalg.det(wcs.celestial.pixel_scale_matrix)
    )
    img_shape = shape[-2:]
    data_size = data.nbytes / 1024**2
    frame_size = data_size / np.prod(data.shape[:-2])

    clog.debug(f"File ID '{file_id}' opened successfully")
    clog.debug(f"File dimensions: {shape}, chunking: {str(data.chunksize)}")

    # Create memmap
    memmap = np.memmap(
        file_path,
        mode="r",
        shape=shape,
        dtype=dtype,
        offset=offset,
    )

    # Create FileData
    filedata = FileData(
        file_path=Path(file_path),
        data=data,
        dask_channels=dask_channels,
        header=header,
        wcs=wcs,
        file_type=CARTA.FileType.FITS,
        hdu_index=hdu_index,
        img_shape=img_shape,
        memmap=memmap,
        hist_on=asyncio.Event(),
        data_size=data_size,
        frame_size=frame_size,
    )
    return filedata


async def get_zarr_FileData(file_id, file_path, client=None):
    # Read zarr
    data = open_zarr(file_path, chunks="auto")

    # Get header
    header = await get_header_from_xradio(data, client)
    img_shape = [data.sizes["m"], data.sizes["l"]]

    # Log file information in separate parts to avoid
    # formatting conflicts
    clog.debug(f"File ID '{file_id}' opened successfully")
    clog.debug(
        f"File dimensions: time={data.sizes.get('time', 'N/A')}, "
        f"frequency={data.sizes.get('frequency', 'N/A')}, "
        f"polarization={data.sizes.get('polarization', 'N/A')}, "
        f"l={data.sizes.get('l', 'N/A')}, "
        f"m={data.sizes.get('m', 'N/A')}"
    )
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
        file_path=Path(file_path),
        data=data,
        dask_channels=data,
        memmap=memmap,
        header=header,
        wcs=wcs,
        file_type=CARTA.FileType.CASA,
        hdu_index=None,
        img_shape=img_shape,
        hist_on=False,
        data_size=data_size,
        frame_size=frame_size,
    )
    return filedata


def zarr_is_chunked(file):
    chunks = glob(os.path.join(file, "SKY", "*"))
    return len(chunks) > 0
