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
    if extension in ['.fits', '.fit', '.fts']:
        return CARTA.FileType.FITS
    elif extension in ['.hdf5', '.h5']:
        return CARTA.FileType.HDF5
    elif extension in ['.zarr']:
        return CARTA.FileType.CASA
    else:
        return CARTA.FileType.UNKNOWN


def get_file_info(path: Union[str, Path]) -> CARTA.FileInfo:
    file_info = CARTA.FileInfo()
    file_info.name = os.path.basename(path)

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

    # Not implemented yet
    # h = CARTA.HeaderEntry()
    # h.name = "Shape"

    # values = []
    # for i in hdr.keys():
    #     if i.startswith("NAXIS") and len(i) > 5:
    #         values.append(hdr[i])

    # names = []
    # for i in hdr.keys():
    #     if i.startswith("CTYPE") and len(i) > 5:
    #         names.append(hdr[i].split("-")[0])

    # h.value = f"{str(values)} {str(names)}"
    # computed_entries.append(h)

    h = CARTA.HeaderEntry()
    h.name = "Number of channels"
    h.entry_type = CARTA.EntryType.INT
    h.numeric_value = hdr.get("NAXIS3", 1)
    h.value = str(h.numeric_value)
    computed_entries.append(h)

    h = CARTA.HeaderEntry()
    h.name = "Number of polarizations"
    h.entry_type = CARTA.EntryType.INT
    h.numeric_value = hdr.get("NAXIS4", 0)
    h.value = str(h.numeric_value)
    computed_entries.append(h)

    # Not implement yet
    h = CARTA.HeaderEntry()
    h.name = "Coordinate type"
    h.value = "Right Ascension, Declination"
    computed_entries.append(h)

    # Not implement yet
    # h = CARTA.HeaderEntry()
    # h.name = "Projection"
    # h.value = "SIN"
    # computed_entries.append(h)

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
        h.value = f'{hdr["CDELT1"]*3600}\", {hdr["CDELT2"]*3600}\"'
        computed_entries.append(h)
    except KeyError:
        pass

    try:
        h = CARTA.HeaderEntry()
        h.name = "Pixel unit"
        h.value = hdr['BUNIT']
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

    h = CARTA.HeaderEntry()
    h.name = "Restoring beam"

    try:
        bmaj = hdr["BMAJ"] * 3600
        bmin = hdr["BMIN"] * 3600
        bpa = hdr["BPA"]
        value = f'{bmaj}\" X {bmin}\", {bpa} deg'
    except KeyError:
        value = ""

    h.value = value
    computed_entries.append(h)

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
        if hdr['NAXIS'] == 0:
            continue
        fex = CARTA.FileInfoExtended()
        fex.dimensions = hdr['NAXIS']
        fex.width = hdr['NAXIS1']
        fex.height = hdr['NAXIS2']
        fex.depth = hdr.get('NAXIS3', 1)
        fex.stokes = hdr.get('NAXIS4', 1)
        # fex.stokes_vals

        header_entries = get_header_entries(hdr)
        fex.header_entries.extend(header_entries)

        computed_entries = get_computed_entries(hdr, hdu_index, file_name)
        fex.computed_entries.extend(computed_entries)

        # Not implemented yet
        a = CARTA.AxesNumbers()
        a.spatial_x = 1
        a.spatial_y = 2
        if "NAXIS3" in hdr:
            a.spectral = 3
            a.depth = 3
        if "NAXIS4" in hdr:
            a.stokes = 4
        fex.axes_numbers.CopyFrom(a)

        fex_dict[str(hdu_index)] = fex

    return fex_dict


def get_header_from_xradio(xarr):
    if hasattr(xarr, "direction"):
        wcs_dict = xarr.direction
    elif hasattr(xarr["SKY"], "direction_info"):
        wcs_dict = xarr["SKY"].direction_info
    else:
        raise ValueError(
            "Could not find direction information in Xradio dataset")

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
    ctype = [f'RA---{wcs_dict["projection"]}',
             f'DEC--{wcs_dict["projection"]}']
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
    bitpix_mapping = {"uint8": 8, "int16": 16, "int32": 32, "int64": 64,
                      "float32": -32, "float64": -64}
    hdr = wcs.to_header()
    hdr["BITPIX"] = bitpix_mapping[xarr["SKY"].dtype.name]
    hdr["NAXIS"] = hdr["WCSAXES"]
    for i, v in enumerate(wcs.pixel_shape):
        hdr[f"NAXIS{i+1}"] = v
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


def load_fits_data(data, channel=None, stokes=None):
    if channel is None:
        channel = slice(channel)
    if stokes is None:
        stokes = slice(stokes)
    ndim = data.ndim
    if ndim == 3:
        data = data[channel]
    elif ndim == 4:
        data = data[stokes][channel]
    # data = data.astype('<f4')
    return data


async def async_load_xradio_data(
        data, channel=None, stokes=None, time=0, client=None):
    if channel is None:
        channel = slice(channel)
    if stokes is None:
        stokes = slice(stokes)
    data = data['SKY'].isel(
        frequency=channel, polarization=stokes, time=time)
    if client is not None:
        data = await client.compute(data)
    return data.data


def load_xradio_data(ds, channel=None, stokes=None, time=0):
    if channel is None:
        channel = slice(channel)
    if stokes is None:
        stokes = slice(stokes)
    data = ds['SKY'].isel(
        frequency=channel, polarization=stokes, time=time)
    return data.data


def load_data(data, channel=None, stokes=None, time=0) -> Optional[da.Array]:
    # Dask array from FITS
    if isinstance(data, da.Array) or isinstance(data, np.ndarray):
        return load_fits_data(data, channel, stokes)
    # Xarary Dataset from Xradio
    elif isinstance(data, Dataset):
        return load_xradio_data(data, channel, stokes, time)
    else:
        clog.error(f"Unsupported data type: {type(data)}")
        return None
