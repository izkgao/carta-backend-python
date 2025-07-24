import asyncio
import json
import os
from itertools import product
from pathlib import Path
from typing import Optional, Tuple, Union

import aiofiles
import dask.array as da
import numba as nb
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from dask import delayed
from numcodecs import get_codec
from xarray import Dataset

from carta_backend import proto as CARTA
from carta_backend.log import logger
from carta_backend.utils import async_get_folder_size, get_folder_size

clog = logger.bind(name="CARTA")
pflog = logger.bind(name="Performance")
ptlog = logger.bind(name="Protocol")


def get_file_type(path: Union[str, Path]) -> int:
    extension = os.path.splitext(path)[1].lower()
    if extension in [".fits", ".fit", ".fts"]:
        return CARTA.FileType.FITS
    elif extension in [".hdf5", ".h5"]:
        return CARTA.FileType.HDF5
    elif extension in [".zarr"]:
        return CARTA.FileType.CASA
    elif extension in [".crtf"]:
        return CARTA.FileType.CRTF
    elif extension in [".reg"]:
        return CARTA.FileType.DS9_REG
    else:
        return CARTA.FileType.UNKNOWN


def get_region_file_type(path: Union[str, Path]) -> int:
    with open(path, "r") as f:
        try:
            first_line = f.readline().strip()
        except UnicodeDecodeError:
            return CARTA.FileType.UNKNOWN

    if "#CRTF" in first_line:
        file_type = CARTA.FileType.CRTF
    elif "# Region file format: DS9" in first_line:
        file_type = CARTA.FileType.DS9_REG
    else:
        file_type = CARTA.FileType.UNKNOWN
    return file_type


def is_zarr(path: Union[str, Path]) -> bool:
    # Check if path is a folder and .zattrs exists
    if os.path.isdir(path):
        return os.path.exists(os.path.join(path, ".zattrs"))
    return False


def is_casa(path: Union[str, Path]) -> bool:
    # Check if path is a folder and table.lock exists
    if os.path.isdir(path):
        return os.path.exists(os.path.join(path, "table.lock"))
    return False


def is_accessible(path: Union[str, Path]) -> bool:
    if isinstance(path, str):
        path = Path(path)
    try:
        path.is_dir()
        return True
    except (PermissionError, OSError, TimeoutError):
        return False


def get_file_info(
    path: str | Path, file_type: int | None = None
) -> CARTA.FileInfo:
    file_info = CARTA.FileInfo()
    file_info.name = os.path.basename(path)

    if file_type is None:
        file_type = get_file_type(path)
    file_info.type = file_type

    try:
        if os.path.isdir(path):
            file_info.size = get_folder_size(path)
        else:
            file_info.size = os.path.getsize(path)
        file_info.HDU_list.append("")
        file_info.date = int(os.path.getmtime(path))
    except (PermissionError, OSError):
        # Handle permission errors
        file_info.type = CARTA.FileType.UNKNOWN
        file_info.size = 0
        file_info.HDU_list.append("")
        file_info.date = 0

    return file_info


async def async_get_file_info(
    path: str | Path, file_type: int | None = None
) -> CARTA.FileInfo:
    file_info = CARTA.FileInfo()
    file_info.name = os.path.basename(path)

    if file_type is None:
        file_type = get_file_type(path)
    file_info.type = file_type

    try:
        if os.path.isdir(path):
            file_info.size = await async_get_folder_size(path)
        else:
            file_info.size = os.path.getsize(path)
        file_info.HDU_list.append("")
        file_info.date = int(os.path.getmtime(path))
    except (PermissionError, OSError):
        # Handle permission errors
        file_info.type = CARTA.FileType.UNKNOWN
        file_info.size = 0
        file_info.HDU_list.append("")
        file_info.date = 0

    return file_info


def get_directory_info(path: Union[str, Path]) -> CARTA.DirectoryInfo:
    dir_info = CARTA.DirectoryInfo()
    dir_info.name = os.path.basename(path)

    try:
        # Count items in subdirectory
        dir_info.item_count = len(os.listdir(path))
        # Get modification time
        dir_info.date = int(os.path.getmtime(path))
    except (PermissionError, OSError):
        # Handle permission errors
        dir_info.item_count = 0
        dir_info.date = 0

    return dir_info


def get_axes_dict(hdr):
    axes_dict = {}
    for i in range(1, hdr["NAXIS"] + 1):
        if hdr[f"CTYPE{i}"].startswith("RA"):
            axes_dict["RA"] = i - 1
        elif hdr[f"CTYPE{i}"].startswith("DEC"):
            axes_dict["DEC"] = i - 1
        elif hdr[f"CTYPE{i}"].startswith("STOKES"):
            axes_dict["STOKES"] = i - 1
        elif hdr[f"CTYPE{i}"].startswith("FREQ"):
            axes_dict["FREQ"] = i - 1
    return axes_dict


def get_header_entries(hdr):
    header_entries = []

    bool_map = {True: "T", False: "False"}

    for card in hdr.cards:
        h = CARTA.HeaderEntry()
        h.name = card[0]
        h.comment = card[2]
        if isinstance(card[1], bool):
            h.value = bool_map[card[1]]
        elif isinstance(card[1], int):
            h.value = str(card[1])
            h.entry_type = CARTA.EntryType.INT
            h.numeric_value = card[1]
        elif isinstance(card[1], float):
            h.value = str(card[1])
            h.entry_type = CARTA.EntryType.FLOAT
            h.numeric_value = card[1]
        else:
            h.value = str(card[1])

        header_entries.append(h)

    return header_entries


