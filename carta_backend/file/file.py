import asyncio
import warnings
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Dict, List, Tuple

import dask.array as da
import numpy as np
import psutil
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from xarray import Dataset, open_zarr

from carta_backend import proto as CARTA
from carta_backend.config.config import TILE_SHAPE
from carta_backend.file.utils import (
    async_read_zarr_channel,
    async_read_zarr_slice,
    block_reduce_numba,
    get_axes_dict,
    get_file_type,
    get_fits_dask_channels_chunks,
    get_header_from_xradio,
    load_data,
    mmap_dask_array,
)
from carta_backend.log import logger
from carta_backend.region.utils import numba_stats_2d
from carta_backend.tile import layer_to_mip

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


@dataclass
class FileData:
    # File path
    file_path: Path
    # for Dask
    data: da.Array | Dataset
    # for creating memmap
    memmap_info: Dict[str, Any] | None
    # for FITS image channels
    dask_channels: da.Array | None
    # FITS header for FITS and Zarr
    header: fits.Header
    # WCS for FITS and Zarr
    wcs: WCS
    # 0: CASA (currently Zarr instead), 3: FITS
    file_type: int
    # HDU index for FITS
    hdu_index: int
    # Image shape
    img_shape: Tuple[int, int]
    # Dict of sizes of each axis with xradio style keys
    sizes: Dict[str, int]
    # Total size of the file/HDU in MiB
    data_size_mib: float
    # Size of the frame in MiB
    frame_size_mib: float
    # Event to signal when histogram is ready
    hist_event: asyncio.Event
    # Spatial requirements
    spat_req: Dict[str, Dict[str, int | None]]
    # Cursor coordinates
    cursor_coords: List[int | None]
    # Dict of axes with xradio style keys
    axes_dict: Dict[str, int] | None
    # Current channel
    channel: int = 0
    # Current stokes
    stokes: int = 0
    # Current time
    time: int = 0


