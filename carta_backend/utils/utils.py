import os
import platform
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

import aiofiles.os
from aioitertools import iter

from carta_backend import proto as CARTA
from carta_backend.log import logger

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """
    Check if a specific port on the given host is available for binding.

    This function attempts to create a socket and bind it to the specified
    host and port. If the binding is successful, the port is considered
    available; otherwise, it's in use.

    Parameters
    ----------
    port : int
        The port number to check for availability.
    host : str, optional
        The host address to bind to. Default is "127.0.0.1".

    Returns
    -------
    bool
        True if the port is available, False if it's already in use or
        cannot be bound.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def get_release_info():
    system = platform.system()

    if system == "Darwin":  # macOS
        result = subprocess.run(["sw_vers"], capture_output=True, text=True)
        return result.stdout

    elif system == "Linux":  # Linux distributions
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r") as f:
                return f.read()
        else:
            # Fallback: Try lsb_release
            result = subprocess.run(
                ["lsb_release", "-a"], capture_output=True, text=True
            )
            return (
                result.stdout
                if result.returncode == 0
                else "Platform information not available"
            )

    elif system == "Windows":  # Windows
        result = subprocess.run(
            ["wmic", "os", "get", "Caption,Version,BuildNumber"],
            capture_output=True,
            text=True,
        )
        return (
            result.stdout
            if result.returncode == 0
            else "Platform information not available"
        )

    return "Platform information not available"


def get_system_info():
    system_info = {
        "platform": platform.system(),
        "architecture": platform.machine(),
        "deployment": "Unknown",
    }

    try:
        system_info["release_info"] = get_release_info()
    except Exception:
        system_info["release_info"] = "Command not available"

    return system_info


# def get_folder_size(path: str) -> int:
#     total_size = 0
#     for dirpath, _, filenames in os.walk(path):
#         for f in filenames:
#             fp = os.path.join(dirpath, f)
#             total_size += os.path.getsize(fp)
#     return total_size


def get_folder_size(path: str) -> int:
    total_size = 0
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
        for dirpath, _, filenames in os.walk(path):
            sizes = executor.map(
                lambda x: os.path.getsize(os.path.join(dirpath, x)), filenames
            )
            total_size += sum(sizes)
    return total_size


async def async_get_folder_size(path: str) -> int:
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        sizes = []
        async for filename in iter(filenames):
            sizes.append(
                await aiofiles.os.path.getsize(os.path.join(dirpath, filename))
            )
        total_size += sum(sizes)
    return total_size


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

EVENT_TYPE_MAP = {v: k for k, v in CARTA.EventType.items()}


def get_event_info(message: bytes) -> Tuple[int, str]:
    event_type = int.from_bytes(message[0:2], byteorder="little")
    event_name = EVENT_TYPE_MAP.get(event_type, None)
    return event_type, event_name