def get_computed_entries(hdr, hdu_index, file_name):
    computed_entries = []

    axes_dict = get_axes_dict(hdr)

    h = CARTA.HeaderEntry()
    h.name = "Name"
    h.value = file_name
    computed_entries.append(h)

    h = CARTA.HeaderEntry()
    h.name = "HDU"
    h.value = str(hdu_index)
    computed_entries.append(h)

    if "EXTNAME" in hdr:
        h = CARTA.HeaderEntry()
        h.name = "Extension name"
        h.value = hdr["EXTNAME"]
        computed_entries.append(h)

    h = CARTA.HeaderEntry()
    h.name = "Data type"
    h.value = "float" if hdr["BITPIX"] < 0 else "int"
    computed_entries.append(h)

    h = CARTA.HeaderEntry()
    h.name = "Shape"

    shape = []
    names = []
    for i in range(1, hdr["NAXIS"] + 1):
        shape.append(hdr[f"NAXIS{i}"])
        names.append(hdr[f"CTYPE{i}"].split("-")[0].strip())
    names = ", ".join(names)
    h.value = f"{str(shape)} ({names})"
    computed_entries.append(h)

    if "FREQ" in axes_dict:
        h = CARTA.HeaderEntry()
        h.name = "Number of channels"
        h.entry_type = CARTA.EntryType.INT
        n = axes_dict["FREQ"] + 1
        h.numeric_value = hdr.get(f"NAXIS{n}", 0)
        h.value = str(h.numeric_value)
        computed_entries.append(h)

    if "STOKES" in axes_dict:
        h = CARTA.HeaderEntry()
        h.name = "Number of polarizations"
        h.entry_type = CARTA.EntryType.INT
        n = axes_dict["STOKES"] + 1
        h.numeric_value = hdr.get(f"NAXIS{n}", 0)
        h.value = str(h.numeric_value)
        computed_entries.append(h)

    # Not implement yet
    h = CARTA.HeaderEntry()
    h.name = "Coordinate type"
    h.value = "Right Ascension, Declination"
    computed_entries.append(h)

    h = CARTA.HeaderEntry()
    h.name = "Projection"
    h.value = hdr["CTYPE1"].split("-")[-1].strip()
    computed_entries.append(h)

    try:
        h = CARTA.HeaderEntry()
        h.name = "Image reference pixels"
        h.value = f"[{int(hdr['CRPIX1'])}, {int(hdr['CRPIX2'])}]"
        computed_entries.append(h)
    except KeyError:
        pass

    try:
        h = CARTA.HeaderEntry()
        h.name = "Image reference coords"
        coord = SkyCoord(ra=hdr["CRVAL1"], dec=hdr["CRVAL2"], unit="deg")
        coords = coord.to_string("hmsdms", sep=":", precision=4).split()
        h.value = f"[{coords[0]}, {coords[1]}]"
        computed_entries.append(h)
    except KeyError:
        pass

    try:
        h = CARTA.HeaderEntry()
        h.name = "Image ref coords (deg)"
        h.value = f"[{hdr['CRVAL1']:.4f} deg, {hdr['CRVAL2']:.4f} deg]"
        computed_entries.append(h)
    except KeyError:
        pass

    try:
        h = CARTA.HeaderEntry()
        h.name = "Pixel increment"
        h.value = f'{hdr["CDELT1"] * 3600}", {hdr["CDELT2"] * 3600}"'
        computed_entries.append(h)
    except KeyError:
        pass

    try:
        h = CARTA.HeaderEntry()
        h.name = "Pixel unit"
        h.value = hdr["BUNIT"]
        computed_entries.append(h)
    except KeyError:
        pass

    try:
        h = CARTA.HeaderEntry()
        h.name = "Celestial frame"
        eq = hdr["EQUINOX"]
        if isinstance(eq, str):
            pass
        elif eq < 2000:
            eq = f"B{eq}"
        else:
            eq = f"J{eq}"
        if "RADESYS" in hdr:
            value = f"{hdr['RADESYS']}, {eq}"
        else:
            value = eq
        h.value = value
        computed_entries.append(h)
    except KeyError:
        pass

    h = CARTA.HeaderEntry()
    h.name = "Spectral frame"
    h.value = hdr.get("SPECSYS", "")
    computed_entries.append(h)

    # Not implement yet
    h = CARTA.HeaderEntry()
    h.name = "Velocity definition"
    h.value = "RADIO"
    computed_entries.append(h)

    if "BMAJ" in hdr:
        try:
            bmaj = hdr["BMAJ"] * 3600
            bmin = hdr["BMIN"] * 3600
            bpa = hdr["BPA"]
            value = f'{bmaj}" X {bmin}", {bpa} deg'
            h = CARTA.HeaderEntry()
            h.name = "Restoring beam"
            h.value = value
            computed_entries.append(h)
        except KeyError:
            pass

    # Not implement yet
    h = CARTA.HeaderEntry()
    h.name = "RA range"
    h.value = ""
    computed_entries.append(h)

    # Not implement yet
    h = CARTA.HeaderEntry()
    h.name = "DEC range"
    h.value = ""
    computed_entries.append(h)

    # Not implement yet
    h = CARTA.HeaderEntry()
    h.name = "Frequency range"
    h.value = ""
    computed_entries.append(h)

    # Not implement yet
    h = CARTA.HeaderEntry()
    h.name = "Velocity range"
    h.value = ""
    computed_entries.append(h)

    # Not implement yet
    # h = CARTA.HeaderEntry()
    # h.name = "Stokes coverage"
    # if "STOKES" in hdr["CTYPE4"].upper():
    #     value = "[I]"
    # else:
    #     value = ""
    # h.value = value
    # computed_entries.append(h)

    return computed_entries


def get_file_info_extended(headers, file_name):
    fex_dict = {}

    for hdu_index, hdr in enumerate(headers):
        if hdr["NAXIS"] == 0:
            continue

        xtension = hdr.get("XTENSION", "").strip()
        if xtension in ["BINTABLE", "TABLE"]:
            continue

        axes_dict = get_axes_dict(hdr)

        fex = CARTA.FileInfoExtended()
        fex.dimensions = hdr["NAXIS"]
        fex.width = hdr["NAXIS1"]
        fex.height = hdr["NAXIS2"]
        if "FREQ" in axes_dict:
            n = axes_dict["FREQ"] + 1
            depth = hdr.get(f"NAXIS{n}", 1)
        else:
            depth = 1
        fex.depth = depth
        if "STOKES" in axes_dict:
            n = axes_dict["STOKES"] + 1
            stokes = hdr.get(f"NAXIS{n}", 1)
        else:
            stokes = 1
        fex.stokes = stokes
        # fex.stokes_vals

        header_entries = get_header_entries(hdr)
        fex.header_entries.extend(header_entries)

        computed_entries = get_computed_entries(hdr, hdu_index, file_name)
        fex.computed_entries.extend(computed_entries)

        a = CARTA.AxesNumbers()
        a.spatial_x = 1
        a.spatial_y = 2
        if "FREQ" in axes_dict:
            n = axes_dict["FREQ"] + 1
            a.spectral = n
            a.depth = n
        if "STOKES" in axes_dict:
            n = axes_dict["STOKES"] + 1
            a.stokes = n
        fex.axes_numbers.CopyFrom(a)

        fex_dict[str(hdu_index)] = fex

    return fex_dict


