import os
from pathlib import Path
from typing import Optional, Union

import dask.array as da
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
from xarray import Dataset

from carta_backend import proto as CARTA
from carta_backend.log import logger
from carta_backend.utils import get_folder_size

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


def load_fits_data(
    data: Union[np.ndarray, da.Array],
    wcs: WCS,
    x=None,
    y=None,
    channel=None,
    stokes=None,
) -> Union[np.ndarray, da.Array]:
    """
    Load data from a FITS array with proper slicing based on WCS coordinates.

    Parameters
    ----------
    data : Union[np.ndarray, da.Array]
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
    return data[tuple(slices)]


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


def load_xradio_data(ds, x=None, y=None, channel=None, stokes=None, time=0):
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
    return data.data


def load_data(
    data, x=None, y=None, channel=None, stokes=None, time=0, wcs=None
) -> Optional[da.Array]:
    # Dask array from FITS
    if isinstance(data, da.Array) or isinstance(data, np.ndarray):
        return load_fits_data(data, wcs, x, y, channel, stokes)
    # Xarray Dataset from Xradio
    elif isinstance(data, Dataset):
        return load_xradio_data(data, x, y, channel, stokes, time)
    else:
        clog.error(f"Unsupported data type: {type(data)}")
        return None
