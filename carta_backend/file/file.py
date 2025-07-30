import asyncio
import warnings
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from time import perf_counter_ns
from typing import Any, AsyncGenerator, Dict, List, Tuple

import dask.array as da
import numpy as np
import psutil
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from dask import delayed
from zarr.api.asynchronous import open_group
from zarr.core.array import AsyncArray

from carta_backend import proto as CARTA
from carta_backend.config.config import TILE_SHAPE
from carta_backend.file.utils import (
    async_load_data,
    async_read_zarr_channel,
    async_read_zarr_slice,
    block_reduce_numba,
    compute_slices,
    get_array_axes_dict,
    get_file_type,
    get_fits_dask_channels_chunks,
    get_header_from_zarr,
    mmap_dask_array,
)
from carta_backend.log import logger
from carta_backend.region.utils import numba_stats_2d
from carta_backend.tile.utils import (
    compute_tile,
    decode_tile_coord,
    get_tile_original_slice,
    get_tile_slice,
    layer_to_mip,
)
from carta_backend.utils.histogram import (
    get_block_hist,
    numba_combine_block_histograms,
)

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


@dataclass
class FileData:
    # File path
    file_path: Path
    # for Dask
    data: da.Array | AsyncArray
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
    # Event to signal when raster is ready
    raster_event: asyncio.Event
    # Spatial requirements
    spat_req: Dict[str, Dict[str, int | None]]
    # Cursor coordinates
    cursor_coords: List[int | None]
    # D
    array_axes_dict: Dict[str, int] | None
    # Current channel
    channel: int = 0
    # Current stokes
    stokes: int = 0
    # Current time
    time: int = 0
    # Use dask
    use_dask: bool = False


