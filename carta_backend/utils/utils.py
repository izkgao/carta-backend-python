import asyncio
import os
import platform
import socket
import subprocess
from pathlib import Path
from typing import Optional, Union

import dask.array as da
import numba as nb
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
from dask.distributed import Client
from numba import njit
from xarray import Dataset

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
            result = subprocess.run(["lsb_release", "-a"],
                                    capture_output=True, text=True)
            return (
                result.stdout
                if result.returncode == 0
                else "Platform information not available"
            )

    elif system == "Windows":  # Windows
        result = subprocess.run(
            ["wmic", "os", "get", "Caption,Version,BuildNumber"],
            capture_output=True, text=True)
        return (
            result.stdout
            if result.returncode == 0
            else "Platform information not available")

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


def get_folder_size(path: str) -> int:
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def get_file_type(path: Union[str, Path]) -> CARTA.FileType:
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


def get_nan_encodings_block(arr):
    # Based on https://gist.github.com/nvictus/66627b580c13068589957d6ab0919e66
    arr = np.isnan(arr).ravel()
    n = arr.size
    if arr[0]:
        rle = np.diff(np.r_[np.r_[0, 0, np.nonzero(np.diff(arr))[0] + 1], n])
    else:
        rle = np.diff(np.r_[np.r_[0, np.nonzero(np.diff(arr))[0] + 1], n])
    return rle.astype(np.uint32)


def encode_tile_coord(x, y, layer):
    return (layer << 24) | (y << 12) | x


def decode_tile_coord(encoded_coord):
    # Extract x: Get the lowest 12 bits
    x = encoded_coord & 0xFFF

    # Extract y: Shift right by 12 bits and get the lowest 12 bits
    y = (encoded_coord >> 12) & 0xFFF

    # Extract layer: Shift right by 24 bits and get the lowest 8 bits
    layer = (encoded_coord >> 24) & 0xFF

    return x, y, layer


def get_header_from_xradio(xarr):
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


# @njit(nb.int64[:](nb.float32[:], nb.int64, nb.float64, nb.float64))
# def numba_histogram(data, bins, bin_min, bin_max):
#     hist = np.zeros(bins, dtype=np.int64)
#     bin_width = (bin_max - bin_min) / bins

#     for x in data:
#         if not np.isnan(x) and bin_min <= x <= bin_max:
#             bin_idx = int((x - bin_min) / bin_width)
#             bin_idx = min(hist.size - 1, bin_idx)
#             hist[bin_idx] += 1

#     return hist


@njit(nb.int64[:](nb.float32[:], nb.float32[:]))
def numba_histogram_single(data, bin_edges):
    # Precompute constants
    n_bins = bin_edges.size - 1
    bin_min, bin_max = bin_edges[0], bin_edges[-1]
    bin_width = bin_edges[1] - bin_edges[0]
    max_idx = n_bins - 1
    hist = np.zeros(n_bins, dtype=np.int64)

    for x in data:
        if not np.isnan(x) and bin_min <= x <= bin_max:
            bin_idx = int((x - bin_min) / bin_width)
            bin_idx = min(max_idx, bin_idx)
            hist[bin_idx] += 1

    return hist


@njit((nb.int64[:](nb.float32[:], nb.float32[:])),
      parallel=True, fastmath=True)
def numba_histogram(data, bin_edges):
    # Precompute constants
    n_bins = bin_edges.size - 1
    bin_min, bin_max = bin_edges[0], bin_edges[-1]
    bin_width = bin_edges[1] - bin_edges[0]
    max_idx = n_bins - 1

    # Use thread-local histograms to avoid race conditions
    n_threads = nb.get_num_threads()
    local_hists = np.zeros((n_threads, n_bins), dtype=np.int64)

    # Process data in chunks for better cache locality
    chunk_size = 1024**2
    n_chunks = (data.size + chunk_size - 1) // chunk_size

    for chunk in nb.prange(n_chunks):
        thread_id = nb.get_thread_id()
        start = chunk * chunk_size
        end = min(start + chunk_size, data.size)

        # Process each chunk
        for i in range(start, end):
            x = data[i]
            # Combine conditions to reduce branching
            if not np.isnan(x) and x >= bin_min and x <= bin_max:
                bin_idx = min(max_idx, int((x - bin_min) / bin_width))
                local_hists[thread_id, bin_idx] += 1

    # Sum up the thread-local histograms
    hist = np.zeros(n_bins, dtype=np.int64)
    for t in range(n_threads):
        for b in range(n_bins):
            hist[b] += local_hists[t, b]

    return hist


async def dask_histogram(data, bins):
    bin_min = da.nanmin(data)
    bin_max = da.nanmax(data)
    hist, bin_edges = da.histogram(data, bins=bins, range=[bin_min, bin_max])
    return hist, bin_edges, bin_min