class FileManager:
    def __init__(self, client=None):
        self.files = {}
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

    async def async_get_channel(
        self,
        file_id: str,
        channel: int,
        stokes: int,
        time: int = 0,
    ):
        # Generate names
        name = f"{file_id}_{channel}_{stokes}_{time}_1"
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
                if not key.startswith(name[:-2]):
                    clog.debug(f"Clearing channel cache for {key}")
                    del self.channel_cache[key]

        # If the frame size is less than half of the available memory,
        # load the full frame into memory
        frame_size_mib = self.files[file_id].frame_size_mib
        if frame_size_mib > (self.avail_mem * 0.25):
            use_dask = True
        else:
            use_dask = False

        # Load data
        file_type = self.files[file_id].file_type
        wcs = self.files[file_id].wcs

        if use_dask:
            # Can be FITS or Zarr
            clog.debug("Using dask to load channel")
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
                memmap_info = self.files[file_id].memmap_info
                _data = np.memmap(**memmap_info)
                data = await asyncio.to_thread(
                    load_data,
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
                data = await async_read_zarr_channel(
                    file_path=file_path,
                    time=time,
                    channel=channel,
                    stokes=stokes,
                )

        # Convert to float32 to avoid using dtype >f4
        t0 = perf_counter_ns()

        if isinstance(data, np.ndarray):
            if data.dtype != np.float32:
                data = data.astype(np.float32, copy=False)
                dt = (perf_counter_ns() - t0) / 1e6
                msg = f"Converted to float32 in {dt:.3f} ms"
                clog.debug(msg)
        else:
            data = data.astype(np.float32, copy=False)

        # Cache data (including dask array)
        self.channel_cache[name] = data
        return data

    async def async_get_channel_mip(
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

        if mip <= 1:
            return await self.async_get_channel(
                file_id=file_id,
                channel=channel,
                stokes=stokes,
                time=time,
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
            data = await self.async_get_channel(
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
                data = await asyncio.to_thread(block_reduce_numba, data, mip)

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

    async def async_get_slice(
        self,
        file_id: str,
        x: int | slice | None = None,
        y: int | slice | None = None,
        channel: int | slice | None = None,
        stokes: int = 0,
        time: int = 0,
        memmap: np.memmap | None = None,
        dtype: np.dtype | None = None,
        semaphore: asyncio.Semaphore | None = None,
        max_workers: int = 4,
        n_jobs: int = 4,
        use_dask: bool = False,
        return_future: bool = False,
    ):
        file_type = self.files[file_id].file_type
        wcs = self.files[file_id].wcs
        full_channel_size = self.files[file_id].sizes["frequency"]

        if x is None:
            x = slice(None)
        if y is None:
            y = slice(None)
        if channel is None:
            channel = slice(0, full_channel_size)

        if semaphore is None:
            semaphore = asyncio.Semaphore(max_workers)

        if use_dask:
            data = load_data(
                data=self.files[file_id].data,
                x=x,
                y=y,
                channel=channel,
                stokes=stokes,
                time=time,
                dtype=dtype,
                wcs=wcs,
            )
            if not return_future:
                data = await self.client.compute(data)
            return data

        if file_type == CARTA.FileType.FITS:
            if memmap is None:
                memmap_info = self.files[file_id].memmap_info
                memmap = np.memmap(**memmap_info)

            if channel.start is None:
                start = 0
            else:
                start = channel.start
            if channel.stop is None:
                stop = full_channel_size
            else:
                stop = channel.stop
            channel_size = stop - start

            async def load_chunk(i):
                ichannel = slice(
                    start + i * channel_size // n_jobs,
                    start + (i + 1) * channel_size // n_jobs,
                )
                async with semaphore:
                    return await asyncio.to_thread(
                        load_data,
                        data=memmap,
                        x=x,
                        y=y,
                        channel=ichannel,
                        stokes=stokes,
                        wcs=wcs,
                        dtype=dtype,
                    )

            tasks = [load_chunk(i) for i in range(n_jobs)]
            results = await asyncio.gather(*tasks)
            data = np.concatenate(results, axis=0)
        elif file_type == CARTA.FileType.CASA:
            file_path = self.files[file_id].file_path
            data = await async_read_zarr_slice(
                file_path=file_path,
                time=time,
                channel=channel,
                stokes=stokes,
                x=x,
                y=y,
                dtype=dtype,
                semaphore=semaphore,
            )
        return data

    async def async_get_point_spectrum(
        self,
        file_id: str,
        x: int,
        y: int,
        channel: slice | None,
        stokes: int,
        time: int = 0,
        memmap: np.memmap | None = None,
        dtype: np.dtype | None = None,
        semaphore: asyncio.Semaphore | None = None,
        max_workers: int = 4,
        n_jobs: int = 4,
        use_dask: bool = False,
    ):
        # Load data
        file_type = self.files[file_id].file_type
        wcs = self.files[file_id].wcs
        full_channel_size = self.files[file_id].sizes["frequency"]

        if semaphore is None:
            semaphore = asyncio.Semaphore(max_workers)

        if use_dask:
            data = load_data(
                data=self.files[file_id].data,
                x=x,
                y=y,
                channel=channel,
                stokes=stokes,
                time=time,
                dtype=dtype,
                wcs=wcs,
            )
            data = await self.client.compute(data)
            return data

        if file_type == CARTA.FileType.FITS:
            if memmap is None:
                memmap_info = self.files[file_id].memmap_info
                memmap = np.memmap(**memmap_info)

            if channel is None:
                channel = slice(0, full_channel_size)
            if channel.start is None:
                start = 0
            else:
                start = channel.start
            if channel.stop is None:
                stop = full_channel_size
            else:
                stop = channel.stop
            channel_size = stop - start

            async def load_chunk(i):
                ichannel = slice(
                    start + i * channel_size // n_jobs,
                    start + (i + 1) * channel_size // n_jobs,
                )
                async with semaphore:
                    return await asyncio.to_thread(
                        load_data,
                        data=memmap,
                        x=x,
                        y=y,
                        channel=ichannel,
                        stokes=stokes,
                        wcs=wcs,
                        dtype=dtype,
                    )

            tasks = [load_chunk(i) for i in range(n_jobs)]
            results = await asyncio.gather(*tasks)
            data = np.concatenate(results, axis=0)
        elif file_type == CARTA.FileType.CASA:
            file_path = self.files[file_id].file_path
            data = await async_read_zarr_slice(
                file_path=file_path,
                time=time,
                channel=channel,
                stokes=stokes,
                x=x,
                y=y,
                dtype=dtype,
                semaphore=semaphore,
            )
        return data

    async def async_get_region_spectrum(
        self,
        file_id: str,
        sub_mask: np.ndarray,
        x: int | slice | None,
        y: int | slice | None,
        channel: int | slice | None,
        stokes: int = 0,
        time: int = 0,
        memmap: np.memmap | None = None,
        dtype: np.dtype | None = None,
        semaphore: asyncio.Semaphore | None = None,
        max_workers: int = 4,
        n_jobs: int = 4,
        use_dask: bool = False,
    ):
        hdr = self.files[file_id].header
        try:
            bmaj, bmin, pix_area = hdr["BMAJ"], hdr["BMIN"], hdr["PIX_AREA"]
            beam_area = np.pi * bmaj * bmin / (4 * np.log(2)) / pix_area
        except KeyError:
            clog.warning("Beam area not found in header, using 1.")
            beam_area = 1

        data = await self.async_get_slice(
            file_id=file_id,
            x=x,
            y=y,
            channel=channel,
            stokes=stokes,
            time=time,
            memmap=memmap,
            dtype=dtype,
            semaphore=semaphore,
            max_workers=max_workers,
            n_jobs=n_jobs,
            use_dask=use_dask,
        )

        def _get_stats(data):
            data = data[:, sub_mask.astype(bool)]
            if dtype == np.float32:
                data = data.astype(np.float64, copy=False)
            stats = numba_stats_2d(data, beam_area)
            return stats

        stats = await asyncio.to_thread(_get_stats, data)
        return stats

    def _clear_cache(self, cache_dict, file_id):
        for key in list(cache_dict.keys()):
            if key.startswith(str(file_id)):
                del cache_dict[key]

    def close(self, file_id):
        """Remove a file from the manager."""
        if file_id in self.files:
            clog.debug(f"Closing file ID '{file_id}'.")
            if hasattr(self.files[file_id].data, "close"):
                self.files[file_id].data.close()
            del self.files[file_id]
            # Clear cache
            self._clear_cache(self.channel_cache, file_id)
        elif file_id == -1:
            for file_id in list(self.files.keys()):
                clog.debug(f"Closing file ID '{file_id}'.")
                if hasattr(self.files[file_id].data, "close"):
                    self.files[file_id].data.close()
                del self.files[file_id]
                # Clear cache
                self._clear_cache(self.channel_cache, file_id)
        else:
            clog.debug(f"File ID '{file_id}' not found.")

    def clear(self):
        """Remove all managed files."""
        self.files.clear()
        self.channel_cache.clear()


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

    # Get sizes
    axes_dict = get_axes_dict(header)
    sizes = {
        "l": shape[-axes_dict["RA"] - 1],
        "m": shape[-axes_dict["DEC"] - 1],
        "frequency": shape[-axes_dict["FREQ"] - 1]
        if "FREQ" in axes_dict
        else None,
        "stokes": shape[-axes_dict["STOKES"] - 1]
        if "STOKES" in axes_dict
        else None,
        "time": shape[-axes_dict["TIME"] - 1] if "TIME" in axes_dict else None,
    }

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
    data_size_mib = data.nbytes / 1024**2
    frame_size_mib = data_size_mib / np.prod(data.shape[:-2])

    clog.debug(f"File ID '{file_id}' opened successfully")
    clog.debug(f"File dimensions: {shape}, chunking: {str(data.chunksize)}")

    memmap_info = {
        "filename": file_path,
        "dtype": dtype,
        "mode": "r",
        "shape": shape,
        "offset": offset,
    }

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
        sizes=sizes,
        memmap_info=memmap_info,
        hist_event=asyncio.Event(),
        data_size_mib=data_size_mib,
        frame_size_mib=frame_size_mib,
        spat_req={
            "x": {"start": 0, "end": None, "mip": 1, "width": 0},
            "y": {"start": 0, "end": None, "mip": 1, "width": 0},
        },
        cursor_coords=[None, None, None],
        axes_dict=get_axes_dict(header),
    )
    return filedata


async def get_zarr_FileData(file_id, file_path, client=None):
    # Read zarr
    data = open_zarr(file_path, chunks="auto")

    # Get header
    header = await get_header_from_xradio(data, client)
    img_shape = [data.sizes["m"], data.sizes["l"]]

    # Get sizes
    sizes = {
        "l": data.sizes["l"],
        "m": data.sizes["m"],
        "frequency": data.sizes.get("frequency", None),
        "stokes": data.sizes.get("polarization", None),
        "time": data.sizes.get("time", None),
    }

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

    data_size_mib = data.SKY.nbytes / 1024**2
    factor = 1
    for k, v in data.SKY.sizes.items():
        if k not in ["l", "m"]:
            factor *= v
    frame_size_mib = data_size_mib / factor

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        wcs = WCS(header)

    filedata = FileData(
        file_path=Path(file_path),
        data=data,
        dask_channels=data,
        memmap_info=None,
        header=header,
        wcs=wcs,
        file_type=CARTA.FileType.CASA,
        hdu_index=None,
        img_shape=img_shape,
        sizes=sizes,
        hist_event=asyncio.Event(),
        data_size_mib=data_size_mib,
        frame_size_mib=frame_size_mib,
        spat_req={
            "x": {"start": 0, "end": None, "mip": 1, "width": 0},
            "y": {"start": 0, "end": None, "mip": 1, "width": 0},
        },
        cursor_coords=[None, None, None],
        axes_dict=get_axes_dict(header),
    )
    return filedata