async def get_header_from_xradio(xarr, client=None):
    if hasattr(xarr, "direction"):
        hdr = await get_header_from_xradio_new(xarr, client)
    elif hasattr(xarr["SKY"], "direction_info"):
        hdr = get_header_from_xradio_old(xarr)
    else:
        raise ValueError(
            "Could not find direction information in Xradio dataset"
        )
    return hdr


async def get_header_from_xradio_new(xarr, client=None):
    wcs_dict = xarr.direction

    # Calculate dimensions except time
    keys = list(xarr.sizes)
    keys.pop(keys.index("time"))
    keys.pop(keys.index("beam_param"))
    naxis = len(keys)

    # Get PC
    pc = np.array(wcs_dict["pc"]["_value"])
    if (pc - np.identity(2)).sum() == 0:
        pc = np.identity(naxis)
    else:
        # Not implemented
        pc = np.identity(naxis)

    # Get crpix
    crpix = []
    for axis in ["l", "m"]:
        crpix.append(np.nonzero((xarr[axis] == 0).values)[0][0] + 1)
    crpix.extend([1.0] * (naxis - 2))

    # Get crval
    crval = []
    crval.append(np.rad2deg(wcs_dict["reference"]["data"][0]))
    crval.append(np.rad2deg(wcs_dict["reference"]["data"][1]))
    if "frequency" in keys:
        crval.append(xarr["frequency"].attrs["reference_value"]["data"])
    if "polarization" in keys:
        crval.append(1.0)

    # Get cdelt
    cdelt = []
    for axis in ["l", "m"]:
        cdelt.append(np.rad2deg(xarr[axis][1] - xarr[axis][0]).values)
    if "frequency" in keys:
        values = xarr.frequency.values
        cdelt.append(values[1] - values[0])
    if "polarization" in keys:
        cdelt.append(1.0)

    # Get ctype
    ctype = [
        f"RA---{wcs_dict['projection']}",
        f"DEC--{wcs_dict['projection']}",
    ]
    if "frequency" in keys:
        ctype.append("FREQ")
    if "polarization" in keys:
        ctype.append("STOKES")

    # Get shape
    sizes = xarr.sizes
    shape = [sizes["l"], sizes["m"]]
    if "frequency" in keys:
        shape.append(sizes["frequency"])
    if "polarization" in keys:
        shape.append(sizes["polarization"])

    # Create WCS object
    wcs = WCS(naxis=naxis)

    # Set the reference pixel and coordinate
    wcs.wcs.crval = crval
    wcs.wcs.crpix = crpix
    wcs.wcs.cdelt = cdelt
    wcs.wcs.ctype = ctype
    wcs.wcs.pc = pc

    # Set additional parameters
    wcs.wcs.lonpole = np.rad2deg(wcs_dict["lonpole"]["data"])
    wcs.wcs.latpole = np.rad2deg(wcs_dict["latpole"]["data"])
    wcs.pixel_shape = shape

    # Get header
    bitpix_mapping = {
        "uint8": 8,
        "int16": 16,
        "int32": 32,
        "int64": 64,
        "float32": -32,
        "float64": -64,
    }
    hdr = wcs.to_header()
    hdr["BITPIX"] = bitpix_mapping[xarr["SKY"].dtype.name]
    hdr["NAXIS"] = hdr["WCSAXES"]
    for i, v in enumerate(wcs.pixel_shape):
        hdr[f"NAXIS{i + 1}"] = v
    bunit = xarr["SKY"].units
    if isinstance(bunit, list):
        bunit = bunit[0]
    hdr["BUNIT"] = bunit
    sky_attrs = wcs_dict["reference"]["attrs"]
    freq_attrs = xarr["frequency"].reference_value["attrs"]
    hdr["RADESYS"] = sky_attrs["frame"].upper()
    hdr["EQUINOX"] = sky_attrs.get("equinox", "J2000.0").upper()
    hdr["SPECSYS"] = freq_attrs["observer"].upper()

    if client is not None and client.asynchronous:
        beam = await client.compute(
            xarr["BEAM"].isel(time=0, frequency=0, polarization=0).data
        )
    else:
        beam = (
            xarr["BEAM"]
            .isel(time=0, frequency=0, polarization=0)
            .data.compute()
        )
    bmaj, bmin, bpa = np.rad2deg(beam)
    hdr["BMAJ"] = bmaj
    hdr["BMIN"] = bmin
    hdr["BPA"] = bpa
    hdr["PIX_AREA"] = np.abs(np.linalg.det(wcs.celestial.pixel_scale_matrix))
    return hdr


