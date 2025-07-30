import asyncio
import itertools
import os
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Optional, Tuple

import dask.array as da
import numpy as np
import psutil
from astropy.io import fits
from dask.distributed import Client
from numba import threading_layer
from zarr.api.asynchronous import open_group

from carta_backend import proto as CARTA
from carta_backend.config.config import (
    ICD_VERSION,
    INIT_DELTA_Z,
    N_JOBS,
    N_SEMAPHORE,
    TARGET_PARTIAL_CURSOR_TIME,
    TARGET_PARTIAL_REGION_TIME,
)
from carta_backend.file.file import FileManager
from carta_backend.file.utils import (
    async_get_file_info,
    get_directory_info,
    get_file_info_extended,
    get_header_from_zarr,
    get_region_file_type,
    is_accessible,
    is_casa,
    is_zarr,
)
from carta_backend.log import logger
from carta_backend.region import get_region
from carta_backend.region.utils import (
    RegionData,
    get_region_slices_mask,
    get_spectral_profile_dask,
    parse_region,
)
from carta_backend.tile.utils import (
    compute_tile,
    decode_tile_coord,
    get_tile_slice,
)
from carta_backend.utils.utils import (
    PROTO_FUNC_MAP,
    get_event_info,
    get_system_info,
    parse_frontend_directory,
)

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
        use_dask: bool = False,
    ):
        self.session_id = session_id
        self.top_level_folder = Path(top_level_folder)
        self.starting_folder = Path(starting_folder)
        self.lock = lock or asyncio.Lock()
        self.client = client
        self.use_dask = use_dask
        self.fm = FileManager(client)

        # Set up message queue
        self.queue = asyncio.Queue()

        # Set semaphore for reading data
        self.semaphore = asyncio.Semaphore(N_SEMAPHORE)

        # FileList
        self.flag_stop_file_list = False

        # Tiles
        self.tile_futures = {}
        self.priority_counter = itertools.count()

        # SpectralRequirements
        self.spec_prof_on = False
        self.spec_prof_cursor_on = False
        self.prev_stats_type = None

        # Region
        self.region_dict = {}

        # Show numba threading layer
        clog.debug(f"Numba threading layer: {threading_layer()}")

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
        self.queue.put_nowait(message)

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

        directory, _directory, parent = parse_frontend_directory(
            directory,
            self.starting_folder,
            self.top_level_folder,
        )

        # Reset stop flag
        async with self.lock:
            self.flag_stop_file_list = False

        # Create response object
        response = CARTA.FileListResponse()
        response.directory = _directory
        response.parent = parent

        if directory == "virtual_root":
            files = []
            subdirectories = []
            for partition in psutil.disk_partitions():
                drive = Path(partition.device).drive.rstrip(":")
                dir_info = CARTA.DirectoryInfo()
                dir_info.name = drive
                subdirectories.append(dir_info)

            response.files.extend(files)
            response.subdirectories.extend(subdirectories)
            response.success = True
            event_type = CARTA.EventType.FILE_LIST_RESPONSE
            message = self.encode_message(event_type, request_id, response)
            self.queue.put_nowait(message)
            return None

        # Check if directory is accessible
        if not is_accessible(directory):
            response.success = False
            msg = f"Directory '{directory}' is not accessible"
            response.message = msg
            event_type = CARTA.EventType.FILE_LIST_RESPONSE
            message = self.encode_message(event_type, request_id, response)
            self.queue.put_nowait(message)
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
                        self.queue.put_nowait(message)
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
                        file_info = async_get_file_info(item_path)
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

                    file_info = async_get_file_info(item_path)
                    files.append(file_info)

            files = await asyncio.gather(*files)

            response.files.extend(files)
            response.subdirectories.extend(subdirectories)
            response.success = True

        except Exception as e:
            response.success = False
            response.message = f"Error listing directory: {str(e)}"
            clog.error(f"Error in do_FileListRequest: {str(e)}")

        event_type = CARTA.EventType.FILE_LIST_RESPONSE
        message = self.encode_message(event_type, request_id, response)
        self.queue.put_nowait(message)
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
        file_info = await async_get_file_info(file_path)

        # Create response object
        response = CARTA.FileInfoResponse()
        response.success = True
        response.file_info.CopyFrom(file_info)

        # Read headers
        if file_info.type == CARTA.FileType.CASA:
            # Currently zarr
            zgrp = await open_group(file_path, mode="r")
            hdr = await get_header_from_zarr(zgrp)
            del zgrp
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
        self.queue.put_nowait(message)
        return None

    async def do_CloseFile(self, message: bytes) -> None:
        # Decode message
        event_type, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id

        # If file is open, close it
        self.fm.close(file_id)

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
        file_info = await async_get_file_info(file_path)

        self.file_path = file_path

        # Open file
        await self.fm.open(file_id, file_path, hdu_index)
        self.fm.files[file_id].use_dask = self.use_dask
        header = self.fm.files[file_id].header

        # OpenFileAck
        # Create response object
        response = CARTA.OpenFileAck()
        response.success = True
        response.file_id = file_id
        response.file_info.CopyFrom(file_info)
        fex_dict = get_file_info_extended([header], file_name)
        file_info_extended = list(fex_dict.values())[0]
        response.file_info_extended.CopyFrom(file_info_extended)

        # Not fully implemented yet
        beam = CARTA.Beam()
        beam.channel = -1
        beam.stokes = -1
        send_beam = False
        for i in file_info_extended.header_entries:
            if i.name == "BMAJ":
                beam.major_axis = float(i.value) * 3600
                send_beam = True
            elif i.name == "BMIN":
                beam.minor_axis = float(i.value) * 3600
            elif i.name == "BPA":
                beam.pa = float(i.value)
        if send_beam:
            response.beam_table.append(beam)

        # Send message
        event_type = CARTA.EventType.OPEN_FILE_ACK
        message = self.encode_message(event_type, request_id, response)
        self.queue.put_nowait(message)

        # RegionHistogramData
        await self.send_RegionHistogramData(
            request_id=0, file_id=file_id, region_id=-1, channel=0, stokes=0
        )
        # await self.send_RegionHistogramData_v2(
        #     request_id=0, file_id=file_id, region_id=-1, channel=0, stokes=0
        # )

        return None

    async def send_RegionHistogramData(
        self,
        request_id: int,
        file_id: int,
        region_id: int,
        channel: int = 0,
        stokes: int = 0,
    ) -> None:
        """
        This executes when the image is first loaded and
        when channel/stokes changes.
        """
        # Load image
        t0 = perf_counter_ns()

        data = await self.fm.async_get_channel(
            file_id=file_id,
            channel=channel,
            stokes=stokes,
            time=0,
            memmap=None,
            dtype=np.float32,
            semaphore=self.semaphore,
            # Use self.use_dask instead of file.use_dask
            # because file.use_dask may be changed after this
            # according to the ratio of frame size to available memory
            use_dask=self.use_dask,
            # Return future for dask array only
            return_future=True,
        )

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

        self.queue.put_nowait(message)

        # Mark histogram as ready
        self.fm.files[file_id].hist_event.set()

        return None

    async def send_RegionHistogramData_v2(
        self,
        request_id: int,
        file_id: int,
        region_id: int,
        channel: int = 0,
        stokes: int = 0,
    ) -> None:
        """
        This executes when the image is first loaded and
        when channel/stokes changes.
        """
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
        histogram = await self.fm.async_get_histogram(
            file_id=file_id,
            channel=channel,
            stokes=stokes,
            time=0,
            semaphore=self.semaphore,
        )
        response.histograms.CopyFrom(histogram)

        # Send message
        event_type = CARTA.EventType.REGION_HISTOGRAM_DATA
        message = self.encode_message(event_type, request_id, response)

        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Fill image histogram in {dt:.3f} ms"
        pflog.debug(msg)

        self.queue.put_nowait(message)

        # Mark histogram as ready
        self.fm.files[file_id].hist_event.set()

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
        self.queue.put_nowait(message)

        # RasterTileData
        t0 = perf_counter_ns()

        use_dask = self.fm.files[file_id].use_dask

        if (
            use_dask
            or self.fm.files[file_id].raster_event.is_set()
            or tiles[0] == 0
        ):
            clog.debug("Generate tiles separately")
            tasks = []

            for tile in tiles:
                tasks.append(
                    self.send_RasterTileData_v2(
                        request_id=request_id,
                        file_id=file_id,
                        tile=tile,
                        compression_type=compression_type,
                        compression_quality=compression_quality,
                        channel=channel,
                        stokes=stokes,
                        use_dask=use_dask,
                    )
                )

            await asyncio.gather(*tasks)

            # Signal raster event
            self.fm.files[file_id].raster_event.set()
        else:
            # All tiles
            clog.debug("Generate all tiles using full image")
            _, _, layer = decode_tile_coord(tiles[0])
            data = await self.fm.async_get_channel_mip(
                file_id=file_id,
                channel=channel,
                stokes=stokes,
                time=0,
                layer=layer,
                dtype=np.float32,
                semaphore=self.semaphore,
                use_dask=False,
            )

            tasks = []
            for tile in tiles:
                x, y, layer = decode_tile_coord(tile)
                y_slice, x_slice = get_tile_slice(
                    x, y, layer, self.fm.files[file_id].img_shape
                )
                tile_data = data[y_slice, x_slice]

                task = self.send_RasterTileData(
                    request_id=request_id,
                    file_id=file_id,
                    data=tile_data,
                    compression_type=compression_type,
                    compression_quality=compression_quality,
                    channel=channel,
                    stokes=stokes,
                    x=x,
                    y=y,
                    layer=layer,
                )

                tasks.append(task)

            await asyncio.gather(*tasks)

            self.fm.files[file_id].raster_event.set()

        # tasks = []

        # tile_dict = await self.fm.async_get_tiles(
        #     file_id=file_id,
        #     tiles=tiles,
        #     compression_type=compression_type,
        #     compression_quality=compression_quality,
        #     channel=channel,
        #     stokes=stokes,
        #     time=0,
        #     dtype=np.float32,
        #     semaphore=self.semaphore,
        #     n_jobs=N_JOBS,
        #     use_dask=self.use_dask,
        # )

        # for tile, ires in tile_dict.items():
        #     comp_data, precision, nan_encodings, tile_shape = ires
        #     tasks.append(
        #         self.send_RasterTileData_v3(
        #             request_id=request_id,
        #             file_id=file_id,
        #             tile=tile,
        #             comp_data=comp_data,
        #             precision=precision,
        #             nan_encodings=nan_encodings,
        #             tile_shape=tile_shape,
        #             compression_type=compression_type,
        #             compression_quality=compression_quality,
        #             channel=channel,
        #             stokes=stokes,
        #         )
        #     )

        # await asyncio.gather(*tasks)

        # tasks = []

        # async for tile, ires in self.fm.async_tile_generator(
        #     file_id=file_id,
        #     tiles=tiles,
        #     compression_type=compression_type,
        #     compression_quality=compression_quality,
        #     channel=channel,
        #     stokes=stokes,
        #     time=0,
        #     dtype=np.float32,
        #     semaphore=self.semaphore,
        #     n_jobs=N_JOBS,
        #     use_dask=self.use_dask,
        # ):
        #     comp_data, precision, nan_encodings, tile_shape = ires
        #     tasks.append(
        #         self.send_RasterTileData_v3(
        #             request_id=request_id,
        #             file_id=file_id,
        #             tile=tile,
        #             comp_data=comp_data,
        #             precision=precision,
        #             nan_encodings=nan_encodings,
        #             tile_shape=tile_shape,
        #             compression_type=compression_type,
        #             compression_quality=compression_quality,
        #             channel=channel,
        #             stokes=stokes,
        #         )
        #     )

        # await asyncio.gather(*tasks)

        dt = (perf_counter_ns() - t0) / 1e6

        # RasterTileSync
        resp_sync.tile_count = len(tiles)
        resp_sync.end_sync = True

        # Send message
        event_type = CARTA.EventType.RASTER_TILE_SYNC
        message = self.encode_message(event_type, request_id, resp_sync)
        self.queue.put_nowait(message)

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
        res = await asyncio.to_thread(
            compute_tile, data, compression_type, compression_quality
        )
        comp_data, precision, nan_encodings, tile_shape = res

        tile_height, tile_width = tile_shape

        await asyncio.sleep(0)

        # RasterTileData
        resp_data = CARTA.RasterTileData()
        resp_data.file_id = file_id
        resp_data.channel = channel
        resp_data.stokes = stokes
        resp_data.compression_type = compression_type
        resp_data.compression_quality = precision
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
        self.queue.put_nowait(message)

        return None

    async def send_RasterTileData_v2(
        self,
        request_id: int,
        file_id: int,
        tile: int,
        compression_type: int,
        compression_quality: int,
        channel: int = 0,
        stokes: int = 0,
        use_dask: bool = False,
    ) -> None:
        # Get tile data
        res = await self.fm.async_get_tile(
            file_id=file_id,
            tile=tile,
            compression_type=compression_type,
            compression_quality=compression_quality,
            channel=channel,
            stokes=stokes,
            time=0,
            dtype=np.float32,
            semaphore=self.semaphore,
            n_jobs=N_JOBS,
            use_dask=use_dask,
        )

        comp_data, precision, nan_encodings, tile_shape = res

        x, y, layer = decode_tile_coord(tile)
        tile_height, tile_width = tile_shape

        # RasterTileData
        resp_data = CARTA.RasterTileData()
        resp_data.file_id = file_id
        resp_data.channel = channel
        resp_data.stokes = stokes
        resp_data.compression_type = compression_type
        resp_data.compression_quality = precision
        resp_data.sync_id = file_id + 1
        # resp_data.animation_id = 0

        tile = CARTA.TileData()
        tile.width = tile_width
        tile.height = tile_height
        tile.image_data = comp_data
        tile.nan_encodings = nan_encodings
        tile.x = x
        tile.y = y
        tile.layer = layer

        resp_data.tiles.append(tile)

        # Send message
        event_type = CARTA.EventType.RASTER_TILE_DATA
        message = self.encode_message(event_type, request_id, resp_data)
        self.queue.put_nowait(message)

        return None

    async def send_RasterTileData_v3(
        self,
        request_id: int,
        file_id: int,
        tile: int,
        comp_data: np.ndarray,
        precision: int,
        nan_encodings: np.ndarray,
        tile_shape: Tuple[int, int],
        compression_type: int,
        compression_quality: int,
        channel: int = 0,
        stokes: int = 0,
    ) -> None:
        clog.debug("Use send_RasterTileData_v3")

        x, y, layer = decode_tile_coord(tile)
        tile_height, tile_width = tile_shape

        if precision > compression_quality:
            pflog.debug(
                f"Upgraded precision to {precision} "
                f"(originally requested precision: {compression_quality})."
            )

        # RasterTileData
        resp_data = CARTA.RasterTileData()
        resp_data.file_id = file_id
        resp_data.channel = channel
        resp_data.stokes = stokes
        resp_data.compression_type = compression_type
        resp_data.compression_quality = precision
        resp_data.sync_id = file_id + 1
        # resp_data.animation_id = 0

        tile = CARTA.TileData()
        tile.width = tile_width
        tile.height = tile_height
        tile.image_data = comp_data
        tile.nan_encodings = nan_encodings
        tile.x = x
        tile.y = y
        tile.layer = layer

        resp_data.tiles.append(tile)

        # Send message
        event_type = CARTA.EventType.RASTER_TILE_DATA
        message = self.encode_message(event_type, request_id, resp_data)
        self.queue.put_nowait(message)

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
        await self.fm.files[file_id].hist_event.wait()
        # This is to switch the event loop to send the histogram
        await asyncio.sleep(0)

        channel = self.fm.files[file_id].channel
        stokes = self.fm.files[file_id].stokes

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
            self.fm.files[file_id].channel = channel
            self.fm.files[file_id].stokes = stokes

        # RegionHistogramData
        await self.send_RegionHistogramData(
            request_id=0,
            file_id=file_id,
            region_id=-1,
            channel=channel,
            stokes=stokes,
        )

        # RasterTile
        self.fm.files[file_id].raster_event.clear()
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
        _, _, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        region_id = obj.region_id
        spatial_profiles = obj.spatial_profiles

        # Skip closed file
        if file_id not in self.fm.files:
            return None

        # Not implemented for regions yet
        if region_id > 0:
            return None

        to_send = False
        params_for_sending = {}
        shape = self.fm.files[file_id].img_shape
        img_shape = {"x": shape[1], "y": shape[0]}

        async with self.lock:
            # Process spatial profiles and update dict
            for p in spatial_profiles:
                start = int(p.start)
                end = int(p.end)
                mip = int(p.mip)
                width = int(p.width)
                coord = p.coordinate

                prev_start = self.fm.files[file_id].spat_req[coord]["start"]
                prev_end = self.fm.files[file_id].spat_req[coord]["end"]
                prev_mip = self.fm.files[file_id].spat_req[coord]["mip"]
                prev_width = self.fm.files[file_id].spat_req[coord]["width"]

                if (
                    start != prev_start
                    or end != prev_end
                    or mip != prev_mip
                    or width != prev_width
                ):
                    to_send = True
                    self.fm.files[file_id].spat_req[coord] = {
                        "start": start,
                        "end": end or img_shape[coord],
                        "mip": mip,
                        "width": width,
                    }

            # Check if we should send data
            x, y, _ = self.fm.files[file_id].cursor_coords
            if to_send and x is not None and y is not None:
                # Read parameters needed for sending within the lock
                sprx = self.fm.files[file_id].spat_req["x"]
                spry = self.fm.files[file_id].spat_req["y"]
                channel = self.fm.files[file_id].channel
                stokes = self.fm.files[file_id].stokes
                params_for_sending = {
                    "x": x,
                    "y": y,
                    "sprx": sprx,
                    "spry": spry,
                    "channel": channel,
                    "stokes": stokes,
                }
            else:
                to_send = False

        if to_send and self.fm.files[file_id].raster_event.is_set():
            # Send spatial profile data outside the lock
            sprx = params_for_sending["sprx"]
            spry = params_for_sending["spry"]
            await self.send_SpatialProfileData(
                request_id=0,
                file_id=file_id,
                slice_x=slice(sprx["start"], sprx["end"]),
                slice_y=slice(spry["start"], spry["end"]),
                mip=sprx["mip"],
                x=params_for_sending["x"],
                y=params_for_sending["y"],
                channel=params_for_sending["channel"],
                stokes=params_for_sending["stokes"],
            )

        return None

    async def do_SetCursor(self, message: bytes) -> None:
        # Decode message
        _, _, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        point = obj.point
        # spatial_requirements = obj.spatial_requirements

        # Check boundary
        shape = self.fm.files[file_id].img_shape
        x, y = int(point.x), int(point.y)
        if not (0 <= x < shape[1] and 0 <= y < shape[0]):
            return

        params_for_sending = {}
        send_spectral_profile = False

        async with self.lock:
            cursor_token = perf_counter_ns()
            self.fm.files[file_id].cursor_coords = [x, y, cursor_token]
            sprx = self.fm.files[file_id].spat_req["x"]
            spry = self.fm.files[file_id].spat_req["y"]
            channel = self.fm.files[file_id].channel
            stokes = self.fm.files[file_id].stokes

            params_for_sending = {
                "slice_x": slice(sprx["start"], sprx["end"]),
                "slice_y": slice(spry["start"], spry["end"]),
                "mip": sprx["mip"],
                "channel": channel,
                "stokes": stokes,
                "cursor_token": cursor_token,
            }
            send_spectral_profile = self.spec_prof_cursor_on

        if self.fm.files[file_id].raster_event.is_set():
            # Send spatial profile data
            await self.send_SpatialProfileData(
                request_id=0,
                file_id=file_id,
                x=x,
                y=y,
                **params_for_sending,
            )

            # Send spectral profile if enabled
            if send_spectral_profile:
                await self.send_SpectralProfileData(
                    request_id=0,
                    file_id=file_id,
                    region_id=0,
                    x=x,
                    y=y,
                    stats_type=2,
                    token=cursor_token,
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
        cursor_token: int | None = None,
    ) -> None:
        t0 = perf_counter_ns()

        # Get data
        shape = self.fm.files[file_id].img_shape
        use_dask = self.fm.files[file_id].use_dask
        data = await self.fm.async_get_channel_mip(
            file_id,
            channel,
            stokes,
            mip=mip,
            dtype=np.float32,
            semaphore=self.semaphore,
            use_dask=use_dask,
            return_future=True,
        )

        start = [slice_x.start, slice_y.start]
        stop = [slice_x.stop, slice_y.stop]

        if mip > 1:
            mx = x // mip
            my = y // mip
            sx1 = start[0] // mip if start[0] is not None else 0
            sx2 = stop[0] // mip if stop[0] is not None else shape[1]
            sy1 = start[1] // mip if start[1] is not None else 0
            sy2 = stop[1] // mip if stop[1] is not None else shape[0]
            slice_x = slice(sx1, sx2)
            slice_y = slice(sy1, sy2)
        else:
            mx = x
            my = y

        # Check if x and y are valid and inside data
        if not (0 <= mx < data.shape[1] and 0 <= my < data.shape[0]):
            return None

        if isinstance(data, da.Array):
            # Compute tasks
            futures = self.client.compute(
                [data[my, mx], data[my, slice_x], data[slice_y, mx]]
            )

            # Check if this is still the current task during computation
            current_token = self.fm.files[file_id].cursor_coords[2]
            if cursor_token is not None and cursor_token != current_token:
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

                # Check if this is still the current task after computation
                current_token = self.fm.files[file_id].cursor_coords[2]
                if cursor_token is not None and cursor_token != current_token:
                    # This task is no longer the current task
                    # Cancel futures and abort
                    pflog.debug("Discarding obsolete spatial profile")
                    return None
            except Exception as e:
                # Handle cancellation or other exceptions
                msg = "Dask computation for spatial profile failed or was cancelled: "
                msg += str(e)
                pflog.debug(msg)
                return None

            value = float(value)
            x_profile = x_profile.tobytes()
            y_profile = y_profile.tobytes()
        else:
            value = float(data[my, mx])
            x_profile = data[my, slice_x].tobytes()
            y_profile = data[slice_y, mx].tobytes()

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
        if start[0]:
            sp.start = start[0]
        if stop[0]:
            sp.end = stop[0]
        sp.mip = mip
        sp.raw_values_fp32 = x_profile
        resp.profiles.append(sp)

        sp = CARTA.SpatialProfile()
        sp.coordinate = "y"
        if start[1]:
            sp.start = start[1]
        if stop[1]:
            sp.end = stop[1]
        sp.mip = mip
        sp.raw_values_fp32 = y_profile
        resp.profiles.append(sp)

        # Encode message
        event_type = CARTA.EventType.SPATIAL_PROFILE_DATA
        message = self.encode_message(event_type, request_id, resp)

        # Check if this is still the current task before sending
        current_token = self.fm.files[file_id].cursor_coords[2]
        if cursor_token is not None and cursor_token != current_token:
            # This task is no longer the current task
            # Cancel futures and abort
            pflog.debug("Discarding obsolete spatial profile")
            return None

        # Send message
        self.queue.put_nowait(message)

        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Fill spatial profile in {dt:.3f} ms"
        pflog.debug(msg)

        return None

    async def dask_executor_for_region(self, input_queue, output_queue):
        while True:
            item = await input_queue.get()
            if item is None:
                input_queue.task_done()
                break
            future, info = item
            result = await self.client.compute(future)
            output_queue.put_nowait((result, info))
            input_queue.task_done()

    async def send_SpectralProfileData(
        self,
        request_id: int,
        file_id: int,
        region_id: int,
        region_info: CARTA.RegionInfo | None = None,
        x: int | None = None,
        y: int | None = None,
        stokes: int = 0,
        time: int = 0,
        stats_type: int = 2,
        token: int | None = None,
    ) -> None:
        if region_id == 0:
            # Cursor
            is_point = True
        elif (
            region_info is not None
            and region_info.region_type == CARTA.RegionType.POINT
        ):
            # Point region
            points = region_info.control_points
            x, y = round(points[0].x), round(points[0].y)
            is_point = True
        else:
            # Other regions
            is_point = False

        # Point/cursor spectral profile
        if is_point:
            await self.send_SpectralProfileData_point(
                request_id=request_id,
                file_id=file_id,
                region_id=region_id,
                x=x,
                y=y,
                stokes=stokes,
                time=time,
                stats_type=stats_type,
                token=token,
            )
            return None

        t0 = perf_counter_ns()

        if self.region_dict[region_id].profiles is not None:
            # Get spectral profile
            sp = CARTA.SpectralProfile()
            sp.coordinate = "z"
            sp.stats_type = stats_type
            profile = self.region_dict[region_id].profiles[stats_type - 2]
            sp.raw_values_fp64 = profile.tobytes()

            # Create response object
            resp = CARTA.SpectralProfileData()
            resp.file_id = file_id
            resp.region_id = region_id
            resp.stokes = stokes
            resp.progress = 1.0
            resp.profiles.append(sp)

            # Send message
            event_type = CARTA.EventType.SPECTRAL_PROFILE_DATA
            message = self.encode_message(event_type, request_id, resp)
            self.queue.put_nowait(message)

            dt = (perf_counter_ns() - t0) / 1e6
            msg = f"Fill region spectral profile in {dt:.3f} ms"
            pflog.debug(msg)

            return None

        # Initilize spectral profile
        dtype = np.float64
        channel_size = self.fm.files[file_id].sizes["frequency"]
        if channel_size is None:
            return None
        spec_profiles = np.full((9, channel_size), np.nan, dtype=dtype)

        # Get header and region
        hdr = self.fm.files[file_id].header
        region = get_region(region_info)

        # Create spectral profile object
        sp = CARTA.SpectralProfile()
        sp.coordinate = "z"
        sp.stats_type = stats_type

        # Create response object
        resp = CARTA.SpectralProfileData()
        resp.file_id = file_id
        resp.region_id = region_id
        resp.stokes = stokes

        # Set progress parameters
        current_channel = 0
        progress = 0.0
        delta_z = INIT_DELTA_Z
        dt_partial_update = TARGET_PARTIAL_REGION_TIME
        count = 0

        # Get slices and region submask for use_dask is False
        image_shape = self.fm.files[file_id].img_shape
        slicex, slicey, sub_mask = get_region_slices_mask(region, image_shape)

        # Initialize variable executor_task
        executor_task = None

        use_dask = self.fm.files[file_id].use_dask

        while progress < 1.0:
            # Check if region changed
            if token is not None:
                current_token = self.region_dict[region_id].token
                if token != current_token:
                    msg = "Discarding obsolete point spectral profile "
                    pflog.debug(msg)
                    return None

            t_start_slice = perf_counter_ns()

            delta_z = min(delta_z, channel_size - current_channel)
            channel_slice = slice(current_channel, current_channel + delta_z)

            start = channel_slice.start
            stop = channel_size

            if use_dask:
                if count == 8 and (stop - start) / delta_z > 3:
                    # If there are more than 3 chunks to process, process
                    # them in parallel and await the futures in later cycles
                    delta_z = min(delta_z, channel_size - current_channel)

                    input_queue = asyncio.Queue()
                    output_queue = asyncio.Queue()
                    executor_task = asyncio.create_task(
                        self.dask_executor_for_region(
                            input_queue, output_queue
                        )
                    )

                    for istart in range(start, stop, delta_z):
                        istop = min(istart + delta_z, stop)
                        channel_slice = slice(istart, istop)
                        data = await self.fm.async_get_slice(
                            file_id=file_id,
                            channel=channel_slice,
                            stokes=stokes,
                            dtype=dtype,
                            use_dask=True,
                            return_future=True,
                        )
                        future = get_spectral_profile_dask(data, region, hdr)
                        input_queue.put_nowait([future, channel_slice])

                    part_spec_profs, channel_slice = await output_queue.get()
                elif executor_task is not None:
                    part_spec_profs, channel_slice = await output_queue.get()
                else:
                    # Process the data in serial
                    data = await self.fm.async_get_slice(
                        file_id=file_id,
                        channel=channel_slice,
                        stokes=stokes,
                        dtype=dtype,
                        use_dask=True,
                        return_future=True,
                    )
                    part_spec_profs = get_spectral_profile_dask(
                        data, region, hdr
                    )
                    part_spec_profs = await self.client.compute(
                        part_spec_profs
                    )
            else:
                part_spec_profs = await self.fm.async_get_region_spectrum(
                    file_id=file_id,
                    sub_mask=sub_mask,
                    x=slicex,
                    y=slicey,
                    channel=channel_slice,
                    stokes=stokes,
                    time=time,
                    dtype=dtype,
                    semaphore=self.semaphore,
                    n_jobs=N_JOBS,
                    use_dask=False,
                )

            spec_profiles[:, channel_slice] = part_spec_profs

            current_channel = channel_slice.stop
            progress = current_channel / channel_size

            t_end_slice = perf_counter_ns()

            # Adjust delta_z based on time taken
            time_taken_ms = (t_end_slice - t_start_slice) / 1e6
            adjustment_factor = dt_partial_update / time_taken_ms
            delta_z = int(
                max(1, min(delta_z * adjustment_factor, channel_size))
            )

            sp.raw_values_fp64 = spec_profiles[stats_type - 2].tobytes()

            resp.progress = progress
            if len(resp.profiles) > 0:
                resp.profiles.pop()
            resp.profiles.append(sp)

            # Encode message
            event_type = CARTA.EventType.SPECTRAL_PROFILE_DATA
            message = self.encode_message(event_type, request_id, resp)

            # Check if cursor/region changed
            await asyncio.sleep(0)
            if token is not None:
                current_token = self.region_dict[region_id].token
                if token != current_token:
                    msg = "Discarding obsolete point spectral profile "
                    pflog.debug(msg)

                    # Cancel executor task if it exists
                    if executor_task is not None:
                        executor_task.cancel()
                        try:
                            await executor_task
                        except asyncio.CancelledError:
                            pass
                    return None

            # Send message
            self.queue.put_nowait(message)
            await asyncio.sleep(0)

            count += 1

        dt = (perf_counter_ns() - t0) / 1e6
        msg = f"Fill region spectral profile in {dt:.3f} ms"
        pflog.debug(msg)

        async with self.lock:
            self.region_dict[region_id].profiles = spec_profiles

        if executor_task is not None:
            input_queue.put_nowait(None)
            await input_queue.join()
            await output_queue.join()
            await executor_task
        return None

    async def send_SpectralProfileData_point(
        self,
        request_id: int,
        file_id: int,
        region_id: int,
        x: int | None = None,
        y: int | None = None,
        stokes: int = 0,
        time: int = 0,
        stats_type: int = 2,
        token: int | None = None,
    ) -> None:
        t0 = perf_counter_ns()

        # Initilize spectral profile
        dtype = np.float32 if region_id == 0 else np.float64
        channel_size = self.fm.files[file_id].sizes["frequency"]
        if channel_size is None:
            return None
        spec_profile = np.full(channel_size, np.nan, dtype=dtype)

        # Get memmap
        memmap_info = self.fm.files[file_id].memmap_info
        if memmap_info is None:
            memmap = None
        else:
            memmap = np.memmap(**memmap_info)

        # Create spectral profile object
        sp = CARTA.SpectralProfile()
        sp.coordinate = "z"
        sp.stats_type = stats_type

        # Create response object
        resp = CARTA.SpectralProfileData()
        resp.file_id = file_id
        resp.region_id = region_id
        resp.stokes = stokes

        # Set progress parameters
        current_channel = 0
        progress = 0.0
        delta_z = INIT_DELTA_Z

        if region_id == 0:
            dt_partial_update = TARGET_PARTIAL_CURSOR_TIME
        else:
            dt_partial_update = TARGET_PARTIAL_REGION_TIME

        use_dask = self.fm.files[file_id].use_dask

        if use_dask:
            clog.debug("Using Dask to load point spectrum")

        while progress < 1.0:
            # Check if cursor/region changed
            if token is not None:
                if region_id == 0:
                    current_token = self.fm.files[file_id].cursor_coords[2]
                else:
                    current_token = self.region_dict[region_id].token
                if token != current_token:
                    msg = "Discarding obsolete point spectral profile "
                    pflog.debug(msg)
                    return None

            t_start_slice = perf_counter_ns()

            delta_z = min(delta_z, channel_size - current_channel)
            channel_slice = slice(current_channel, current_channel + delta_z)

            part_spec_prof = await self.fm.async_get_point_spectrum(
                file_id=file_id,
                x=x,
                y=y,
                channel=channel_slice,
                stokes=stokes,
                time=time,
                memmap=memmap,
                dtype=dtype,
                semaphore=self.semaphore,
                n_jobs=N_JOBS,
                use_dask=use_dask,
            )
            spec_profile[channel_slice] = part_spec_prof

            current_channel += delta_z
            progress = current_channel / channel_size

            t_end_slice = perf_counter_ns()

            # Adjust delta_z based on time taken
            time_taken_ms = (t_end_slice - t_start_slice) / 1e6
            adjustment_factor = dt_partial_update / time_taken_ms
            delta_z = int(
                max(1, min(delta_z * adjustment_factor, channel_size))
            )

            if region_id == 0:
                sp.raw_values_fp32 = spec_profile.tobytes()
            else:
                sp.raw_values_fp64 = spec_profile.tobytes()

            resp.progress = progress
            if len(resp.profiles) > 0:
                resp.profiles.pop()
            resp.profiles.append(sp)

            # Encode message
            event_type = CARTA.EventType.SPECTRAL_PROFILE_DATA
            message = self.encode_message(event_type, request_id, resp)

            # Check if cursor/region changed
            await asyncio.sleep(0)
            if token is not None:
                if region_id == 0:
                    current_token = self.fm.files[file_id].cursor_coords[2]
                else:
                    current_token = self.region_dict[region_id].token
                if token != current_token:
                    msg = "Discarding obsolete point spectral profile "
                    pflog.debug(msg)
                    return None

            # Send message
            self.queue.put_nowait(message)
            await asyncio.sleep(0)

        dt = (perf_counter_ns() - t0) / 1e6
        msg_add = " cursor" if region_id == 0 else " point"
        msg = f"Fill{msg_add} spectral profile in {dt:.3f} ms"
        pflog.debug(msg)

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

        region_token = perf_counter_ns()

        # Record region
        async with self.lock:
            if region_id not in self.region_dict:
                self.region_dict[region_id] = RegionData(
                    file_id=file_id,
                    region_info=region_info,
                    preview_region=preview_region,
                    profiles=None,
                    token=region_token,
                )
            else:
                self.region_dict[region_id].region_info = region_info
                self.region_dict[region_id].profiles = None
                self.region_dict[region_id].token = region_token

        # Send message
        resp = CARTA.SetRegionAck()
        resp.success = True
        resp.region_id = region_id
        event_type = CARTA.EventType.SET_REGION_ACK
        message = self.encode_message(event_type, request_id, resp)
        self.queue.put_nowait(message)

        # Send spectral profile
        if self.spec_prof_on:
            await self.send_SpectralProfileData(
                request_id,
                file_id,
                region_id,
                region_info,
                stats_type=self.prev_stats_type,
                token=region_token,
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
                x, y, _ = self.fm.files[file_id].cursor_coords
                if x is None or y is None:
                    return None
            else:
                # Region
                region_info = self.region_dict[region_id].region_info
                # stats_type = self.prev_stats_type
                x, y = None, None
                region_token = self.region_dict[region_id].token

        # Send spectral profile
        if self.spec_prof_on or self.spec_prof_cursor_on:
            # Use create_task to avoid blocking the event loop
            asyncio.create_task(
                self.send_SpectralProfileData(
                    request_id=0,
                    file_id=file_id,
                    region_id=region_id,
                    region_info=region_info,
                    stats_type=self.prev_stats_type,
                    x=x,
                    y=y,
                    token=region_token,
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
            self.queue.put_nowait(message)
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

                    file_info = async_get_file_info(item_path, file_type)
                    files.append(file_info)

            files = await asyncio.gather(*files)

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
        self.queue.put_nowait(message)
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
        file_info = await async_get_file_info(file_path, file_type)

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
        self.queue.put_nowait(message)
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
                    token=perf_counter_ns(),
                )
                resp.regions[max_id].CopyFrom(region_info)
                resp.region_styles[max_id].CopyFrom(region_style)

        # Send message
        event_type = CARTA.EventType.IMPORT_REGION_ACK
        message = self.encode_message(event_type, request_id, resp)
        self.queue.put_nowait(message)
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
