import asyncio
import os
import random
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Optional, Tuple

import numpy as np
import pyzfp
from astropy.io import fits
from dask.distributed import Client
from starlette.websockets import WebSocket
from xarray import open_zarr
from xradio.image import load_image

from carta_backend import proto as CARTA
from carta_backend.log import logger
from carta_backend.proto.enums_pb2 import EventType, SessionType
from carta_backend.region import get_region_slices_mask, get_spectral_profile
from carta_backend.utils import (get_directory_info, get_file_info,
                                 get_file_info_extended,
                                 get_header_from_xradio,
                                 get_nan_encodings_block, get_system_info,
                                 load_fits_data, load_xradio_data,
                                 numba_histogram)

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")

PROTO_FUNC_MAP = {
    1: CARTA.RegisterViewer,
    2: CARTA.FileListRequest,
    3: CARTA.FileInfoRequest,
    4: CARTA.OpenFile,
    6: CARTA.SetImageChannels,
    7: CARTA.SetCursor,
    8: CARTA.SetSpatialRequirements,
    9: CARTA.SetHistogramRequirements,
    10: CARTA.SetStatsRequirements,
    11: CARTA.SetRegion,
    12: CARTA.RemoveRegion,
    13: CARTA.CloseFile,
    14: CARTA.SetSpectralRequirements,
    15: CARTA.StartAnimation,
    16: CARTA.StartAnimationAck,
    17: CARTA.StopAnimation,
    18: CARTA.RegisterViewerAck,
    19: CARTA.FileListResponse,
    20: CARTA.FileInfoResponse,
    21: CARTA.OpenFileAck,
    22: CARTA.SetRegionAck,
    23: CARTA.RegionHistogramData,
    25: CARTA.SpatialProfileData,
    26: CARTA.SpectralProfileData,
    27: CARTA.RegionStatsData,
    28: CARTA.ErrorData,
    29: CARTA.AnimationFlowControl,
    30: CARTA.AddRequiredTiles,
    31: CARTA.RemoveRequiredTiles,
    32: CARTA.RasterTileData,
    33: CARTA.RegionListRequest,
    34: CARTA.RegionListResponse,
    35: CARTA.RegionFileInfoRequest,
    36: CARTA.RegionFileInfoResponse,
    37: CARTA.ImportRegion,
    38: CARTA.ImportRegionAck,
    39: CARTA.ExportRegion,
    40: CARTA.ExportRegionAck,
    45: CARTA.SetContourParameters,
    46: CARTA.ContourImageData,
    47: CARTA.ResumeSession,
    48: CARTA.ResumeSessionAck,
    49: CARTA.RasterTileSync,
    50: CARTA.CatalogListRequest,
    51: CARTA.CatalogListResponse,
    52: CARTA.CatalogFileInfoRequest,
    53: CARTA.CatalogFileInfoResponse,
    54: CARTA.OpenCatalogFile,
    55: CARTA.OpenCatalogFileAck,
    56: CARTA.CloseCatalogFile,
    57: CARTA.CatalogFilterRequest,
    58: CARTA.CatalogFilterResponse,
    59: CARTA.ScriptingRequest,
    60: CARTA.ScriptingResponse,
    61: CARTA.MomentRequest,
    62: CARTA.MomentResponse,
    63: CARTA.MomentProgress,
    64: CARTA.StopMomentCalc,
    65: CARTA.SaveFile,
    66: CARTA.SaveFileAck,
    69: CARTA.ConcatStokesFiles,
    70: CARTA.ConcatStokesFilesAck,
    71: CARTA.ListProgress,
    72: CARTA.StopFileList,
    75: CARTA.PvRequest,
    76: CARTA.PvResponse,
    77: CARTA.PvProgress,
    78: CARTA.StopPvCalc,
    79: CARTA.FittingRequest,
    80: CARTA.FittingResponse,
    81: CARTA.SetVectorOverlayParameters,
    82: CARTA.VectorOverlayTileData,
    83: CARTA.FittingProgress,
    84: CARTA.StopFitting,
    85: CARTA.PvPreviewData,
    86: CARTA.StopPvPreview,
    87: CARTA.ClosePvPreview,
    88: CARTA.RemoteFileRequest,
    89: CARTA.RemoteFileResponse,
    90: CARTA.ChannelMapFlowControl,
}