def get_header_from_xradio_old(xarr):
    wcs_dict = xarr["SKY"].direction_info

    # Calculate dimensions except time
    keys = list(xarr.sizes)
    keys.pop(keys.index("time"))
    naxis = len(keys)

    # Get PC
    pc = np.array(wcs_dict["pc"])
    if (pc - np.identity(2)).sum() == 0:
        pc = np.identity(naxis)
    else:
        # Not implemented
        pc = np.identity(naxis)

    # Get crpix
    crpix = []
    for axis in ["l", "m"]:
        crpix.append(np.nonzero((xarr[axis] == 0).values)[0][0] + 1)
    crpix.extend([1.0] * (naxis - 2))

    # Get crval
    crval = []
    crval.append(np.rad2deg(wcs_dict["reference"]["data"][0]))
    crval.append(np.rad2deg(wcs_dict["reference"]["data"][1]))
    if "frequency" in keys:
        crval.append(xarr["frequency"].attrs["crval"])
    if "polarization" in keys:
        crval.append(1.0)

    # Get cdelt
    cdelt = []
    for axis in ["l", "m"]:
        cdelt.append(np.rad2deg(xarr[axis][1] - xarr[axis][0]).values)
    if "frequency" in keys:
        values = xarr.frequency.values
        cdelt.append(values[1] - values[0])
    if "polarization" in keys:
        cdelt.append(1.0)

    # Get ctype
    ctype = [
        f"RA---{wcs_dict['projection']}",
        f"DEC--{wcs_dict['projection']}",
    ]
    if "frequency" in keys:
        ctype.append("FREQ")
    if "polarization" in keys:
        ctype.append("STOKES")

    # Get shape
    sizes = xarr.sizes
    shape = [sizes["l"], sizes["m"]]
    if "frequency" in keys:
        shape.append(sizes["frequency"])
    if "polarization" in keys:
        shape.append(sizes["polarization"])

    # Create WCS object
    wcs = WCS(naxis=naxis)

    # Set the reference pixel and coordinate
    wcs.wcs.crval = crval
    wcs.wcs.crpix = crpix
    wcs.wcs.cdelt = cdelt
    wcs.wcs.ctype = ctype
    wcs.wcs.pc = pc

    # Set additional parameters
    wcs.wcs.lonpole = np.rad2deg(wcs_dict["lonpole"]["value"])
    wcs.wcs.latpole = np.rad2deg(wcs_dict["latpole"]["value"])
    wcs.pixel_shape = shape

    # Get header
    bitpix_mapping = {
        "uint8": 8,
        "int16": 16,
        "int32": 32,
        "int64": 64,
        "float32": -32,
        "float64": -64,
    }
    hdr = wcs.to_header()
    hdr["BITPIX"] = bitpix_mapping[xarr["SKY"].dtype.name]
    hdr["NAXIS"] = hdr["WCSAXES"]
    for i, v in enumerate(wcs.pixel_shape):
        hdr[f"NAXIS{i + 1}"] = v
    hdr["BUNIT"] = xarr["SKY"].units[0]
    sky_attrs = xarr["SKY"].direction_info["reference"]["attrs"]
    freq_attrs = xarr["frequency"].reference_value["attrs"]
    hdr["RADESYS"] = sky_attrs["frame"]
    hdr["EQUINOX"] = sky_attrs["equinox"]
    hdr["SPECSYS"] = freq_attrs["observer"].upper()
    hdr["BMAJ"] = xarr["SKY"].user["bmaj"]
    hdr["BMIN"] = xarr["SKY"].user["bmin"]
    hdr["BPA"] = xarr["SKY"].user["bpa"]
    hdr["PIX_AREA"] = np.abs(np.linalg.det(wcs.celestial.pixel_scale_matrix))
    return hdr


def get_fits_dask_channels_chunks(wcs: WCS) -> tuple:
    """
    Get a tuple of chunk sizes for creating a Dask array from a FITS file.

    The chunk sizes are determined by the WCS coordinate types. The RA and DEC
    coordinates should be chunked automatically, while the FREQ and STOKES
    coordinates should be chunked with a chunk size of 1.

    Parameters
    ----------
    wcs : WCS
        The WCS object from the FITS file.

    Returns
    -------
    tuple
        A tuple of chunk sizes for creating a Dask array from the FITS file.
    """
    # Get coordinate types from WCS
    ctypes = [ctype.upper() for ctype in wcs.wcs.ctype][::-1]
    chunks = []
    for ctype in ctypes:
        if ctype.startswith("RA"):
            chunks.append("auto")
        elif ctype.startswith("DEC"):
            chunks.append("auto")
        elif ctype.startswith("FREQ"):
            chunks.append(1)
        elif ctype.startswith("STOKES"):
            chunks.append(1)
    return tuple(chunks)


def load_fits_data(
    data: Union[np.ndarray, np.memmap, da.Array],
    wcs: WCS,
    x=None,
    y=None,
    channel=None,
    stokes=None,
    dtype=None,
) -> Union[np.ndarray, da.Array]:
    """
    Load data from a FITS array with proper slicing based on WCS coordinates.

    Parameters
    ----------
    data : Union[np.ndarray, np.memmap, da.Array]
        The input data array (numpy or dask)
    wcs : WCS
        The WCS object containing coordinate information
    x : int, slice, or None
        X index or slice to select. If None, all x are selected.
    y : int, slice, or None
        Y index or slice to select. If None, all y are selected.
    channel : int, slice, or None
        Channel index or slice to select. If None, all channels are selected.
    stokes : int, slice, or None
        Stokes index or slice to select. If None, all stokes are selected.
    dtype : np.dtype | None
        The data type to convert the result to. If None, the original data
        type is used.


    Returns
    -------
    Union[np.ndarray, da.Array]
        The sliced data array
    """
    # Convert None to slice(None) for proper indexing
    x_slice = slice(None) if x is None else x
    y_slice = slice(None) if y is None else y
    channel_slice = slice(None) if channel is None else channel
    stokes_slice = slice(None) if stokes is None else stokes

    # Get coordinate types from WCS
    ctypes = [ctype.upper() for ctype in wcs.wcs.ctype]

    # Create a mapping of coordinate types to their corresponding slices
    slice_map = {}
    for i, ctype in enumerate(ctypes):
        if ctype.startswith("RA"):
            slice_map[i] = x_slice
        elif ctype.startswith("DEC"):
            slice_map[i] = y_slice
        elif ctype.startswith("FREQ"):
            slice_map[i] = channel_slice
        elif ctype.startswith("STOKES"):
            slice_map[i] = stokes_slice

    # Create a tuple of slices in the correct order for the data dimensions
    # FITS data has dimensions reversed compared to WCS (fastest varying last)
    slices = [slice(None)] * data.ndim
    wcs_dims = len(ctypes)

    # Map WCS dimensions to data array dimensions
    for wcs_axis, data_slice in slice_map.items():
        # Convert from FITS/WCS axis ordering to numpy/data axis ordering
        data_axis = wcs_dims - 1 - wcs_axis
        if data_axis < data.ndim:
            slices[data_axis] = data_slice

    # Apply the slices to the data
    result = data[tuple(slices)]

    if isinstance(result, np.memmap):
        result = np.array(result, dtype=dtype, copy=True)
    elif dtype is not None:
        result = result.astype(dtype, copy=False)
    return result


async def async_load_xradio_data(
    data, channel=None, stokes=None, time=0, client=None
):
    if channel is None:
        channel = slice(channel)
    if stokes is None:
        stokes = slice(stokes)
    data = data["SKY"].isel(frequency=channel, polarization=stokes, time=time)
    if client is not None:
        data = await client.compute(data)
    return data.data


