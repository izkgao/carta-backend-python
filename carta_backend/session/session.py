import asyncio
import itertools
import os
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Optional, Tuple

import dask.array as da
import numpy as np
import zfpy
from aioitertools import iter
from astropy.io import fits
from dask.distributed import Client, as_completed
from xarray import open_zarr

from carta_backend import proto as CARTA
from carta_backend.config.config import ICD_VERSION
from carta_backend.file import (
    FileManager,
    get_directory_info,
    get_file_info,
    get_file_info_extended,
    get_header_from_xradio,
)
from carta_backend.file.utils import (
    get_region_file_type,
    is_accessible,
    is_casa,
    is_zarr,
)
from carta_backend.log import logger
from carta_backend.region import get_region
from carta_backend.region.utils import (
    RegionData,
    get_spectral_profile_dask,
    parse_region,
)
from carta_backend.tile import (
    decode_tile_coord,
    get_nan_encodings_block,
    get_tile_slice,
)
from carta_backend.utils import PROTO_FUNC_MAP, get_event_info, get_system_info

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


class Session:
    # Add a mapping dict from event_type to method in Session
    handler_map = {
        1: "do_RegisterViewer",
        2: "do_FileListRequest",
        3: "do_FileInfoRequest",
        13: "do_CloseFile",
        4: "do_OpenFile",
        30: "do_AddRequiredTiles",
        6: "do_SetImageChannels",
        7: "do_SetCursor",
        8: "do_SetSpatialRequirements",
        14: "do_SetSpectralRequirements",
        11: "do_SetRegion",
        33: "do_RegionListRequest",
        35: "do_RegionFileInfoRequest",
        37: "do_ImportRegion",
        12: "do_RemoveRegion",
    }

    def __init__(
        self,
        session_id: int = 0,
        top_level_folder: str = None,
        starting_folder: str = None,
        lock: asyncio.Lock = None,
        client: Client = None,
    ):
        self.session_id = session_id
        self.top_level_folder = Path(top_level_folder)
        self.starting_folder = Path(starting_folder)
        self.lock = lock or asyncio.Lock()
        self.client = client
        self.fm = FileManager(client)

        # Set up message queue
        self.queue = asyncio.Queue()

        # FileList
        self.flag_stop_file_list = False

        # Histogram
        self.hist_events = {}

        # Tiles
        self.tile_futures = {}
        self.priority_counter = itertools.count()

        # Channel & Stokes
        self.channel_stokes = [0, 0]

        # SpatialRequirements
        self.spat_dict = {}

        # SpectralRequirements
        self.spec_prof_on = False
        self.spec_prof_cursor_on = False
        self.prev_stats_type = None

        # Cursor
        self.cursor_dict = {}

        # Region
        self.region_dict = {}

        # Task tokens for cursor movement
        self.cursor_task_tokens = {}

    async def close(self):
        # Close dask client
        if self.client is not None:
            await self.client.close()
            self.client = None

    async def take_action(self, message: bytes) -> None:
        # Get event info from received message
        event_type, event_name = get_event_info(message)
        ptlog.debug(f"<green><== {event_name}</>")

        # Get corresponding handler (e.g., do_FileListRequest)
        handler = self.handler_map.get(event_type, None)
        if handler is None:
            ptlog.error(f"No handler for event {event_name}")
            return None

        # Call handler
        handler = getattr(self, handler)
        await handler(message)

    def decode_message(self, message: bytes) -> Optional[Tuple[int, int, Any]]:
        event_type = int.from_bytes(message[0:2], byteorder="little")
        # icd_version = int.from_bytes(message[2:4], byteorder="little")
        request_id = int.from_bytes(message[4:8], byteorder="little")

        func = PROTO_FUNC_MAP.get(event_type, None)

        if func is None:
            return None

        obj = func()
        obj.ParseFromString(message[8:])

        return event_type, request_id, obj

    def encode_message(
        self, event_type: int, request_id: int, obj: Any
    ) -> bytes:
        message = event_type.to_bytes(2, byteorder="little")
        message += ICD_VERSION.to_bytes(2, byteorder="little")
        message += request_id.to_bytes(4, byteorder="little")
        message += obj.SerializeToString()
        return message

    async def do_template(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        pass

        # Create response object
        pass

        # Send message
        pass

    async def do_RegisterViewer(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        session_id = obj.session_id
        # api_key = obj.api_key
        # client_feature_flags = obj.client_feature_flags

        # Create response object
        response = CARTA.RegisterViewerAck()

        if session_id == 0:
            response.session_id = session_id
            response.success = True
            response.message = ""
            response.session_type = CARTA.SessionType.NEW
            response.platform_strings.update(get_system_info())
        else:
            # Resume an existing session
            # Not implemented
            response.success = False
            response.message = "Not implemented"

        # Send message
        event_type = CARTA.EventType.REGISTER_VIEWER_ACK
        message = self.encode_message(event_type, request_id, response)
        await self.queue.put(message)

        # Import (compile) numba functions here
        # This block is good for doing time-consuming tasks
        # and the performance will not be affected.
        from carta_backend.tile.utils import fill_nan_with_block_average
        from carta_backend.utils.histogram import get_histogram

        self.get_histogram = get_histogram
        self.fill_nan_with_block_average = fill_nan_with_block_average
        return None

    async def do_FileListRequest(self, message: bytes) -> None:
        """Handle file list request from client.

        This method processes a FileListRequest, which asks for a list
        of files and subdirectories in a specified directory. It sends
        progress updates during processing and returns a FileListResponse
        with the results.

        Parameters
        ----------
        message : bytes
            The message containing the directory to list and filter mode

        Returns
        -------
        tuple
            A tuple containing the event type (FILE_LIST_RESPONSE) and the
            response object
        """
        # Not implemented: ListProgress, CASA, DS9_REG, MIRIAD

        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        directory = obj.directory
        # filter_mode = obj.filter_mode

        # Set directory
        if directory == "$BASE":
            directory = self.starting_folder
        else:
            directory = self.top_level_folder / directory

        # Reset stop flag
        async with self.lock:
            self.flag_stop_file_list = False

        # Create response object
        response = CARTA.FileListResponse()
        response.directory = str(directory.relative_to(self.top_level_folder))
        parent = directory.parent
        if parent == self.top_level_folder:
            parent = ""
        else:
            parent = str(parent.relative_to(self.top_level_folder))
        response.parent = parent

        # Check if directory is accessible
        if not is_accessible(directory):
            response.success = False
            msg = f"Directory '{directory}' is not accessible"
            response.message = msg
            event_type = CARTA.EventType.FILE_LIST_RESPONSE
            message = self.encode_message(event_type, request_id, response)
            await self.queue.put(message)
            return None

        # Lists of files and directories
        files = []
        subdirectories = []

        # Get total items
        items = os.listdir(directory)

        try:
            for item in items:
                # Check if operation was cancelled
                async with self.lock:
                    if self.flag_stop_file_list:
                        # Set response
                        response.files.extend(files)
                        response.subdirectories.extend(subdirectories)
                        response.success = False
                        response.cancel = True
                        event_type = CARTA.EventType.FILE_LIST_RESPONSE
                        # Encode message
                        message = self.encode_message(
                            event_type, request_id, response
                        )
                        # Send message
                        await self.queue.put(message)
                        return None

                # Full path of item
                item_path = directory / item

                # Check if item is accessible
                if not is_accessible(item_path):
                    continue

                # If item is a directory
                if item_path.is_dir():
                    # Skip hidden directories
                    if item.startswith("."):
                        continue
                    # Treat .zarr folder as a file
                    elif item.endswith(".zarr"):
                        file_info = get_file_info(item_path)
                        files.append(file_info)
                    else:
                        dir_info = get_directory_info(item_path)
                        subdirectories.append(dir_info)
                # If item is a file
                else:
                    # Acceptable extensions
                    extensions = [".fits", ".fit", ".fts", ".hdf5", ".h5"]

                    # Get file extension
                    extension = os.path.splitext(item)[1].lower()

                    # Skip hidden files
                    if item.startswith("."):
                        continue
                    # Skip files with unacceptable extensions
                    elif extension not in extensions:
                        continue

                    file_info = get_file_info(item_path)
                    files.append(file_info)

            response.files.extend(files)
            response.subdirectories.extend(subdirectories)
            response.success = True

        except Exception as e:
            response.success = False
            response.message = f"Error listing directory: {str(e)}"
            clog.error(f"Error in do_FileListRequest: {str(e)}")

        event_type = CARTA.EventType.FILE_LIST_RESPONSE
        message = self.encode_message(event_type, request_id, response)
        await self.queue.put(message)
        return None

    async def do_StopFileList(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        # file_list_type = obj.file_list_type

        # Set stop flag
        async with self.lock:
            self.flag_stop_file_list = True

        return None

    async def do_FileInfoRequest(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        directory = obj.directory
        file = obj.file
        # hdu = obj.hdu
        # support_aips_beam = obj.support_aips_beam

        # Set parameters
        directory = self.top_level_folder / directory
        file_path = str(directory / file)

        # Get file info
        file_info = get_file_info(file_path)

        # Create response object
        response = CARTA.FileInfoResponse()
        response.success = True
        response.file_info.CopyFrom(file_info)

        # Read headers
        if file_info.type == CARTA.FileType.CASA:
            # Currently zarr
            xarr = open_zarr(file_path)
            hdr = await get_header_from_xradio(xarr, self.client)
            xarr.close()
            fex_dict = get_file_info_extended([hdr], file)
            for k, v in fex_dict.items():
                response.file_info_extended[k].CopyFrom(v)
        elif file_info.type == CARTA.FileType.FITS:
            with fits.open(file_path) as hdul:
                hdrs = [h.header for h in hdul]
                fex_dict = get_file_info_extended(hdrs, file)
                for k, v in fex_dict.items():
                    response.file_info_extended[k].CopyFrom(v)

        # Send message
        event_type = CARTA.EventType.FILE_INFO_RESPONSE
        message = self.encode_message(event_type, request_id, response)
        await self.queue.put(message)
        return None

    async def do_CloseFile(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id

        # If file is open, close it
        self.fm.close(file_id)
        if file_id in self.hist_events:
            self.hist_events[file_id].clear()
            del self.hist_events[file_id]

        return None

    async def do_OpenFile(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        directory = obj.directory
        file = obj.file
        hdu = obj.hdu
        file_id = obj.file_id
        # render_mode = obj.render_mode
        # lel_expr = obj.lel_expr
        # support_aips_beam = obj.support_aips_beam

        # Set parameters
        directory = self.top_level_folder / obj.directory
        file_name = file
        file_path = str(directory / file_name)
        hdu_index = int(hdu) if len(hdu) > 0 else 0
        file_info = get_file_info(file_path)

        self.file_path = file_path

        # Open file
        await self.fm.open(file_id, file_path, hdu_index)
        header = self.fm.files[file_id].header

        # OpenFileAck
        # Create response object
        response = CARTA.OpenFileAck()
        response.success = True
        response.file_id = file_id
        response.file_info.CopyFrom(file_info)
        fex_dict = get_file_info_extended([header], file_name)
        response.file_info_extended.CopyFrom(list(fex_dict.values())[0])

        # Not implemented yet
        # response.beam_table

        # Send message
        event_type = CARTA.EventType.OPEN_FILE_ACK
        message = self.encode_message(event_type, request_id, response)
        await self.queue.put(message)

        # RegionHistogramData
        self.hist_events[file_id] = asyncio.Event()
        await self.send_RegionHistogramData(
            request_id=0, file_id=file_id, region_id=-1, channel=0, stokes=0
        )

        return None

    async def send_RegionHistogramData(
        self,
        request_id: int,
        file_id: int,
        region_id: int,
        channel: int = 0,
        stokes: int = 0,
        mip: int = 1,
    ) -> None:
        """
        This executes when the image is first loaded and
        when channel/stokes changes.
        """
        # Load image
        t0 = perf_counter_ns()

        data = await self.fm.get_slice(file_id, channel, stokes, mip=mip)

        dt = (perf_counter_ns() - t0) / 1e6

        shape = data.shape
        mpix_s = data.size / 1e6 / dt * 1000

        if isinstance(data, np.ndarray):
            msg = f"Load {shape[1]}x{shape[0]} image to cache "
        else:
            msg = f"Lazy load {shape[1]}x{shape[0]} image "
        msg += f"in {dt:.3f} ms at {mpix_s:.3f} MPix/s"
        clog.debug(msg)

        # RegionHistogramData
        # Not fully implemented
        t0 = perf_counter_ns()
        response = CARTA.RegionHistogramData()
        response.file_id = file_id
        response.region_id = region_id
        response.channel = channel
        response.stokes = stokes
        response.progress = 1.0

        # Set histogram config
        config = CARTA.HistogramConfig()
        config.num_bins = -1
        config.bounds.CopyFrom(CARTA.DoubleBounds())
        response.config.CopyFrom(config)

        # Calculate histogram
        histogram = await self.get_histogram(data, self.client)
        response.histograms.CopyFrom(histogram)

        # Send message
        event_type = CARTA.EventType.REGION_HISTOGRAM_DATA
        message = self.encode_message(event_type, request_id, response)

        dt = (perf_counter_ns() - t0) / 1e6
        mpix_s = data.size / 1e6 / dt * 1000
        msg = f"Fill image histogram in {dt:.3f} ms at {mpix_s:.3f} MPix/s"
        pflog.debug(msg)

        await self.queue.put(message)

        # Mark histogram as ready
        self.hist_events[file_id].set()

        return None

    async def send_RasterTileSync(
        self,
        request_id: int,
        file_id: int,
        compression_type: int,
        compression_quality: int,
        tiles: list = [],
        channel: int = 0,
        stokes: int = 0,
    ) -> None:
        # RasterTileSync
        resp_sync = CARTA.RasterTileSync()
        resp_sync.file_id = file_id
        resp_sync.channel = channel
        resp_sync.stokes = stokes
        resp_sync.sync_id = file_id + 1
        # Not implemented
        # resp_sync.animation_id = 0
        resp_sync.tile_count = len(tiles)

        # Send message
        event_type = CARTA.EventType.RASTER_TILE_SYNC
        message = self.encode_message(event_type, request_id, resp_sync)
        await self.queue.put(message)

        priority = next(self.priority_counter)

        # Cancel futures with lower priority
        # async with self.lock:
        #     for p in list(self.tile_futures.keys()):
        #         if p < priority:
        #             for future in list(self.tile_futures[p].keys()):
        #                 await future.cancel()
        #                 del future
        #             del self.tile_futures[p]

        # RasterTileData
        t0 = perf_counter_ns()
        if tiles is None or tiles[0] == 0:
            # Send full image
            data = await self.fm.get_slice(file_id, channel, stokes)
            if isinstance(data, da.Array):
                data = await self.client.compute(data[:, :], priority=priority)
            await self.send_RasterTileData(
                request_id=request_id,
                file_id=file_id,
                data=data,
                compression_type=compression_type,
                compression_quality=compression_quality,
                channel=channel,
                stokes=stokes,
            )
        else:
            # Send tiles
            layer = decode_tile_coord(tiles[0])[2]
            data = await self.fm.get_slice(
                file_id, channel, stokes, layer=layer
            )
            image_shape = self.fm.files[file_id].img_shape

            if isinstance(data, da.Array):
                futures = {}

                for tile in tiles:
                    x, y, layer = decode_tile_coord(tile)
                    slicey, slicex = get_tile_slice(x, y, layer, image_shape)
                    future = self.client.compute(
                        data[slicey, slicex], priority=priority
                    )
                    futures[future] = (x, y, layer)

                # async with self.lock:
                #     self.tile_futures[priority] = futures

                async with asyncio.TaskGroup() as tg:
                    async for future in as_completed(futures):
                        x, y, layer = futures[future]
                        tg.create_task(
                            self.send_RasterTileData(
                                request_id=request_id,
                                file_id=file_id,
                                data=await future,
                                compression_type=compression_type,
                                compression_quality=compression_quality,
                                channel=channel,
                                stokes=stokes,
                                x=x,
                                y=y,
                                layer=layer,
                            )
                        )
            else:
                async for tile in iter(tiles):
                    x, y, layer = decode_tile_coord(tile)
                    slicey, slicex = get_tile_slice(x, y, layer, image_shape)
                    idata = data[slicey, slicex]
                    await self.send_RasterTileData(
                        request_id=request_id,
                        file_id=file_id,
                        data=idata,
                        compression_type=compression_type,
                        compression_quality=compression_quality,
                        channel=channel,
                        stokes=stokes,
                        x=x,
                        y=y,
                        layer=layer,
                    )

        dt = (perf_counter_ns() - t0) / 1e6

        # RasterTileSync
        resp_sync.tile_count = len(tiles)
        resp_sync.end_sync = True

        # Send message
        event_type = CARTA.EventType.RASTER_TILE_SYNC
        message = self.encode_message(event_type, request_id, resp_sync)
        await self.queue.put(message)

        msg = f"Get tile data group in {dt:.3f} ms"
        pflog.debug(msg)

        return None

    async def send_RasterTileData(
        self,
        request_id: int,
        file_id: int,
        data: np.ndarray,
        compression_type: int,
        compression_quality: int,
        channel: int = 0,
        stokes: int = 0,
        x: int = None,
        y: int = None,
        layer: int = None,
    ) -> None:
        t0 = perf_counter_ns()
        tile_height, tile_width = data.shape
        nan_encodings = get_nan_encodings_block(data).tobytes()
        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Get nan encodings in {dt:.3f} ms"
        pflog.debug(msg)

        # Fill NaNs
        t0 = perf_counter_ns()
        data = self.fill_nan_with_block_average(data.astype(np.float32))
        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Fill NaN with block average in {dt:.3f} ms"
        pflog.debug(msg)

        # msg = f"Nearest neighbour filter {tile_width}x{tile_height} "
        # msg += f"raster data to {tile_width}x{tile_height} in "
        # msg += f"{dt:.3f} ms at {data.size / 1e6 / dt * 1000:.3f} MPix/s"
        # pflog.debug(msg)

        # Compress data
        t0 = perf_counter_ns()
        if compression_type == CARTA.CompressionType.ZFP:
            comp_data = zfpy.compress_numpy(
                data, precision=compression_quality, write_header=False
            )
        elif compression_type == CARTA.CompressionType.SZ:
            # Not implemented yet
            comp_data = data.tobytes()
        else:
            comp_data = data.tobytes()

        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Compress {tile_width}x{tile_height} tile data in {dt:.3f} ms "
        msg += f"at {data.size / 1e6 / dt * 1000:.3f} MPix/s"
        pflog.debug(msg)

        # RasterTileData
        resp_data = CARTA.RasterTileData()
        resp_data.file_id = file_id
        resp_data.channel = channel
        resp_data.stokes = stokes
        resp_data.compression_type = compression_type
        resp_data.compression_quality = compression_quality
        resp_data.sync_id = file_id + 1
        # resp_data.animation_id = 0

        tile = CARTA.TileData()
        tile.width = tile_width
        tile.height = tile_height
        tile.image_data = comp_data
        tile.nan_encodings = nan_encodings
        if x is not None:
            tile.x = x
        if y is not None:
            tile.y = y
        if layer is not None:
            tile.layer = layer

        resp_data.tiles.append(tile)

        # Send message
        event_type = CARTA.EventType.RASTER_TILE_DATA
        message = self.encode_message(event_type, request_id, resp_data)
        await self.queue.put(message)

        return None

    async def do_AddRequiredTiles(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        tiles = obj.tiles
        compression_type = obj.compression_type
        compression_quality = obj.compression_quality
        # current_tiles = obj.current_tiles

        # Set parameters
        tiles = list(tiles)

        # Check if histogram is sent
        await self.hist_events[file_id].wait()
        # This is to switch the event loop to send the histogram
        await asyncio.sleep(0)

        # RasterTile
        await self.send_RasterTileSync(
            request_id=0,
            file_id=file_id,
            compression_type=compression_type,
            compression_quality=compression_quality,
            tiles=tiles,
            channel=0,
            stokes=0,
        )

        return None

    async def do_SetImageChannels(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        # Main obj
        file_id = obj.file_id
        channel = obj.channel
        stokes = obj.stokes
        required_tiles = obj.required_tiles
        # channel_range = obj.channel_range
        # current_range = obj.current_range
        # channel_map_enabled = obj.channel_map_enabled
        tiles = required_tiles.tiles
        compression_type = required_tiles.compression_type
        compression_quality = required_tiles.compression_quality

        # Update channel and stokes
        async with self.lock:
            self.channel_stokes = [channel, stokes]

        # RegionHistogramData
        await self.send_RegionHistogramData(
            request_id=0,
            file_id=file_id,
            region_id=-1,
            channel=channel,
            stokes=stokes,
        )

        # RasterTile
        await self.send_RasterTileSync(
            request_id=0,
            file_id=file_id,
            compression_type=compression_type,
            compression_quality=compression_quality,
            tiles=tiles,
            channel=channel,
            stokes=stokes,
        )

        return None

    async def do_SetSpatialRequirements(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        region_id = obj.region_id
        spatial_profiles = obj.spatial_profiles

        # Not implemented
        if region_id > 0:
            return None

        # Record spatial profiles
        if file_id not in self.spat_dict:
            async with self.lock:
                # [start, end, mip, width]
                self.spat_dict[file_id] = {
                    "x": [0, None, 1, 0],
                    "y": [0, None, 1, 0],
                }

        to_send = False

        async with self.lock:
            for p in spatial_profiles:
                start = int(p.start)
                end = int(p.end)
                mip = int(p.mip)
                width = p.width

                if (start == 0) and (end == 0):
                    if mip != 0:
                        to_send = True
                        self.spat_dict[file_id][p.coordinate][2] = mip
                    if width == 0:
                        continue
                    else:
                        to_send = True
                        self.spat_dict[file_id][p.coordinate][3] = width
                else:
                    ox, oy, om = self.spat_dict[file_id][p.coordinate][:3]
                    if (start == ox) and (end == oy) and (mip == om):
                        continue
                    to_send = True
                    content = [start, end, mip, width]
                    self.spat_dict[file_id][p.coordinate] = content

            if file_id not in self.cursor_dict:
                to_send = False

            if to_send:
                # Read parameters
                x, y = self.cursor_dict[file_id]
                sprx = self.spat_dict[file_id]["x"]
                spry = self.spat_dict[file_id]["y"]
                channel, stokes = self.channel_stokes

        if to_send:
            # Send spatial profile data
            await self.send_SpatialProfileData(
                request_id=0,
                file_id=file_id,
                slice_x=slice(sprx[0], sprx[1]),
                slice_y=slice(spry[0], spry[1]),
                mip=sprx[2],
                x=x,
                y=y,
                channel=channel,
                stokes=stokes,
            )

        return None

    async def do_SetCursor(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        point = obj.point
        # spatial_requirements = obj.spatial_requirements

        # Check boundary
        shape = self.fm.files[file_id].img_shape
        x, y = int(point.x), int(point.y)
        if x < 0 or x >= shape[1] or y < 0 or y >= shape[0]:
            return None

        # Record cursor and read other parameters
        async with self.lock:
            if file_id not in self.spat_dict:
                # Return None if spatial requirement has not been set
                return None
            self.cursor_dict[file_id] = [x, y]
            sprx = self.spat_dict[file_id]["x"]
            spry = self.spat_dict[file_id]["y"]
            channel, stokes = self.channel_stokes
            mip = sprx[2]

            # Generate a new cursor task token to identify this request
            task_token = f"{file_id}_{x}_{y}_{perf_counter_ns()}"
            self.cursor_task_tokens[file_id] = task_token

        # Send spatial profile data
        await self.send_SpatialProfileData(
            request_id=0,
            file_id=file_id,
            slice_x=slice(sprx[0], sprx[1]),
            slice_y=slice(spry[0], spry[1]),
            mip=mip,
            x=x,
            y=y,
            channel=channel,
            stokes=stokes,
            task_token=task_token,
        )

        # Send spectral profile
        if self.spec_prof_cursor_on:
            asyncio.create_task(
                self.send_SpectroProfileData(
                    request_id=0,
                    file_id=file_id,
                    region_id=0,
                    x=x,
                    y=y,
                    stats_type=2,
                    task_token=task_token,
                )
            )

        return None

    async def send_SpatialProfileData(
        self,
        request_id: int,
        file_id: int,
        slice_x: slice,
        slice_y: slice,
        mip: int,
        x: int,
        y: int,
        channel: int,
        stokes: int,
        region_id: int = None,
        task_token: str = None,
    ) -> None:
        t0 = perf_counter_ns()

        # Get data
        shape = self.fm.files[file_id].img_shape
        data = await self.fm.get_slice(file_id, channel, stokes, mip=mip)

        if mip > 1:
            mx = x // mip
            my = y // mip
            sx1 = slice_x.start // mip if slice_x.start is not None else None
            sx2 = slice_x.stop // mip if slice_x.stop is not None else None
            sy1 = slice_y.start // mip if slice_y.start is not None else None
            sy2 = slice_y.stop // mip if slice_y.stop is not None else None
            slice_x = slice(sx1, sx2)
            slice_y = slice(sy1, sy2)
        else:
            mx = x
            my = y
            slice_x = slice(None, None)
            slice_y = slice(None, None)

        # Check if x and y are valid and inside data
        if my < 0 or my >= data.shape[0] or mx < 0 or mx >= data.shape[1]:
            return None

        if isinstance(data, da.Array):
            # Compute tasks
            futures = self.client.compute(
                [
                    data[my, mx],
                    data[my, slice_x].astype("<f4"),
                    data[slice_y, mx].astype("<f4"),
                ]
            )

            # Check if this is still the current task before awaiting results
            async with self.lock:
                current_token = self.cursor_task_tokens.get(file_id)
                if task_token is not None and current_token != task_token:
                    # This task is no longer the current task
                    # Cancel futures and abort
                    msg = "Cancelling obsolete spatial profile "
                    msg += f"calculation for {file_id}"
                    pflog.debug(msg)
                    for future in futures:
                        future.cancel()
                    return None

            try:
                # Await results (may raise if cancelled)
                value, x_profile, y_profile = await asyncio.gather(*futures)

                # Check again after computation in case cursor moved
                # during computation
                async with self.lock:
                    current_token = self.cursor_task_tokens.get(file_id)
                    if task_token is not None and current_token != task_token:
                        # This task is no longer the current task, abort
                        msg = "Discarding obsolete spatial profile "
                        msg += f"results for {file_id}"
                        pflog.debug(msg)
                        return None
            except Exception as e:
                # Handle cancellation or other exceptions
                msg = "Dask computation for spatial profile failed: "
                msg += str(e)
                pflog.debug(msg)
                return None

            value = float(value)
            x_profile = x_profile.tobytes()
            y_profile = y_profile.tobytes()
        else:
            value = float(data[my, mx])
            x_profile = data[my, slice_x].astype("<f4").tobytes()
            y_profile = data[slice_y, mx].astype("<f4").tobytes()

        resp = CARTA.SpatialProfileData()
        resp.file_id = file_id
        if region_id is not None:
            resp.region_id = region_id
        resp.x = x
        resp.y = y
        resp.value = value
        resp.channel = channel
        resp.stokes = stokes

        sp = CARTA.SpatialProfile()
        sp.coordinate = "x"
        sp.end = shape[1]
        sp.mip = mip
        sp.raw_values_fp32 = x_profile
        resp.profiles.append(sp)

        sp.coordinate = "y"
        sp.end = shape[0]
        sp.mip = mip
        sp.raw_values_fp32 = y_profile
        resp.profiles.append(sp)

        # Send message
        event_type = CARTA.EventType.SPATIAL_PROFILE_DATA
        message = self.encode_message(event_type, request_id, resp)
        await self.queue.put(message)

        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Fill spatial profile in {dt:.3f} ms"
        pflog.debug(msg)

        return None

    async def send_SpectroProfileData(
        self,
        request_id: int,
        file_id: int,
        region_id: int,
        region_info: CARTA.RegionInfo | None = None,
        x: int | None = None,
        y: int | None = None,
        stats_type: int = 2,
        task_token: str = None,
    ) -> None:
        t0 = perf_counter_ns()

        # Get spectral profile
        sp = CARTA.SpectralProfile()
        sp.coordinate = "z"
        sp.stats_type = stats_type

        # Set is_point to True
        # if region_id is 0 (cursor) or region is point
        if region_id == 0:
            is_point = True
        elif (
            region_info is not None
            and region_info.region_type == CARTA.RegionType.POINT
        ):
            points = region_info.control_points
            x, y = round(points[0].x), round(points[0].y)
            is_point = True
        else:
            is_point = False

        if is_point:
            # Cursor/point spectral profile
            spec_profile = self.fm.get_point_spectrum(
                file_id=file_id, x=x, y=y, channel=None, stokes=0, time=0
            )

            # Compute the task
            if isinstance(spec_profile, da.Array):
                spec_profile = await self.compute_cursor_spectral_profile(
                    spec_profile, file_id, task_token
                )

            if spec_profile is None:
                return None

            if region_id == 0:
                sp.raw_values_fp32 = spec_profile.astype("float32").tobytes()
                msg_add = " cursor"
            else:
                sp.raw_values_fp64 = spec_profile.astype("float64").tobytes()
                msg_add = ""
        else:
            # Region spectral profile
            if self.region_dict[region_id].profiles is None:
                data = await self.fm.get_slice(file_id, channel=None, stokes=0)
                hdr = self.fm.files[file_id].header
                region = get_region(region_info)
                profiles = get_spectral_profile_dask(data, region, hdr)
                profiles = await self.client.compute(profiles)
                self.region_dict[region_id].profiles = profiles

            profile = self.region_dict[region_id].profiles[stats_type - 2]
            sp.raw_values_fp64 = profile.tobytes()
            msg_add = ""

        # Create response object
        resp = CARTA.SpectralProfileData()
        resp.file_id = file_id
        resp.region_id = region_id
        resp.stokes = 0
        resp.progress = 1
        resp.profiles.append(sp)

        # Send message
        event_type = CARTA.EventType.SPECTRAL_PROFILE_DATA
        message = self.encode_message(event_type, request_id, resp)
        await self.queue.put(message)

        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Fill{msg_add} spectral profile in {dt:.3f} ms"
        pflog.debug(msg)

        return None

    async def compute_cursor_spectral_profile(
        self,
        spec_profile: da.Array,
        file_id: int,
        task_token: str,
    ):
        # Compute the task and get future
        future = self.client.compute(spec_profile)

        # Check if still current task
        async with self.lock:
            current_token = self.cursor_task_tokens.get(file_id)
        if task_token is not None and current_token != task_token:
            # This task is no longer the current task
            # Cancel future and abort
            msg = "Cancelling obsolete spectral profile "
            msg += f"calculation for {file_id}"
            pflog.debug(msg)
            future.cancel()
            return None

        try:
            # Await result (may raise if cancelled)
            spec_profile = await future

            # Check again after computation
            async with self.lock:
                current_token = self.cursor_task_tokens.get(file_id)
            if task_token is not None and current_token != task_token:
                # This task is no longer the current task
                # Cancel future and abort
                msg = "Discarding obsolete spectral profile "
                msg += f"results for {file_id}"
                pflog.debug(msg)
                return None
        except Exception as e:
            # Handle cancellation or other exceptions
            msg = "Dask computation for spectral profile failed: "
            msg += str(e)
            pflog.error(msg)
            return None

        return spec_profile

    async def do_SetRegion(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        region_id = obj.region_id
        region_info = obj.region_info
        preview_region = obj.preview_region

        # Assign region ID
        if region_id <= 0:
            region_id = max(self.region_dict.keys(), default=0) + 1

        # Record region
        async with self.lock:
            if region_id not in self.region_dict:
                self.region_dict[region_id] = RegionData(
                    file_id=file_id,
                    region_info=region_info,
                    preview_region=preview_region,
                    profiles=None,
                )
            else:
                self.region_dict[region_id].region_info = region_info
                self.region_dict[region_id].profiles = None

        # Send message
        resp = CARTA.SetRegionAck()
        resp.success = True
        resp.region_id = region_id
        event_type = CARTA.EventType.SET_REGION_ACK
        message = self.encode_message(event_type, request_id, resp)
        await self.queue.put(message)

        # Send spectral profile
        if self.spec_prof_on:
            await self.send_SpectroProfileData(
                request_id,
                file_id,
                region_id,
                region_info,
                stats_type=self.prev_stats_type,
            )

        return None

    async def do_SetSpectralRequirements(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        region_id = obj.region_id
        if len(obj.spectral_profiles) == 0:
            if region_id == 0:
                async with self.lock:
                    self.spec_prof_cursor_on = False
            else:
                async with self.lock:
                    self.spec_prof_on = False
            return None
        else:
            spectral_profile = obj.spectral_profiles[0]
            # coordinate = spectral_profile.coordinate
            stats_type = spectral_profile.stats_types[0]
            async with self.lock:
                if region_id == 0:
                    self.spec_prof_cursor_on = True
                else:
                    self.spec_prof_on = True
                self.prev_stats_type = stats_type

        # Get region info
        async with self.lock:
            if (region_id != 0) and (region_id not in self.region_dict):
                return None
            elif region_id == 0:
                # Cursor
                region_info = None
                # stats_type = 2  # Sum
                if file_id not in list(self.cursor_dict.keys()):
                    return None
                x, y = self.cursor_dict[file_id]
            else:
                # Region
                region_info = self.region_dict[region_id].region_info
                # stats_type = self.prev_stats_type
                x, y = None, None

        # Send spectral profile
        if self.spec_prof_on or self.spec_prof_cursor_on:
            # Use create_task to avoid blocking the event loop
            asyncio.create_task(
                self.send_SpectroProfileData(
                    request_id=0,
                    file_id=file_id,
                    region_id=region_id,
                    region_info=region_info,
                    stats_type=self.prev_stats_type,
                    x=x,
                    y=y,
                )
            )

        return None

    async def do_RegionListRequest(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        directory = obj.directory
        # filter_mode = obj.filter_mode

        # Set directory
        if directory == "$BASE":
            directory = self.starting_folder
        else:
            directory = self.top_level_folder / directory

        # Create response object
        resp = CARTA.RegionListResponse()
        resp.directory = str(directory.relative_to(self.top_level_folder))
        parent = directory.parent
        if parent == self.top_level_folder:
            parent = ""
        else:
            parent = str(parent.relative_to(self.top_level_folder))
        resp.parent = parent

        # Check if directory is accessible
        if not is_accessible(directory):
            resp.success = False
            msg = f"Directory '{directory}' is not accessible"
            resp.message = msg
            event_type = CARTA.EventType.REGION_LIST_RESPONSE
            message = self.encode_message(event_type, request_id, resp)
            await self.queue.put(message)
            return None

        # Lists of files and directories
        files = []
        subdirectories = []

        # Get total items
        items = os.listdir(directory)

        try:
            for item in items:
                # Full path of item
                item_path = directory / item

                # Check if item is accessible
                if not is_accessible(item_path):
                    continue

                # If item is a directory
                if item_path.is_dir():
                    # Skip hidden directories
                    if item.startswith("."):
                        continue
                    # Skip Zarr and CASA
                    elif is_zarr(item_path) or is_casa(item_path):
                        continue
                    else:
                        dir_info = get_directory_info(item_path)
                        subdirectories.append(dir_info)
                # If item is a file
                else:
                    # Skip hidden files
                    if item.startswith("."):
                        continue

                    # Check file type
                    file_type = get_region_file_type(item_path)

                    if file_type == CARTA.FileType.UNKNOWN:
                        continue

                    file_info = get_file_info(item_path, file_type)
                    files.append(file_info)

            resp.files.extend(files)
            resp.subdirectories.extend(subdirectories)
            resp.success = True

        except Exception as e:
            resp.success = False
            resp.message = f"Error listing directory: {str(e)}"
            clog.error(f"Error in do_FileListRequest: {str(e)}")

        # Send message
        event_type = CARTA.EventType.REGION_LIST_RESPONSE
        message = self.encode_message(event_type, request_id, resp)
        await self.queue.put(message)
        return None

    async def do_RegionFileInfoRequest(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        directory = obj.directory
        file = obj.file

        # Set parameters
        directory = self.top_level_folder / directory
        file_path = str(directory / file)

        # Get file info
        file_type = get_region_file_type(file_path)
        file_info = get_file_info(file_path, file_type)

        # Create response object
        resp = CARTA.RegionFileInfoResponse()
        resp.success = True
        resp.file_info.CopyFrom(file_info)

        # Read region file content
        with open(file_path, "r") as f:
            contents = f.readlines()

        for i, v in enumerate(contents):
            contents[i] = v.strip("\n")

        resp.contents.extend(contents)

        # Send message
        event_type = CARTA.EventType.REGION_FILE_INFO_RESPONSE
        message = self.encode_message(event_type, request_id, resp)
        await self.queue.put(message)
        return None

    async def do_ImportRegion(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        group_id = obj.group_id
        file_type = obj.type
        directory = obj.directory
        file = obj.file
        # contents = obj.contents

        # Set parameters
        directory = self.top_level_folder / directory
        file_path = str(directory / file)

        # Create response object
        resp = CARTA.ImportRegionAck()
        resp.success = True

        # Add regions
        regions = parse_region(file_path, file_type)
        async with self.lock:
            keys = list(self.region_dict.keys())
            max_id = max(keys) if keys else 0
            for region_info, region_style in regions:
                max_id += 1
                self.region_dict[max_id] = RegionData(
                    file_id=group_id,
                    region_info=region_info,
                    preview_region=None,
                    profiles=None,
                )
                resp.regions[max_id].CopyFrom(region_info)
                resp.region_styles[max_id].CopyFrom(region_style)

        # Send message
        event_type = CARTA.EventType.IMPORT_REGION_ACK
        message = self.encode_message(event_type, request_id, resp)
        await self.queue.put(message)
        return None

    async def do_RemoveRegion(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        region_id = obj.region_id

        # Remove region
        async with self.lock:
            if region_id in self.region_dict:
                del self.region_dict[region_id]

        return None