class FileManager:
    def __init__(self, client=None):
        self.files = {}
        self.channel_cache = {}
        self.tile_cache = {}
        self.client = client

        self.avail_mem = (
            psutil.virtual_memory().available / 1024**2
        )  # Unit: MiB

    async def open(self, file_id, file_path, hdu_index=None):
        if file_id in self.files:
            clog.error(f"File ID '{file_id}' already exists.")
            return None

        file_path = Path(file_path)

        file_type = get_file_type(file_path)

        if file_type == CARTA.FileType.FITS:
            filedata = get_fits_FileData(file_id, file_path, hdu_index)
        elif file_type == CARTA.FileType.CASA:
            filedata = await get_zarr_FileData(file_id, file_path)

        self.files[file_id] = filedata

    async def async_get_channel(
        self,
        file_id: str,
        channel: int,
        stokes: int,
        time: int = 0,
        memmap: np.memmap | None = None,
        dtype: np.dtype | None = None,
        semaphore: asyncio.Semaphore | None = None,
        max_workers: int = 4,
        use_dask: bool = False,
        return_future: bool = False,
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
            if not use_dask:
                clog.warning(
                    f"Frame size {frame_size_mib / 1024:.2f} GiB is greater "
                    f"than 25% of available memory {self.avail_mem / 1024:.2f} "
                    "GiB, falling back to use Dask as the compute backend for "
                    "this file."
                )
                use_dask = True

        self.files[file_id].use_dask = use_dask

        # Load data
        file_type = self.files[file_id].file_type
        array_axes_dict = self.files[file_id].array_axes_dict

        if use_dask:
            # Can be FITS or Zarr
            clog.debug("Using dask to load channel")
            _data = self.files[file_id].dask_channels
            data = await async_load_data(
                data=_data,
                array_axes_dict=array_axes_dict,
                x=None,
                y=None,
                channel=channel,
                stokes=stokes,
                time=time,
                dtype=dtype,
            )
        else:
            if file_type == CARTA.FileType.FITS:
                memmap_info = self.files[file_id].memmap_info
                data = await async_load_data(
                    data=memmap
                    if memmap is not None
                    else np.memmap(**memmap_info),
                    array_axes_dict=array_axes_dict,
                    x=None,
                    y=None,
                    channel=channel,
                    stokes=stokes,
                    time=time,
                    dtype=dtype,
                )
            elif file_type == CARTA.FileType.CASA:
                file_path = self.files[file_id].file_path
                data = await async_read_zarr_channel(
                    file_path=file_path,
                    time=time,
                    channel=channel,
                    stokes=stokes,
                    dtype=dtype,
                    semaphore=semaphore,
                    max_workers=max_workers,
                )

        if isinstance(data, da.Array):
            if not return_future:
                data = await self.client.compute(data)

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
        memmap: np.memmap | None = None,
        dtype: np.dtype | None = None,
        semaphore: asyncio.Semaphore | None = None,
        max_workers: int = 4,
        use_dask: bool = False,
        return_future: bool = False,
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
                memmap=memmap,
                dtype=dtype,
                semaphore=semaphore,
                max_workers=max_workers,
                use_dask=use_dask,
                return_future=return_future,
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
                memmap=memmap,
                dtype=dtype,
                semaphore=semaphore,
                max_workers=max_workers,
                use_dask=use_dask,
                return_future=return_future,
            )

        # Downsample data
        if mip > 1:
            if isinstance(data, da.Array):
                # Check if need to pad NaN
                if data.shape[0] % mip != 0 or data.shape[1] % mip != 0:
                    pad_y = mip - data.shape[0] % mip
                    pad_x = mip - data.shape[1] % mip
                    pad_y = pad_y if pad_y != mip else 0
                    pad_x = pad_x if pad_x != mip else 0
                    padding = ((0, pad_y), (0, pad_x))
                    data = da.pad(
                        data, padding, mode="constant", constant_values=da.nan
                    )
                data = da.coarsen(da.nanmean, data, {0: mip, 1: mip})
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
            # Check if need to pad NaN
            if data.shape[0] % mip != 0 or data.shape[1] % mip != 0:
                pad_y = mip - data.shape[0] % mip
                pad_x = mip - data.shape[1] % mip
                pad_y = pad_y if pad_y != mip else 0
                pad_x = pad_x if pad_x != mip else 0
                padding = ((0, pad_y), (0, pad_x))
                data = da.pad(
                    data, padding, mode="constant", constant_values=da.nan
                )
            data = da.coarsen(da.nanmean, data, {0: mip, 1: mip})
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
        array_axes_dict = self.files[file_id].array_axes_dict
        full_channel_size = self.files[file_id].sizes["frequency"]

        if x is None:
            x = slice(None)
        if y is None:
            y = slice(None)
        if channel is None:
            channel = slice(0, full_channel_size)
        if isinstance(channel, slice):
            start = channel.start if channel.start is not None else 0
            stop = (
                channel.stop if channel.stop is not None else full_channel_size
            )
            channel_size = stop - start
            channel = slice(start, stop)

        if semaphore is None:
            semaphore = asyncio.Semaphore(max_workers)

        if use_dask:
            data = await async_load_data(
                data=self.files[file_id].data,
                array_axes_dict=array_axes_dict,
                x=x,
                y=y,
                channel=channel,
                stokes=stokes,
                time=time,
                dtype=dtype,
            )
            if not return_future:
                data = await self.client.compute(data)
            return data

        if file_type == CARTA.FileType.FITS:
            memmap_info = self.files[file_id].memmap_info

            if isinstance(channel, int):
                data = await async_load_data(
                    data=memmap
                    if memmap is not None
                    else np.memmap(**memmap_info),
                    array_axes_dict=array_axes_dict,
                    x=x,
                    y=y,
                    channel=channel,
                    stokes=stokes,
                    dtype=dtype,
                )
            else:

                async def load_chunk(i):
                    ichannel = slice(
                        channel.start + i * channel_size // n_jobs,
                        channel.start + (i + 1) * channel_size // n_jobs,
                    )
                    async with semaphore:
                        return await async_load_data(
                            data=memmap
                            if memmap is not None
                            else np.memmap(**memmap_info),
                            array_axes_dict=array_axes_dict,
                            x=x,
                            y=y,
                            channel=ichannel,
                            stokes=stokes,
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

    async def async_get_tile(
        self,
        file_id: str,
        tile: int,
        compression_type: CARTA.CompressionType,
        compression_quality: int,
        channel: int,
        stokes: int,
        time: int = 0,
        memmap: np.memmap | None = None,
        dtype: np.dtype | None = None,
        semaphore: asyncio.Semaphore | None = None,
        max_workers: int = 4,
        n_jobs: int = 4,
        use_dask: bool = False,
    ):
        t0 = perf_counter_ns()
        x, y, layer = decode_tile_coord(tile)
        image_shape = self.files[file_id].img_shape
        mip = layer_to_mip(layer, image_shape=image_shape)

        # Check tile cache
        name = f"{file_id}_{channel}_{stokes}_{time}_{x}_{y}_{layer}"
        if name in self.tile_cache:
            clog.debug(f"Using cached tile for {name}")
            return self.tile_cache[name]

        # Check channel cache
        layer_name = f"{file_id}_{channel}_{stokes}_{time}_{mip}"
        frame_name = f"{file_id}_{channel}_{stokes}_{time}"
        if layer_name in self.channel_cache:
            # From downsampled data
            data = self.channel_cache[layer_name]
            slicey, slicex = get_tile_slice(x, y, layer, image_shape)
            tile_data = data[slicey, slicex]
        else:
            # From full resolution data
            if frame_name in self.channel_cache:
                # From cache
                data = self.channel_cache[frame_name]
                slicey, slicex = get_tile_original_slice(
                    x, y, layer, image_shape
                )
                tile_data = data[slicey, slicex]
            else:
                # From file
                slicey, slicex = get_tile_original_slice(
                    x, y, layer, image_shape
                )
                tile_data = await self.async_get_slice(
                    file_id=file_id,
                    x=slicex,
                    y=slicey,
                    channel=channel,
                    stokes=stokes,
                    time=time,
                    memmap=memmap,
                    dtype=dtype,
                    semaphore=semaphore,
                    max_workers=max_workers,
                    n_jobs=n_jobs,
                    use_dask=use_dask,
                    return_future=use_dask,
                )

            # Downsample
            if isinstance(tile_data, da.Array):
                # Check if need to pad NaN
                if (
                    tile_data.shape[0] % mip != 0
                    or tile_data.shape[1] % mip != 0
                ):
                    pad_y = mip - tile_data.shape[0] % mip
                    pad_x = mip - tile_data.shape[1] % mip
                    pad_y = pad_y if pad_y != mip else 0
                    pad_x = pad_x if pad_x != mip else 0
                    padding = ((0, pad_y), (0, pad_x))
                    tile_data = da.pad(
                        tile_data,
                        padding,
                        mode="constant",
                        constant_values=da.nan,
                    )
                tile_data = da.coarsen(da.nanmean, tile_data, {0: mip, 1: mip})
            else:
                t1 = perf_counter_ns()
                tile_data = await asyncio.to_thread(
                    block_reduce_numba, tile_data, mip
                )
                dt = (perf_counter_ns() - t1) / 1e6
                iy, ix = tile_data.shape
                msg = f"Downsample tile data to {ix}x{iy} in {dt:.3f} ms "
                msg += f"at {tile_data.size / 1e6 / dt * 1000:.3f} MPix/s"
                pflog.debug(msg)

        if isinstance(tile_data, da.Array):
            # tile_data = await self.client.compute(tile_data)
            res = delayed(compute_tile)(
                tile_data,
                compression_type,
                compression_quality,
            )
            res = await self.client.compute(res)
        else:
            res = compute_tile(
                tile_data,
                compression_type,
                compression_quality,
            )

        comp_data, precision, nan_encodings, tile_shape = res

        # Cache tile
        if name not in self.tile_cache:
            self.tile_cache[name] = (
                comp_data,
                precision,
                nan_encodings,
                tile_shape,
            )

        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Compute tile data in {dt:.3f} ms "
        msg += f"at {tile_data.size / 1e6 / dt * 1000:.3f} MPix/s"
        pflog.debug(msg)

        return comp_data, precision, nan_encodings, tile_shape

    async def async_get_tiles(
        self,
        file_id: str,
        tiles: List[int],
        compression_type: CARTA.CompressionType,
        compression_quality: int,
        channel: int,
        stokes: int,
        time: int = 0,
        memmap: np.memmap | None = None,
        dtype: np.dtype | None = None,
        semaphore: asyncio.Semaphore | None = None,
        max_workers: int = 4,
        n_jobs: int = 4,
        use_dask: bool = False,
    ):
        coord_dict = {tile: decode_tile_coord(tile) for tile in tiles}
        tile_dict = {}

        # Check tile cache
        for tile, coord in coord_dict.items():
            x, y, layer = coord
            name = f"{file_id}_{channel}_{stokes}_{time}_{x}_{y}_{layer}"
            if name in self.tile_cache:
                clog.debug(f"Using cached tile for {name}")
                tile_dict[tile] = self.tile_cache[name]
                del coord_dict[tile]

        # Check if all tiles are in the same layer
        coords_arr = np.array(list(coord_dict.values()))
        image_shape = self.files[file_id].img_shape
        mip = layer_to_mip(coords_arr[0, 2], image_shape)
        mip_name = f"{file_id}_{channel}_{stokes}_{time}_{mip}"

        if (
            not np.all(coords_arr[:, 2] == coords_arr[0, 2])
            or mip_name in self.channel_cache
        ):
            tasks = []
            for tile, coord in coord_dict.items():
                tasks.append(
                    self.fm.async_get_tile(
                        file_id=file_id,
                        tile=tile,
                        compression_type=compression_type,
                        compression_quality=compression_quality,
                        channel=channel,
                        stokes=stokes,
                        time=time,
                        dtype=dtype,
                        semaphore=semaphore,
                        n_jobs=n_jobs,
                    )
                )
            results = await asyncio.gather(*tasks)
            for tile, ires in zip(coord_dict.keys(), results):
                tile_dict[tile] = ires
        else:
            xmin = np.min(coords_arr[:, 0])
            xmax = np.max(coords_arr[:, 0])
            ymin = np.min(coords_arr[:, 1])
            ymax = np.max(coords_arr[:, 1])
            y_slice, x_slice = get_tile_original_slice(
                xmin, ymin, layer, image_shape, tile_shape=TILE_SHAPE
            )
            y_sl_min = y_slice.start
            x_sl_min = x_slice.start
            y_slice, x_slice = get_tile_original_slice(
                xmax, ymax, layer, image_shape, tile_shape=TILE_SHAPE
            )
            y_sl_max = y_slice.stop
            x_sl_max = x_slice.stop
            y_slice = slice(y_sl_min, y_sl_max)
            x_slice = slice(x_sl_min, x_sl_max)

            # Get data
            frame_name = f"{file_id}_{channel}_{stokes}_{time}"
            if frame_name in self.channel_cache.keys():
                # From cache
                data = self.channel_cache[frame_name]
                data = data[y_slice, x_slice]
            else:
                # From file
                data = await self.async_get_slice(
                    file_id=file_id,
                    x=x_slice,
                    y=y_slice,
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

            # Downsample
            if isinstance(data, da.Array):
                data = da.coarsen(
                    da.nanmean,
                    data,
                    {0: mip, 1: mip},
                    trim_excess=False,
                )
            else:
                t0 = perf_counter_ns()
                data = await asyncio.to_thread(block_reduce_numba, data, mip)
                dt = (perf_counter_ns() - t0) / 1e6
                msg = f"Downsample {data.shape[1]}x{data.shape[0]} data in {dt:.3f} ms "
                msg += f"at {data.size / 1e6 / dt * 1000:.3f} MPix/s"
                pflog.debug(msg)

            if isinstance(data, da.Array):
                data = await self.client.compute(data)

            for tile, coord in coord_dict.items():
                x, y, layer = coord
                y_slice, x_slice = get_tile_slice(
                    x, y, layer, image_shape, tile_shape=TILE_SHAPE
                )
                # Compute tile
                comp_data, precision, nan_encodings, tile_shape = (
                    self._compute_tile(
                        data[y_slice, x_slice],
                        compression_type,
                        compression_quality,
                    )
                )
                # Cache tile
                name = f"{file_id}_{channel}_{stokes}_{time}_{x}_{y}_{layer}"
                self.tile_cache[name] = (
                    comp_data,
                    precision,
                    nan_encodings,
                    tile_shape,
                )
                tile_dict[tile] = (
                    comp_data,
                    precision,
                    nan_encodings,
                    tile_shape,
                )

        return tile_dict

    async def async_tile_generator(
        self,
        file_id: str,
        tiles: List[int],
        compression_type: CARTA.CompressionType,
        compression_quality: int,
        channel: int,
        stokes: int,
        time: int = 0,
        memmap: np.memmap | None = None,
        dtype: np.dtype | None = None,
        semaphore: asyncio.Semaphore | None = None,
        max_workers: int = 4,
        n_jobs: int = 4,
        use_dask: bool = False,
    ) -> AsyncGenerator[Tuple[int, Any], None]:
        coord_dict = {tile: decode_tile_coord(tile) for tile in tiles}

        # Check tile cache and yield cached tiles immediately
        remaining_coords = {}
        for tile, coord in coord_dict.items():
            x, y, layer = coord
            name = f"{file_id}_{channel}_{stokes}_{time}_{x}_{y}_{layer}"
            if name in self.tile_cache:
                clog.debug(f"Using cached tile for {name}")
                yield tile, self.tile_cache[name]
            else:
                remaining_coords[tile] = coord

        if not remaining_coords:
            return

        coord_dict = remaining_coords

        # Check if all tiles are in the same layer
        coords_arr = np.array(list(coord_dict.values()))
        image_shape = self.files[file_id].img_shape
        mip = layer_to_mip(coords_arr[0, 2], image_shape)
        mip_name = f"{file_id}_{channel}_{stokes}_{time}_{mip}"

        if (
            not np.all(coords_arr[:, 2] == coords_arr[0, 2])
            or mip_name in self.channel_cache
        ):
            tasks = {}
            for tile, coord in coord_dict.items():
                task = asyncio.create_task(
                    self.fm.async_get_tile(
                        file_id=file_id,
                        tile=tile,
                        compression_type=compression_type,
                        compression_quality=compression_quality,
                        channel=channel,
                        stokes=stokes,
                        time=time,
                        dtype=dtype,
                        semaphore=semaphore,
                        n_jobs=n_jobs,
                    )
                )
                tasks[task] = tile

            for future in asyncio.as_completed(tasks):
                tile = tasks[future]
                ires = await future
                yield tile, ires
        else:
            xmin = np.min(coords_arr[:, 0])
            xmax = np.max(coords_arr[:, 0])
            ymin = np.min(coords_arr[:, 1])
            ymax = np.max(coords_arr[:, 1])
            y_slice, x_slice = get_tile_original_slice(
                xmin, ymin, layer, image_shape, tile_shape=TILE_SHAPE
            )
            y_sl_min = y_slice.start
            x_sl_min = x_slice.start
            y_slice, x_slice = get_tile_original_slice(
                xmax, ymax, layer, image_shape, tile_shape=TILE_SHAPE
            )
            y_sl_max = y_slice.stop
            x_sl_max = x_slice.stop
            y_slice = slice(y_sl_min, y_sl_max)
            x_slice = slice(x_sl_min, x_sl_max)

            # Get data
            frame_name = f"{file_id}_{channel}_{stokes}_{time}"
            if frame_name in self.channel_cache.keys():
                # From cache
                data = self.channel_cache[frame_name]
                data = data[y_slice, x_slice]
            else:
                # From file
                data = await self.async_get_slice(
                    file_id=file_id,
                    x=x_slice,
                    y=y_slice,
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

            # Downsample
            if isinstance(data, da.Array):
                data = da.coarsen(
                    da.nanmean,
                    data,
                    {0: mip, 1: mip},
                    trim_excess=False,
                )
            else:
                t0 = perf_counter_ns()
                data = await asyncio.to_thread(block_reduce_numba, data, mip)
                dt = (perf_counter_ns() - t0) / 1e6
                msg = f"Downsample {data.shape[1]}x{data.shape[0]} data in {dt:.3f} ms "
                msg += f"at {data.size / 1e6 / dt * 1000:.3f} MPix/s"
                pflog.debug(msg)

            if isinstance(data, da.Array):
                data = await self.client.compute(data)

            for tile, coord in coord_dict.items():
                x, y, layer = coord
                y_slice, x_slice = get_tile_slice(
                    x, y, layer, image_shape, tile_shape=TILE_SHAPE
                )
                # Compute tile
                comp_data, precision, nan_encodings, tile_shape = (
                    self._compute_tile(
                        data[y_slice, x_slice],
                        compression_type,
                        compression_quality,
                    )
                )
                # Cache tile
                name = f"{file_id}_{channel}_{stokes}_{time}_{x}_{y}_{layer}"
                self.tile_cache[name] = (
                    comp_data,
                    precision,
                    nan_encodings,
                    tile_shape,
                )
                yield (
                    tile,
                    (
                        comp_data,
                        precision,
                        nan_encodings,
                        tile_shape,
                    ),
                )

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
        return_future: bool = False,
    ):
        # Load data
        file_type = self.files[file_id].file_type
        array_axes_dict = self.files[file_id].array_axes_dict
        full_channel_size = self.files[file_id].sizes["frequency"]

        if semaphore is None:
            semaphore = asyncio.Semaphore(max_workers)

        if use_dask:
            data = await async_load_data(
                data=self.files[file_id].data,
                array_axes_dict=array_axes_dict,
                x=x,
                y=y,
                channel=channel,
                stokes=stokes,
                time=time,
                dtype=dtype,
            )
            if not return_future:
                data = await self.client.compute(data)
            return data

        if file_type == CARTA.FileType.FITS:
            memmap_info = self.files[file_id].memmap_info

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
                    return await async_load_data(
                        data=memmap
                        if memmap is not None
                        else np.memmap(**memmap_info),
                        array_axes_dict=array_axes_dict,
                        x=x,
                        y=y,
                        channel=ichannel,
                        stokes=stokes,
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

    async def async_get_histogram(
        self,
        file_id: str,
        channel: int,
        stokes: int = 0,
        time: int = 0,
        semaphore: asyncio.Semaphore | None = None,
        max_workers: int = 4,
        use_dask: bool = False,
    ):
        file_type = self.files[file_id].file_type
        image_shape = self.files[file_id].img_shape
        block_shape = (2048, 2048)
        # nbins = int(
        #     min(max(np.sqrt(image_shape[0] * image_shape[1]), 2.0), 10000)
        # )
        nbins = int(max(np.sqrt(image_shape[0] * image_shape[1]), 2.0))
        dtype = np.float32

        if semaphore is None:
            semaphore = asyncio.Semaphore(max_workers)

        if file_type == CARTA.FileType.FITS:
            array_axes_dict = self.files[file_id].array_axes_dict
            memmap_info = self.files[file_id].memmap_info
            slices_y, slices_x = compute_slices(image_shape, block_shape)

            async def calc_single_hist(sy, sx):
                async with semaphore:
                    data = await async_load_data(
                        data=np.memmap(**memmap_info),
                        array_axes_dict=array_axes_dict,
                        x=sx,
                        y=sy,
                        channel=channel,
                        stokes=stokes,
                        time=time,
                        dtype=dtype,
                    )
                res = await asyncio.to_thread(
                    get_block_hist, data, block_shape[0]
                )
                return res

            tasks = [
                calc_single_hist(sy, sx)
                for sy, sx in product(slices_y, slices_x)
            ]

            hists = np.empty((len(tasks), block_shape[0] * 2 + 2), dtype=dtype)

            for i, task in enumerate(asyncio.as_completed(tasks)):
                result = await task
                hists[i] = result

            bin_min = np.nanmin(hists[:, -2])
            bin_max = np.nanmax(hists[:, -1])
            bin_width = (bin_max - bin_min) / nbins
            bin_edges = np.linspace(bin_min, bin_max, nbins + 1, dtype=dtype)
            bin_centers = bin_edges[:-1] + bin_width / 2

            hist = numba_combine_block_histograms(hists, bin_edges)

            mean = np.sum(hist * bin_centers) / np.sum(hist)
            std_dev = np.sqrt(
                np.sum(hist * (bin_centers - mean) ** 2) / np.sum(hist)
            )

        histogram = CARTA.Histogram()
        histogram.num_bins = nbins
        histogram.bin_width = bin_width
        histogram.first_bin_center = bin_centers[0]
        histogram.bins.extend(hist)
        histogram.mean = mean
        histogram.std_dev = std_dev
        return histogram

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
        while True:
            if hdul[hdu_index].data is not None:
                break
            hdu_index += 1
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
    array_axes_dict = get_array_axes_dict(header)
    sizes = {
        "l": shape[array_axes_dict["x"]] if "x" in array_axes_dict else None,
        "m": shape[array_axes_dict["y"]] if "y" in array_axes_dict else None,
        "frequency": shape[array_axes_dict["channel"]]
        if "channel" in array_axes_dict
        else None,
        "stokes": shape[array_axes_dict["stokes"]]
        if "stokes" in array_axes_dict
        else None,
        "time": shape[array_axes_dict["time"]]
        if "time" in array_axes_dict
        else None,
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

    clog.debug(f"File ID {file_id} opened successfully")
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
        raster_event=asyncio.Event(),
        data_size_mib=data_size_mib,
        frame_size_mib=frame_size_mib,
        spat_req={
            "x": {"start": 0, "end": None, "mip": 1, "width": 0},
            "y": {"start": 0, "end": None, "mip": 1, "width": 0},
        },
        cursor_coords=[None, None, None],
        array_axes_dict=array_axes_dict,
        use_dask=False,
    )
    return filedata


async def get_zarr_FileData(file_id, file_path):
    # Get information
    zgrp = await open_group(file_path)
    header = await get_header_from_zarr(zgrp)

    sizes = {
        "l": header["NAXIS1"],
        "m": header["NAXIS2"],
        "frequency": header["NAXIS4"],
        "stokes": header["NAXIS3"],
        "time": header["NAXIS5"],
    }

    sky = await zgrp.get("SKY")
    chunks = sky.chunks
    itemsize = np.dtype(sky.dtype).itemsize
    data_size_mib = sky.nbytes / 1024**2
    frame_size_mib = itemsize * sizes["l"] * sizes["m"] / 1024**2
    img_shape = [sizes["m"], sizes["l"]]
    array_axes_dict = get_array_axes_dict(header)

    # Create dask array
    data = da.from_zarr(file_path / "SKY")
    data = data.swapaxes(3, 4)

    # Log file information in separate parts to avoid
    # formatting conflicts
    clog.debug(f"File ID {file_id} opened successfully.")
    clog.debug(
        f"File dimensions: time={sizes['time']}, "
        f"frequency={sizes['frequency']}, "
        f"polarization={sizes['stokes']}, "
        f"l={sizes['l']}, "
        f"m={sizes['m']}"
    )
    clog.debug(f"Chunking: {str(chunks)}")

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
        raster_event=asyncio.Event(),
        data_size_mib=data_size_mib,
        frame_size_mib=frame_size_mib,
        spat_req={
            "x": {"start": 0, "end": None, "mip": 1, "width": 0},
            "y": {"start": 0, "end": None, "mip": 1, "width": 0},
        },
        cursor_coords=[None, None, None],
        array_axes_dict=array_axes_dict,
        use_dask=False,
    )
    return filedata