def load_xradio_data(
    ds, x=None, y=None, channel=None, stokes=None, time=0, dtype=None
):
    if channel is None:
        channel = slice(channel)
    if stokes is None:
        stokes = slice(stokes)
    data = (
        ds["SKY"]
        .isel(frequency=channel, polarization=stokes, time=time)
        .transpose(..., "m", "l")
    )
    if x is not None:
        data = data.isel(l=x)
    if y is not None:
        data = data.isel(m=y)

    # Get dask array from xarray Dataset
    data = data.data

    if dtype is not None:
        data = data.astype(dtype, copy=False)
    return data


def load_data(
    data,
    x=None,
    y=None,
    channel=None,
    stokes=None,
    time=0,
    wcs=None,
    dtype=None,
) -> Optional[da.Array]:
    # Dask array from FITS
    if isinstance(data, (da.Array, np.ndarray, np.memmap)):
        return load_fits_data(
            data=data,
            wcs=wcs,
            x=x,
            y=y,
            channel=channel,
            stokes=stokes,
            dtype=dtype,
        )
    # Xarray Dataset from Xradio
    elif isinstance(data, Dataset):
        return load_xradio_data(
            ds=data,
            x=x,
            y=y,
            channel=channel,
            stokes=stokes,
            time=time,
            dtype=dtype,
        )
    else:
        clog.error(f"Unsupported data type: {type(data)}")
        return None


@nb.njit((nb.bool(nb.float32)), fastmath=True)
def isnan_f32(x):
    bits = np.float32(x).view(np.uint32)
    exp_mask = 0x7F800000
    frac_mask = 0x007FFFFF
    return (bits & exp_mask) == exp_mask and (bits & frac_mask) != 0


@nb.njit(fastmath=True)
def isinf_f32(x):
    bits = np.float32(x).view(np.uint32)
    exp_mask = 0x7F800000
    frac_mask = 0x007FFFFF
    return (bits & exp_mask) == exp_mask and (bits & frac_mask) == 0


@nb.njit((nb.bool(nb.float32)), fastmath=True)
def isfinite_f32(x):
    bits = np.float32(x).view(np.uint32)
    exp_mask = 0x7F800000
    return (bits & exp_mask) != exp_mask


@nb.njit(
    (nb.float32[:, :](nb.float32[:, :], nb.int64)),
    parallel=True,
    cache=True,
)
def block_reduce_numba(arr, factor):
    rows, cols = arr.shape
    block_rows, block_cols = factor, factor

    n_block_rows = (rows + factor - 1) // factor
    n_block_cols = (cols + factor - 1) // factor

    result = np.empty((n_block_rows, n_block_cols), dtype=np.float32)

    nan32 = np.float32(np.nan)

    for i in nb.prange(n_block_rows):
        i = np.uint64(i)
        row_start = np.uint64(i * block_rows)
        row_end = np.uint64(min(row_start + block_rows, rows))

        for j in range(n_block_cols):
            j = np.uint64(j)
            col_start = np.uint64(j * block_cols)
            col_end = np.uint64(min(col_start + block_cols, cols))

            sum_val = np.float32(0.0)
            count = 0

            for ii in range(row_start, row_end):
                for jj in range(col_start, col_end):
                    val = arr[ii, jj]
                    if np.isfinite(val):
                        sum_val += val
                        count += 1

            if count == 0:
                result[i, j] = nan32
            else:
                result[i, j] = np.float32(sum_val / count)

    return result


def get_chunk_read_plan(
    shape: Tuple[int], chunk_shape: Tuple[int], indices: Tuple[int | slice]
) -> Tuple:
    """
    Compute a plan for reading chunks from a zarr array based on the given
    indices.

    The function takes the shape of the array, the chunk shape, and the indices
    as input. It returns a list of dictionaries, where each dictionary describes
    a chunk to be read, and the output shape of the concatenated chunks.

    Each dictionary in the list contains the following keys:

    - ``chunk_id``: a string representing the chunk coordinates, joined by
      periods.
    - ``chunk_coords``: a tuple of integers representing the chunk coordinates.
    - ``chunk_slice``: a tuple of slices representing the slice of the chunk
      to be read.
    - ``global_slice``: a tuple of slices representing the slice of the output
      array corresponding to the chunk.

    Parameters
    ----------
    shape : tuple of int
        The shape of the array.
    chunk_shape : tuple of int
        The shape of the chunks.
    indices : tuple of int or slice
        The indices of the array to be read.

    Returns
    -------
    plans : list of dict
        The list of dictionaries describing the chunks to be read.
    output_shape : tuple of int
        The shape of the output array.
    """
    chunk_ranges = []
    slice_ranges = []
    output_shape = []

    for dim_size, chunk_size, idx in zip(shape, chunk_shape, indices):
        if isinstance(idx, int):
            chunk_idx = idx // chunk_size
            offset_in_chunk = idx % chunk_size
            chunk_ranges.append([chunk_idx])
            slice_ranges.append(
                {chunk_idx: offset_in_chunk}
            )  # scalar, not a slice
            output_shape.append(1)
        elif isinstance(idx, slice):
            start = 0 if idx.start is None else idx.start
            stop = dim_size if idx.stop is None else min(idx.stop, dim_size)
            start_chunk = start // chunk_size
            stop_chunk = (stop - 1) // chunk_size
            chunks_in_dim = list(range(start_chunk, stop_chunk + 1))
            chunk_ranges.append(chunks_in_dim)

            ranges = {}
            for chunk_idx in chunks_in_dim:
                chunk_start = chunk_idx * chunk_size
                chunk_end = min(chunk_start + chunk_size, dim_size)

                slice_start = max(start, chunk_start)
                slice_end = min(stop, chunk_end)

                # Local offset inside the chunk
                local_start = slice_start - chunk_start
                local_end = slice_end - chunk_start

                ranges[chunk_idx] = slice(local_start, local_end)
            slice_ranges.append(ranges)
            output_shape.append(stop - start)
        else:
            raise ValueError("Unsupported index type")

    plans = []
    for chunk_coords in product(*chunk_ranges):
        chunk_id = ".".join(map(str, chunk_coords))
        chunk_slice = []
        global_slice = []

        for axis, (chunk_idx, chunk_size, index_info) in enumerate(
            zip(chunk_coords, chunk_shape, slice_ranges)
        ):
            if isinstance(indices[axis], int):
                offset = index_info[chunk_idx]
                chunk_slice.append(slice(offset, offset + 1))
                global_slice.append(slice(0, 1))
            else:
                s = index_info[chunk_idx]
                chunk_slice.append(s)

                start = chunk_idx * chunk_size + s.start
                full_start = (
                    0 if indices[axis].start is None else indices[axis].start
                )
                global_slice.append(
                    slice(
                        start - full_start,
                        start - full_start + (s.stop - s.start),
                    )
                )

        plans.append(
            {
                "chunk_id": chunk_id,
                "chunk_coords": chunk_coords,
                "chunk_slice": tuple(chunk_slice),
                "global_slice": tuple(global_slice),
            }
        )
    plans.sort(key=lambda p: p["chunk_coords"])
    return plans, tuple(output_shape)