EVENT_TYPE_MAP = {v: k for k, v in EventType.items()}


class Session:
    # Add a mapping dict from event_id to method in Session
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
    }

    def __init__(
            self,
            session_id: int = 0,
            top_level_folder: str = None,
            starting_folder: str = None,
            lock: asyncio.Lock = None,
            ws: WebSocket = None,
            dask_scheduler: str = None,
            client: Client = None,
    ):
        self.session_id = session_id
        self.top_level_folder = Path(top_level_folder)
        self.starting_folder = Path(starting_folder)
        self.lock = lock or asyncio.Lock()
        self.ws = ws
        self.dask_scheduler = dask_scheduler
        self.client = client

        # Set up message queue
        self.queue = asyncio.Queue()
        self.sender_task = asyncio.create_task(self.send_message_worker())
        # For concurrent processing (for future use)
        # self.task_group = asyncio.TaskGroup()
        # Send message asynchronously
        # self.task_group.create_task(self._send_message(res1))

        # FileList
        self.flag_stop_file_list = False

        # OpenFile
        self.open_file_dict = {}

        # Channel & Stokes
        self.channel_stokes = [0, 0]

        # SpatialRequirements
        self.spat_dict = {}

        # SpectralRequirements
        self.spec_prof_on = False
        self.prev_stats_type = None

        # Cursor
        self.cursor_dict = {}

        # Region
        self.region_dict = {}

    async def send_message_worker(self):
        """Continuously sends messages from the queue."""
        while True:
            message = await self.queue.get()
            # This is to close the sender task
            if message is None:
                break
            await self._send_message(message)

    async def _send_message(self, message):
        # This message should be encoded.
        await self.ws.send_bytes(message)
        # Get event info from received message
        _, event_type = self.get_event_info(message)
        ptlog.debug(f"[protocol] ==> {event_type}")

    async def start_dask_client(self) -> None:
        self.client = await Client(
            address=self.dask_scheduler,
            asynchronous=True
        )
        clog.info("Dask client started.")
        clog.info(f"Dask scheduler served at {self.client.scheduler.address}")
        clog.info(f"Dask dashboard link: {self.client.dashboard_link}")

    async def close(self):
        # Send stop signal to the sender task
        await self.queue.put(None)
        await self.sender_task

        # Close dask client
        if self.client is not None:
            await self.client.close()
            self.client = None

    async def take_action(self, message: bytes) -> None:
        # Get event info from received message
        event_id, event_type = self.get_event_info(message)
        ptlog.debug(f"[protocol] <== {event_type}")

        # Get corresponding handler (e.g., do_FileListRequest)
        handler = self.handler_map.get(event_id, None)
        if handler is None:
            ptlog.error(f"[protocol] No handler for event {event_type}")
            return None

        # Call handler
        handler = getattr(self, handler)
        await handler(message)

    def get_event_info(self, message: bytes) -> Tuple[int, str]:
        event_id = int.from_bytes(message[0:1], byteorder="little")
        event_type = EVENT_TYPE_MAP.get(event_id, None)
        return event_id, event_type

    def decode_message(
            self,
            message: bytes
    ) -> Optional[Tuple[int, int, Any]]:

        event_id = int.from_bytes(message[0:1], byteorder="little")
        request_id = int.from_bytes(message[1:8], byteorder="little")

        func = PROTO_FUNC_MAP.get(event_id, None)

        if func is None:
            return None

        obj = func()
        obj.ParseFromString(message[8:])

        return event_id, request_id, obj

    def encode_message(
            self,
            event_id: int,
            request_id: int,
            obj: Any
    ) -> bytes:
        message = bytes([event_id])
        message += request_id.to_bytes(7, byteorder="little")
        message += obj.SerializeToString()
        return message

    async def do_template(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

        # Extract parameters
        pass

        # Create response object
        pass

        # Send message
        pass

    async def do_RegisterViewer(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

        # Extract parameters
        session_id = obj.session_id
        # api_key = obj.api_key
        # client_feature_flags = obj.client_feature_flags

        # Create response object
        response = CARTA.RegisterViewerAck()

        if session_id == 0:
            # Create a new session
            # Generate a nine digit session ID
            session_id = random.randint(100000000, 999999999)
            async with self.lock:
                self.session_id = session_id
            response.session_id = session_id
            response.success = True
            response.message = ""
            response.session_type = SessionType.NEW
            response.platform_strings.update(get_system_info())
        else:
            # Resume an existing session
            # Not implemented
            response.success = False
            response.message = "Not implemented"

        client_ip = self.ws.client.host
        msg = f"Session {self.session_id:09d} [{client_ip}] Connected."
        clog.info(msg)

        # Start Dask client if not started
        if self.client is None:
            await self.start_dask_client()

        # Send message
        event_id = EventType.REGISTER_VIEWER_ACK
        message = self.encode_message(event_id, request_id, response)
        await self.queue.put(message)

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
        event_id, request_id, obj = self.decode_message(message)

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

        def is_accessible(path):
            try:
                path.is_dir()
                return True
            except (PermissionError, OSError, TimeoutError):
                return False

        # Check if directory is accessible
        if not is_accessible(directory):
            response.success = False
            msg = f"Directory '{directory}' is not accessible"
            response.message = msg
            event_id = EventType.FILE_LIST_RESPONSE
            message = self.encode_message(event_id, request_id, response)
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
                        event_id = EventType.FILE_LIST_RESPONSE
                        # Encode message
                        message = self.encode_message(
                            event_id, request_id, response)
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

        event_id = EventType.FILE_LIST_RESPONSE
        message = self.encode_message(event_id, request_id, response)
        await self.queue.put(message)
        return None

    async def do_StopFileList(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

        # Extract parameters
        # file_list_type = obj.file_list_type

        # Set stop flag
        async with self.lock:
            self.flag_stop_file_list = True

        return None

    async def do_FileInfoRequest(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

        # Extract parameters
        directory = obj.directory
        file = obj.file
        hdu = obj.hdu
        # support_aips_beam = obj.support_aips_beam

        # Set parameters
        directory = self.top_level_folder / directory
        file_path = str(directory / file)
        if hdu == "":
            hdu_index = 0
        else:
            hdu_index = int(hdu)

        # Get file info
        file_info = get_file_info(file_path)

        # Create response object
        response = CARTA.FileInfoResponse()

        # Read headers
        if file_info.type == CARTA.FileType.FITS:
            with fits.open(file_path) as hdul:
                hdr = hdul[hdu_index].header
        elif file_info.type == CARTA.FileType.CASA:
            # Currently zarr
            xarr = open_zarr(file_path)
            hdr = get_header_from_xradio(xarr)
            xarr.close()

        response.success = True
        response.file_info.CopyFrom(file_info)

        fex_dict = get_file_info_extended(hdr, hdu_index, file)

        for k, v in fex_dict.items():
            response.file_info_extended[k].CopyFrom(v)

        # Send message
        event_id = EventType.FILE_INFO_RESPONSE
        message = self.encode_message(event_id, request_id, response)
        await self.queue.put(message)
        return None

    async def do_CloseFile(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id

        # If file is open, close it
        if file_id in list(self.open_file_dict.keys()):
            # Close file
            self.open_file_dict[file_id][0].close()
            async with self.lock:
                del self.open_file_dict[file_id]
        # Close all files
        elif file_id == -1:
            for file_id in list(self.open_file_dict.keys()):
                self.open_file_dict[file_id][0].close()
                async with self.lock:
                    del self.open_file_dict[file_id]

        return None

    async def do_OpenFile(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

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
        hdu_index = int(hdu)
        file_info = get_file_info(file_path)

        # Open file
        if file_id not in self.open_file_dict:
            async with self.lock:
                if file_info.type == CARTA.FileType.FITS:
                    self.open_file_dict[file_id] = [
                        fits.open(file_path, memmap=True), hdu_index]
                elif file_info.type == CARTA.FileType.CASA:
                    xarr = load_image(file_path)
                    self.open_file_dict[file_id] = [
                        xarr, None]

        hdul, hdu_index = self.open_file_dict[file_id]

        if hdu_index is not None:
            hdr = hdul[hdu_index].header
        else:
            hdr = get_header_from_xradio(hdul)
            hdu_index = 0

        # OpenFileAck
        # Create response object
        response = CARTA.OpenFileAck()
        response.success = True
        response.file_id = file_id
        response.file_info.CopyFrom(file_info)
        fex_dict = get_file_info_extended(hdr, hdu_index, file_name)
        response.file_info_extended.CopyFrom(fex_dict[str(hdu_index)])

        # Not implemented yet
        # response.beam_table

        # Send message
        event_id = EventType.OPEN_FILE_ACK
        message = self.encode_message(event_id, request_id, response)
        await self.queue.put(message)

    async def send_RegionHistogramData(
        self,
        request_id: int,
        file_id: int,
        region_id: int,
        channel: int = 0,
        stokes: int = 0,
    ) -> None:

        # Load image
        t0 = perf_counter_ns()
        hdul, hdu_index = self.open_file_dict[file_id]

        if hdu_index is not None:
            data = load_fits_data(hdul, hdu_index, channel, stokes)
        else:
            # data = await async_load_xradio_data(hdul, channel, stokes,
            #                                     client=self.client)
            data = load_xradio_data(hdul, channel, stokes)

        dt = (perf_counter_ns() - t0) / 1e6
        mpix_s = data.size / 1e6 / dt * 1000
        msg = f"Load {data.shape[0]}x{data.shape[1]} image to "
        msg += f"cache in {dt:.3f} ms at {mpix_s:.3f} MPix/s"
        clog.debug(msg)

        t0 = perf_counter_ns()

        # RegionHistogramData
        # Not fully implemented
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

        # # Get data
        # hdul, hdu_index = self.open_file_dict[file_id]
        # ndim = hdul[hdu_index].data.ndim

        # if ndim == 2:
        #     data = hdul[hdu_index].data
        # elif ndim == 3:
        #     data = hdul[hdu_index].data[channel]
        # elif ndim == 4:
        #     data = hdul[hdu_index].data[stokes][channel]

        # Calculate histogram
        nbins = int(max(np.sqrt(data.shape[0] * data.shape[1]), 2.0))
        bin_min, bin_max = np.nanmin(data), np.nanmax(data)
        bin_width = (bin_max - bin_min) / nbins
        hist = numba_histogram(
            data.astype('<f4').ravel(), nbins, bin_min, bin_max)
        histogram = CARTA.Histogram()
        histogram.num_bins = nbins
        histogram.bin_width = bin_width
        histogram.first_bin_center = bin_min + bin_width / 2
        histogram.bins.extend(hist)
        histogram.mean = np.nanmean(data)
        histogram.std_dev = np.nanstd(data)
        response.histograms.CopyFrom(histogram)

        # Send message
        event_id = EventType.REGION_HISTOGRAM_DATA
        message = self.encode_message(event_id, request_id, response)

        dt = (perf_counter_ns() - t0) / 1e6
        mpix_s = data.size / 1e6 / dt * 1000
        msg = f"Fill image histogram in {dt:.3f} ms at {mpix_s:.3f} MPix/s"
        pflog.debug(msg)

        await self.queue.put(message)

    async def send_RasterTileData(
        self,
        request_id: int,
        file_id: int,
        compression_type: int,
        compression_quality: int,
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
        resp_sync.tile_count = 1

        # Send message
        event_id = EventType.RASTER_TILE_SYNC
        message = self.encode_message(event_id, request_id, resp_sync)
        await self.queue.put(message)

        # Get data
        hdul, hdu_index = self.open_file_dict[file_id]

        if hdu_index is not None:
            data = load_fits_data(hdul, hdu_index, channel, stokes)
        else:
            data = load_xradio_data(hdul, channel, stokes, client=self.client)

        # Compress data
        t0 = perf_counter_ns()
        if compression_type == CARTA.CompressionType.ZFP:
            comp_data = pyzfp.compress(
                data.astype('<f4'),
                precision=compression_quality)
        elif compression_type == CARTA.CompressionType.SZ:
            # Not implemented yet
            comp_data = data
        else:
            comp_data = data
        dt = (perf_counter_ns() - t0) / 1e6
        tile_width, tile_height = data.shape
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
        tile.width = data.shape[0]
        tile.height = data.shape[1]
        tile.image_data = np.asarray(comp_data).tobytes()
        tile.nan_encodings = get_nan_encodings_block(data)

        resp_data.tiles.append(tile)

        # Send message
        event_id = EventType.RASTER_TILE_DATA
        message = self.encode_message(event_id, request_id, resp_data)
        await self.queue.put(message)

        # RasterTileSync
        resp_sync.end_sync = True

        # Send message
        event_id = EventType.RASTER_TILE_SYNC
        message = self.encode_message(event_id, request_id, resp_sync)
        await self.queue.put(message)

        return None

    async def do_AddRequiredTiles(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        # tiles = obj.tiles
        compression_type = obj.compression_type
        compression_quality = obj.compression_quality
        # current_tiles = obj.current_tiles

        # RegionHistogramData
        await self.send_RegionHistogramData(
            request_id,
            file_id,
            region_id=-1,
            channel=0,
            stokes=0
        )

        # RasterTile
        await self.send_RasterTileData(
            request_id,
            file_id,
            compression_type,
            compression_quality,
            channel=0,
            stokes=0
        )

        return None

    async def do_SetImageChannels(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

        # Extract parameters
        # Main obj
        file_id = obj.file_id
        channel = obj.channel
        stokes = obj.stokes
        required_tiles = obj.required_tiles
        # channel_range = obj.channel_range
        # current_range = obj.current_range
        # channel_map_enabled = obj.channel_map_enabled
        # Tiles
        # tiles = required_tiles.tiles
        compression_type = required_tiles.compression_type
        compression_quality = required_tiles.compression_quality

        # Update channel and stokes
        async with self.lock:
            self.channel_stokes = [channel, stokes]

        # RegionHistogramData
        await self.send_RegionHistogramData(
            request_id,
            file_id,
            region_id=-1,
            channel=channel,
            stokes=stokes
        )

        # RasterTile
        await self.send_RasterTileData(
            request_id,
            file_id,
            compression_type,
            compression_quality,
            channel=channel,
            stokes=stokes
        )

        return None

    async def do_SetSpatialRequirements(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

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
                    "x": [0, None, 1, 0], "y": [0, None, 1, 0]}

        to_send = False

        async with self.lock:
            for p in spatial_profiles:
                start = int(p.start)
                end = int(p.end)
                mip = int(p.mip)
                width = p.width

                if (start == 0) and (end == 0):
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

            if to_send:
                # Read parameters
                x, y = self.cursor_dict[file_id]
                sprx = self.spat_dict[file_id]["x"]
                spry = self.spat_dict[file_id]["y"]
                channel, stokes = self.channel_stokes

        if to_send:
            # Send spatial profile data
            await self.send_SpatialProfileData(
                request_id,
                file_id,
                slice_x=slice(sprx[0], sprx[1]),
                slice_y=slice(spry[0], spry[1]),
                mip=sprx[2],
                x=x,
                y=y,
                channel=channel,
                stokes=stokes
            )

        return None

    async def do_SetCursor(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        point = obj.point
        # spatial_requirements = obj.spatial_requirements

        # Record cursor and read other parameters
        async with self.lock:
            x, y = int(point.x), int(point.y)
            self.cursor_dict[file_id] = [x, y]
            sprx = self.spat_dict[file_id]["x"]
            spry = self.spat_dict[file_id]["y"]
            channel, stokes = self.channel_stokes

        # Send spatial profile data
        await self.send_SpatialProfileData(
            request_id,
            file_id,
            slice_x=slice(sprx[0], sprx[1]),
            slice_y=slice(spry[0], spry[1]),
            mip=sprx[2],
            x=x,
            y=y,
            channel=channel,
            stokes=stokes
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
    ) -> None:

        t0 = perf_counter_ns()

        # Get data
        hdul, hdu_index = self.open_file_dict[file_id]

        if hdu_index is not None:
            data = load_fits_data(hdul, hdu_index, channel, stokes)
        else:
            data = load_xradio_data(hdul, channel, stokes, client=self.client)

        value = data[y, x]

        spx = CARTA.SpatialProfile()
        spx.coordinate = "x"
        spx.start = slice_x.start
        spx.end = slice_x.stop if slice_x.stop is not None else data.shape[1]
        spx.mip = mip
        spx.raw_values_fp32 = data[y, slice_x].astype('<f4').tobytes()

        spy = CARTA.SpatialProfile()
        spy.coordinate = "y"
        spy.start = slice_y.start
        spy.end = slice_y.stop if slice_y.stop is not None else data.shape[0]
        spy.mip = mip
        spy.raw_values_fp32 = data[slice_y, x].astype('<f4').tobytes()

        resp = CARTA.SpatialProfileData()
        resp.file_id = file_id
        if region_id is not None:
            resp.region_id = region_id
        resp.x = x
        resp.y = y
        resp.value = value
        resp.channel = channel
        resp.stokes = stokes
        resp.profiles.append(spx)
        resp.profiles.append(spy)

        # Send message
        event_id = EventType.SPATIAL_PROFILE_DATA
        message = self.encode_message(event_id, request_id, resp)
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
        region_info: CARTA.RegionInfo,
        stats_type: int
    ) -> None:

        # Get region slices and mask
        slicex, slicey, mask = get_region_slices_mask(region_info)

        # Get data
        hdul, hdu_index = self.open_file_dict[file_id]
        if hdu_index is not None:
            # data = load_fits_data(hdul, hdu_index, channel, stokes)
            data = hdul[hdu_index].data[0][:, slicey, slicex]
        else:
            # data = load_xradio_data(hdul, channel, stokes,
            #                         client=self.client)
            data = hdul['SKY'].isel(
                polarization=0, time=0).values[:, slicey, slicex]

        # Get spectral profile
        spec_profile = get_spectral_profile(data, mask, stats_type)
        sp = CARTA.SpectralProfile()
        sp.coordinate = "z"
        sp.stats_type = stats_type
        sp.raw_values_fp64 = spec_profile.astype('<f8').tobytes()

        # Create response object
        resp = CARTA.SpectralProfileData()
        resp.file_id = file_id
        resp.region_id = region_id
        resp.stokes = 0
        resp.progress = 1
        resp.profiles.append(sp)

        # Send message
        event_id = EventType.SPECTRAL_PROFILE_DATA
        message = self.encode_message(event_id, request_id, resp)
        await self.queue.put(message)

        return None

    async def do_SetRegion(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

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
                self.region_dict[region_id] = {
                    "file_id": file_id,
                    "region_info": region_info,
                    "preview_region": preview_region
                }
            else:
                self.region_dict[region_id]["region_info"] = region_info

        # Send message
        resp = CARTA.SetRegionAck()
        resp.success = True
        resp.region_id = region_id
        event_id = EventType.SET_REGION_ACK
        message = self.encode_message(event_id, request_id, resp)
        await self.queue.put(message)

        # Send spectral profile
        if self.spec_prof_on:
            await self.send_SpectroProfileData(
                request_id,
                file_id,
                region_id,
                region_info,
                self.prev_stats_type
            )

        return None

    async def do_SetSpectralRequirements(self, message: bytes) -> None:
        # Decode message
        event_id, request_id, obj = self.decode_message(message)

        # Extract parameters
        file_id = obj.file_id
        region_id = obj.region_id
        if len(obj.spectral_profiles) == 0:
            async with self.lock:
                self.spec_prof_on = False
            return None
        else:
            spectral_profile = obj.spectral_profiles[0]
            coordinate = spectral_profile.coordinate
            stats_type = spectral_profile.stats_types[0]
            async with self.lock:
                self.spec_prof_on = True
                self.prev_stats_type = stats_type

        # Get region info
        async with self.lock:
            if region_id not in self.region_dict:
                return None
            region_info = self.region_dict[region_id]["region_info"]

        # Get region slices and mask
        slicex, slicey, mask = get_region_slices_mask(region_info)

        # Get data
        hdul, hdu_index = self.open_file_dict[file_id]
        if hdu_index is not None:
            # data = load_fits_data(hdul, hdu_index, channel, stokes)
            data = hdul[hdu_index].data[0][:, slicey, slicex]
        else:
            # data = load_xradio_data(hdul, channel, stokes,
            #                         client=self.client)
            data = hdul['SKY'].isel(
                polarization=0, time=0).values[:, slicey, slicex]

        # Get spectral profile
        spec_profile = get_spectral_profile(data, mask, stats_type)
        sp = CARTA.SpectralProfile()
        sp.coordinate = coordinate
        sp.stats_type = stats_type
        sp.raw_values_fp64 = spec_profile.astype('<f8').tobytes()

        # Create response object
        resp = CARTA.SpectralProfileData()
        resp.file_id = file_id
        resp.region_id = region_id
        resp.stokes = 0
        resp.progress = 1
        resp.profiles.append(sp)

        # Send message
        event_id = EventType.SPECTRAL_PROFILE_DATA
        message = self.encode_message(event_id, request_id, resp)
        await self.queue.put(message)

        return None