async def get_histogram_dask(data, client: Client):
    # Calculate number of bins
    nbins = int(max(np.sqrt(data.shape[0] * data.shape[1]), 2.0))

    # Calculate bin range
    res = client.compute([da.nanmin(data), da.nanmax(data)])
    bin_min, bin_max = await client.gather(res)

    # Calculate histogram
    res = client.compute(
        da.histogram(data, bins=nbins, range=[bin_min, bin_max]))
    hist, bin_edges = await client.gather(res)
    bin_width = bin_edges[1] - bin_edges[0]
    bin_centers = bin_edges[:-1] + bin_width / 2
    mean = np.sum(hist * bin_centers) / np.sum(hist)
    std_dev = np.sqrt(np.sum(hist * (bin_centers - mean) ** 2) / np.sum(hist))

    histogram = CARTA.Histogram()
    histogram.num_bins = nbins
    histogram.bin_width = bin_width
    histogram.first_bin_center = bin_centers[0]
    histogram.bins.extend(hist)
    histogram.mean = mean
    histogram.std_dev = std_dev
    return histogram


async def get_histogram_numpy(data: np.ndarray) -> CARTA.Histogram:
    # Calculate number of bins
    nbins = int(max(np.sqrt(data.shape[0] * data.shape[1]), 2.0))

    # Calculate bin range
    bin_min, bin_max = np.nanmin(data), np.nanmax(data)
    bin_width = (bin_max - bin_min) / nbins
    bin_edges = np.linspace(bin_min, bin_max, nbins + 1, dtype='float32')

    # Calculate histogram
    data = data.astype('float32').ravel()
    if data.size <= 1024**2:
        hist = numba_histogram_single(data, bin_edges)
    else:
        hist = await asyncio.to_thread(numba_histogram, data, bin_edges)
    bin_centers = bin_edges[:-1] + bin_width / 2
    mean = np.sum(hist * bin_centers) / np.sum(hist)
    std_dev = np.sqrt(np.sum(hist * (bin_centers - mean) ** 2) / np.sum(hist))

    histogram = CARTA.Histogram()
    histogram.num_bins = nbins
    histogram.bin_width = bin_width
    histogram.first_bin_center = bin_min + bin_width / 2
    histogram.bins.extend(hist)
    histogram.mean = mean
    histogram.std_dev = std_dev
    return histogram


async def get_histogram(
        data: da.Array | np.ndarray, client: Client
        ) -> CARTA.Histogram:
    if isinstance(data, da.Array):
        clog.debug("Using dask histogram")
        return await get_histogram_dask(data, client)
    elif isinstance(data, np.ndarray):
        clog.debug("Using numba histogram")
        return await get_histogram_numpy(data)


# @dask.delayed
# def compress_data_zfp_dask(data, compression_quality):
#     comp_data = pyzfp.compress(
#         data,
#         precision=compression_quality)
#     nan_encodings = get_nan_encodings_block(data)
#     return np.asarray(comp_data), nan_encodings


def pad_for_coarsen(darray, coarsen_factors):
    """
    Pad a 2D dask array with NaN values to make its dimensions divisible
    by coarsen_factors.

    Parameters:
    -----------
    darray : dask.array
        Input 2D dask array to be padded
    coarsen_factors : tuple of int
        Factors by which to coarsen each dimension (e.g., (4, 4))

    Returns:
    --------
    dask.array
        Padded dask array with dimensions divisible by coarsen_factors
    """
    # Get current shape
    orig_shape = darray.shape

    # Calculate required dimensions that are divisible by the coarsen factors
    padded_shape = []
    pad_widths = []

    for dim, factor in zip(orig_shape, coarsen_factors):
        # Calculate required padding
        remainder = dim % factor
        padding_needed = 0 if remainder == 0 else factor - remainder
        padded_shape.append(dim + padding_needed)

        # Padding configuration for this dimension
        # We pad only at the end of each dimension
        pad_widths.append((0, padding_needed))

    # Pad the array with NaN values
    padded_array = da.pad(
        darray,
        pad_width=pad_widths,
        mode="constant",
        constant_values=da.nan
    )

    return padded_array


@njit
def fill_nan_with_block_average(data, offset=0):
    h, w = data.shape
    data = data.ravel()

    for i in range(0, w, 4):
        for j in range(0, h, 4):
            block_start = offset + j * w + i
            valid_count = 0
            sum_val = 0.0

            # Limit block size at image edges
            block_width = min(4, w - i)
            block_height = min(4, h - j)

            # Calculate sum and count of non-NaN values in block
            for x in range(block_width):
                for y in range(block_height):
                    idx = block_start + (y * w) + x
                    v = data[idx]
                    if not np.isnan(v):
                        valid_count += 1
                        sum_val += v

            # Only process blocks with both NaN and non-NaN values
            if valid_count > 0 and valid_count < (block_width * block_height):
                average = sum_val / valid_count

                # Replace NaNs with the block average
                for x in range(block_width):
                    for y in range(block_height):
                        idx = block_start + (y * w) + x
                        if np.isnan(data[idx]):
                            data[idx] = average
    return data