def get_zarr_info(file_path: Union[str, Path]) -> Tuple:
    """
    Retrieve metadata information from a Zarr file.

    This function reads the '.zarray' metadata file of a Zarr dataset to
    extract information about the data's shape, chunking, data type, and
    compression configuration.

    Parameters
    ----------
    file_path : Union[str, Path]
        The path to the Zarr dataset directory.

    Returns
    -------
    Tuple
        A tuple containing:
        - shape: The shape of the Zarr array.
        - chunk_shape: The shape of the chunks in the Zarr array.
        - dtype: The numpy data type of the Zarr array.
        - order: The memory layout order ('C' for row-major, 'F' for column-major).
        - compressor_config: The compression configuration of the Zarr array.
    """
    file_path = Path(file_path)
    with open(file_path / "SKY" / ".zarray", "r") as f:
        sky = json.load(f)
        compressor_config = sky["compressor"]
        shape = sky["shape"]
        chunk_shape = sky["chunks"]
        dtype = np.dtype(sky["dtype"])
        order = sky["order"]
    return shape, chunk_shape, dtype, order, compressor_config


async def async_get_zarr_info(file_path: Union[str, Path]) -> Tuple:
    """
    Retrieve metadata information from a Zarr file.

    This function reads the '.zarray' metadata file of a Zarr dataset to
    extract information about the data's shape, chunking, data type, and
    compression configuration.

    Parameters
    ----------
    file_path : Union[str, Path]
        The path to the Zarr dataset directory.

    Returns
    -------
    Tuple
        A tuple containing:
        - shape: The shape of the Zarr array.
        - chunk_shape: The shape of the chunks in the Zarr array.
        - dtype: The numpy data type of the Zarr array.
        - order: The memory layout order ('C' for row-major, 'F' for column-major).
        - compressor_config: The compression configuration of the Zarr array.
    """
    file_path = Path(file_path)
    async with aiofiles.open(file_path / "SKY" / ".zarray", "r") as f:
        sky = await f.read()
        sky = json.loads(sky)
        compressor_config = sky["compressor"]
        shape = sky["shape"]
        chunk_shape = sky["chunks"]
        dtype = np.dtype(sky["dtype"])
        order = sky.get("order", "C")
    return shape, chunk_shape, dtype, order, compressor_config


def get_fits_info(file_path: Union[str, Path], hdu_index: int = 0) -> Tuple:
    """
    Retrieve metadata information from a FITS file.

    This function reads the header and data of a FITS file to extract
    information about the data's shape, data type, offset, and header.

    Parameters
    ----------
    file_path : Union[str, Path]
        The path to the FITS file.
    hdu_index : int, optional
        The index of the HDU to read. Defaults to 0.

    Returns
    -------
    Tuple
        A tuple containing:
        - shape: The shape of the FITS data.
        - dtype: The numpy data type of the FITS data.
        - offset: The offset of the FITS data in the file.
        - header: The header of the FITS file.
    """
    with fits.open(file_path, memmap=True, mode="denywrite") as hdul:
        hdu = hdul[hdu_index]
        dtype = np.dtype(hdu.data.dtype)
        shape = hdu.data.shape
        offset = hdu._data_offset
        header = hdu.header
    return shape, dtype, offset, header


async def async_read_zarr_slice(
    file_path: Union[str, Path],
    time: slice | int | None = None,
    channel: slice | int | None = None,
    stokes: slice | int | None = None,
    x: slice | int | None = None,
    y: slice | int | None = None,
    dtype: np.dtype | None = None,
    semaphore: asyncio.Semaphore | None = None,
    max_workers: int = 4,
) -> np.ndarray:
    """
    Read a slice of data from a Zarr file.

    This function reads a slice of data from a Zarr file, taking into account
    the chunking and compression of the data.

    Parameters
    ----------
    file_path : Union[str, Path]
        The path to the Zarr dataset directory.
    time : slice | int | None, optional
        The slice of time to read. Defaults to None (all).
    channel : slice | int | None, optional
        The slice of channel to read. Defaults to None (all).
    stokes : slice | int | None, optional
        The slice of stokes to read. Defaults to None (all).
    x : slice | int | None, optional
        The slice of x to read. Defaults to None (all).
    y : slice | int | None, optional
        The slice of y to read. Defaults to None (all).
    dtype : np.dtype | None, optional
        The data type to convert the result to. If None, the original data
        type is used.
    semaphore : asyncio.Semaphore | None, optional
        The semaphore to use for limiting the number of concurrent
        read operations. If None, ``asyncio.Semaphore(max_workers)`` is used.
    max_workers : int, optional
        The maximum number of semaphores to use for reading. Defaults to 4.

    Returns
    -------
    np.ndarray
        The slice of data read from the Zarr file.
    """
    if time is None:
        time = slice(None)
    if channel is None:
        channel = slice(None)
    if stokes is None:
        stokes = slice(None)
    if x is None:
        x = slice(None)
    if y is None:
        y = slice(None)

    if (
        isinstance(channel, int)
        and isinstance(stokes, int)
        and isinstance(time, int)
    ):
        return await async_read_zarr_channel(
            file_path=file_path,
            channel=channel,
            x=x,
            y=y,
            stokes=stokes,
            time=time,
            dtype=dtype,
            semaphore=semaphore,
            max_workers=max_workers,
        )

    output_dtype = dtype

    file_path = Path(file_path)
    (
        shape,
        chunk_full_shape,
        dtype,
        order,
        comp_config,
    ) = await async_get_zarr_info(file_path)
    slices = (time, channel, stokes, x, y)
    plans, output_shape = get_chunk_read_plan(shape, chunk_full_shape, slices)

    if comp_config is not None:
        compressor = get_codec(comp_config)

    if semaphore is None:
        semaphore = asyncio.Semaphore(max_workers)

    result = np.empty(output_shape, dtype=dtype)

    async def read_and_insert(plan):
        chunk_id = plan["chunk_id"]
        chunk_slice = plan["chunk_slice"]
        global_slice = plan["global_slice"]

        chunk_filename = file_path / "SKY" / chunk_id

        def read_chunk():
            chunk_data = np.memmap(
                chunk_filename,
                mode="r",
                shape=chunk_full_shape,
                dtype=dtype,
                order=order,
            )
            data_piece = chunk_data[chunk_slice]
            return data_piece

        async with semaphore:
            result[global_slice] = await asyncio.to_thread(read_chunk)

    async def decomp_read_and_insert(plan):
        chunk_id = plan["chunk_id"]
        chunk_slice = plan["chunk_slice"]
        global_slice = plan["global_slice"]

        chunk_filename = file_path / "SKY" / chunk_id

        async with semaphore:
            async with aiofiles.open(chunk_filename, "rb") as f:
                compressed = await f.read()

        decompressed = await asyncio.to_thread(compressor.decode, compressed)

        chunk_data = np.frombuffer(decompressed, dtype=dtype).reshape(
            chunk_full_shape, order=order
        )
        data_piece = chunk_data[chunk_slice]
        result[global_slice] = data_piece

    if comp_config is not None:
        func = decomp_read_and_insert
    else:
        func = read_and_insert

    await asyncio.gather(*[func(plan) for plan in plans])

    result = np.squeeze(np.swapaxes(result, 3, 4))

    if output_dtype is not None:
        result = result.astype(output_dtype, copy=False)
    return result


async def async_read_zarr_channel(
    file_path: Union[str, Path],
    channel: int,
    x: int | slice | None = None,
    y: int | slice | None = None,
    stokes: int = 0,
    time: int = 0,
    dtype: np.dtype | None = None,
    semaphore: asyncio.Semaphore | None = None,
    max_workers: int = 4,
) -> np.ndarray:
    """
    Read a channel from a Zarr file.

    This function reads a channel from a Zarr file, taking into account
    the chunking and compression of the data.

    Parameters
    ----------
    file_path : Union[str, Path]
        The path to the Zarr dataset directory.
    channel : int
        The channel index to read.
    x : int | slice | None, optional
        The x index to read. Defaults to None.
    y : int | slice | None, optional
        The y index to read. Defaults to None.
    stokes : int
        The stokes index to read.
    time : int, optional
        The time index to read. Defaults to 0.
    dtype : np.dtype | None, optional
        The data type to convert the result to. If None, the original data
        type is used.
    semaphore : asyncio.Semaphore | None, optional
        The semaphore to use for limiting the number of concurrent
        read operations. If None, ``asyncio.Semaphore(max_workers)`` is used.
    max_workers : int, optional
        The maximum number of semaphores to use for reading. Defaults to 4.

    Returns
    -------
    np.ndarray
        The channel read from the Zarr file.
    """

    x = slice(None) if x is None else x
    y = slice(None) if y is None else y

    output_dtype = dtype

    file_path = Path(file_path)
    (
        shape,
        chunk_full_shape,
        dtype,
        order,
        comp_config,
    ) = await async_get_zarr_info(file_path)

    if comp_config is not None:
        compressor = get_codec(comp_config)

    if semaphore is None:
        semaphore = asyncio.Semaphore(max_workers)

    slices = (time, channel, stokes, x, y)
    plans, output_shape = get_chunk_read_plan(shape, chunk_full_shape, slices)

    result = np.empty(output_shape[-2:], dtype=dtype)

    async def read_and_insert(plan):
        chunk_id = plan["chunk_id"]
        chunk_slice = plan["chunk_slice"]
        global_slice = plan["global_slice"]
        channel_chunk_slice = tuple(i for i in chunk_slice[-2:])
        channel_global_slice = tuple(i for i in global_slice[-2:])

        layer_shape = chunk_full_shape[-2:]

        chunk_filename = file_path / "SKY" / chunk_id

        start = np.ravel_multi_index(
            (0, chunk_slice[1].start, 0, 0, 0), chunk_full_shape
        )
        nitems = np.prod(layer_shape)

        itemsize = dtype.itemsize

        async with semaphore:
            async with aiofiles.open(chunk_filename, "rb") as f:
                await f.seek(start * itemsize)
                chunk_data = await f.read(nitems * itemsize)

        chunk_data = np.frombuffer(chunk_data, dtype=dtype).reshape(
            layer_shape, order=order
        )

        data_piece = chunk_data[channel_chunk_slice]
        result[channel_global_slice] = data_piece

    async def decomp_read_and_insert(plan):
        chunk_id = plan["chunk_id"]
        chunk_slice = plan["chunk_slice"]
        global_slice = plan["global_slice"]
        channel_chunk_slice = tuple(i for i in chunk_slice[-2:])
        channel_global_slice = tuple(i for i in global_slice[-2:])

        layer_shape = chunk_full_shape[-2:]

        chunk_filename = file_path / "SKY" / chunk_id

        start = np.ravel_multi_index(
            (0, chunk_slice[1].start, 0, 0, 0), chunk_full_shape
        )
        nitems = np.prod(layer_shape)

        async with semaphore:
            async with aiofiles.open(chunk_filename, "rb") as f:
                compressed = await f.read()

        decompressed = await asyncio.to_thread(
            compressor.decode_partial, compressed, start, nitems
        )

        chunk_data = np.frombuffer(decompressed, dtype=dtype).reshape(
            layer_shape, order=order
        )
        data_piece = chunk_data[channel_chunk_slice]
        result[channel_global_slice] = data_piece

    func = (
        decomp_read_and_insert if comp_config is not None else read_and_insert
    )

    await asyncio.gather(*[func(plan) for plan in plans])

    result = np.swapaxes(result, 0, 1)

    if output_dtype is not None:
        result = result.astype(output_dtype, copy=False)
    return result


@delayed
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
    data = np.memmap(
        filename, mode="r", shape=shape, dtype=dtype, offset=offset
    )
    return data[sl]


def mmap_dask_array_old(filename, shape, dtype, offset=0, chunks="auto"):
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
                    create_nested_blocks(dimension + 1, new_indices)
                )
            return blocks_in_dim

    # Create the nested structure of blocks
    nested_blocks = create_nested_blocks()

    # Combine all blocks using da.block
    return da.block(nested_blocks)


def mmap_dask_array_old_v2(filename, shape, dtype, offset=0, chunks="auto"):
    def build_block(_, block_info=None):
        # Create slices from the chunk indices
        idx_tuple = block_info[0]["array-location"]
        slices = tuple(slice(start, stop) for start, stop in idx_tuple)

        # Create a memmap chunk
        memmap_chunk = np.memmap(
            filename, mode="r", shape=shape, dtype=dtype, offset=offset
        )[slices]
        return memmap_chunk

    # Create a dask array and map blocks
    data = da.empty(shape, dtype=dtype, chunks=chunks).map_blocks(
        build_block, dtype=dtype
    )
    return data


def mmap_dask_array_old_v3(filename, shape, dtype, offset=0, chunks="auto"):
    """
    Maps a file to a Dask Array using memory mapping.

    This function is derived from code in the RosettaSciIO project
    (https://github.com/hyperspy/rosettasciio), Copyright 2007–2025
    The HyperSpy developers, and distributed under the terms of the
    GNU General Public License v3 (GPLv3).

    Modifications made by Zhen-Kai Gao under the same GPLv3 license.

    Parameters
    ----------
    filename : str
        The file to be mapped.
    shape : tuple
        The shape of the array.
    dtype : dtype
        The data type of the array.
    offset : int, optional
        The offset in bytes from the start of the file. Default is 0.
    chunks : str or tuple, optional
        The chunk size of the Dask Array. Default is "auto".

    Returns
    -------
    dask_array : dask.array.Array
        The Dask Array mapped to the file.
    """

    # Normalize chunks
    normalized_chunks = da.core.normalize_chunks(
        chunks=chunks, shape=shape, dtype=dtype
    )

    # Pre-compute all slice information
    chunk_grid_shape = tuple(
        len(chunks_dim) for chunks_dim in normalized_chunks
    )
    slice_array = np.empty(chunk_grid_shape + (len(shape), 2), dtype=int)

    for block_id in np.ndindex(chunk_grid_shape):
        for dim in range(len(shape)):
            start = sum(normalized_chunks[dim][: block_id[dim]])
            stop = start + normalized_chunks[dim][block_id[dim]]
            slice_array[block_id][dim] = [start, stop]

    # Convert slice array to dask array
    slice_dask = da.from_array(
        slice_array,
        chunks=(1,) * len(chunk_grid_shape) + slice_array.shape[-2:],
    )

    # Use map_blocks with pre-computed slices
    return da.map_blocks(
        _load_chunk_from_slices,
        slice_dask,
        filename,
        shape,
        dtype,
        offset,
        dtype=dtype,
        chunks=normalized_chunks,
        drop_axis=list(range(len(chunk_grid_shape), len(slice_dask.shape))),
    )


def _load_chunk_from_slices(slice_specs, filename, shape, dtype, offset):
    """Load chunk using pre-computed slice specifications."""
    slice_specs = np.squeeze(slice_specs)[()]
    slices = tuple(slice(int(s[0]), int(s[1])) for s in slice_specs)

    memmap_data = np.memmap(
        filename, mode="r", shape=shape, dtype=dtype, offset=offset
    )
    return memmap_data[slices]


def mmap_dask_array(filename, shape, dtype, offset=0, chunks="auto"):
    """
    Maps a file to a Dask Array using memory mapping.

    This function is derived from code in the RosettaSciIO project
    (https://github.com/hyperspy/rosettasciio), Copyright 2007–2025
    The HyperSpy developers, and distributed under the terms of the
    GNU General Public License v3 (GPLv3).

    Modifications made by Zhen-Kai Gao under the same GPLv3 license.

    Parameters
    ----------
    filename : str
        The file to be mapped.
    shape : tuple
        The shape of the array.
    dtype : dtype
        The data type of the array.
    offset : int, optional
        The offset in bytes from the start of the file. Default is 0.
    chunks : str or tuple, optional
        The chunk size of the Dask Array. Default is "auto".

    Returns
    -------
    dask_array : dask.array.Array
        The Dask Array mapped to the file.
    """

    # Normalize chunks
    normalized_chunks = da.core.normalize_chunks(
        chunks=chunks, shape=shape, dtype=dtype
    )

    # Pre-compute all slice information
    chunk_grid_shape = tuple(
        len(chunks_dim) for chunks_dim in normalized_chunks
    )

    # Pre-compute cumulative sums
    cumsum_chunks = [
        np.concatenate(([0], np.cumsum(chunks_dim)))
        for chunks_dim in normalized_chunks
    ]

    # Create index arrays for each dimension
    indices = [np.arange(n) for n in chunk_grid_shape]

    # Use broadcasting to compute all slices at once
    slice_starts = np.zeros(chunk_grid_shape + (len(shape),), dtype=int)
    slice_stops = np.zeros(chunk_grid_shape + (len(shape),), dtype=int)

    for dim in range(len(shape)):
        # Create broadcasting-compatible shape
        broadcast_shape = [1] * len(chunk_grid_shape)
        broadcast_shape[dim] = chunk_grid_shape[dim]

        dim_indices = indices[dim].reshape(broadcast_shape)
        slice_starts[..., dim] = cumsum_chunks[dim][dim_indices]
        slice_stops[..., dim] = cumsum_chunks[dim][dim_indices + 1]

    # Combine into slice array
    slice_array = np.stack([slice_starts, slice_stops], axis=-1)

    # Convert slice array to dask array
    slice_dask = da.from_array(
        slice_array,
        chunks=(1,) * len(chunk_grid_shape) + slice_array.shape[-2:],
    )

    # Use map_blocks with pre-computed slices
    return da.map_blocks(
        _load_chunk_from_slices,
        slice_dask,
        filename,
        shape,
        dtype,
        offset,
        dtype=dtype,
        chunks=normalized_chunks,
        drop_axis=list(range(len(chunk_grid_shape), len(slice_dask.shape))),
    )


def compute_slices(array_shape, block_shape):
    slices = []
    for dim_size, block_size in zip(array_shape, block_shape):
        dim_slices = []
        start = 0
        while start < dim_size:
            end = min(start + block_size, dim_size)
            dim_slices.append(slice(start, end))
            start = end
        slices.append(dim_slices)
    return slices
