import re
from dataclasses import dataclass

import dask.array as da
import numba as nb
import numpy as np
import shapely
from numba import njit, prange
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.affinity import rotate

from carta_backend import proto as CARTA


@dataclass
class RegionData:
    file_id: int
    region_info: CARTA.RegionInfo
    preview_region: bool | None
    profiles: np.ndarray | None


def get_rectangle(region_info):
    points = region_info.control_points
    center = [points[0].x, points[0].y]
    size = [points[1].x, points[1].y]
    xmin = center[0] - size[0] / 2
    xmax = xmin + size[0]
    ymin = center[1] - size[1] / 2
    ymax = ymin + size[1]
    rect = shapely.box(xmin, ymin, xmax, ymax)
    if region_info.rotation != 0:
        rect = rotate(rect, region_info.rotation)
    return rect


def is_box(polygon, tol=1e-8):
    if not polygon.is_valid or polygon.is_empty:
        return False

    # Check if it has 5 points (including repeated first point)
    coords = list(polygon.exterior.coords)
    if len(coords) != 5:
        return False

    # Create a box using bounds
    box = shapely.box(*polygon.bounds)

    return polygon.equals_exact(box, tolerance=tol)


def get_point(region_info):
    points = region_info.control_points
    x, y = points[0].x, points[0].y
    x, y = round(x), round(y)
    return shapely.Point(x, y)


def get_region(region_info):
    if region_info.region_type == CARTA.RegionType.RECTANGLE:
        return get_rectangle(region_info)
    elif region_info.region_type == CARTA.RegionType.POINT:
        return get_point(region_info)
    else:
        return None


def get_region_slices_mask(region_info):
    # Currently rectangle only
    reg = get_region(region_info)
    if reg is None:
        return None

    # Get slices
    bounds = shapely.bounds(reg)
    x1, y1 = np.floor(bounds)[:2].astype(int)
    x2, y2 = np.ceil(bounds)[2:].astype(int)
    slicex = slice(x1, x2)
    slicey = slice(y1, y2)

    # Make an array mask
    out_shape = (y2 - y1, x2 - x1)
    mask = np.zeros(out_shape, dtype=np.uint8)
    rasterize([reg], out=mask, transform=from_origin(x1, y1, 1, -1))
    return slicex, slicey, mask


def rasterize_chunk(block_data, block_info=None, region=None):
    if block_info is None:
        return block_data

    block_mask = np.zeros(block_data.shape[-2:], dtype=np.uint8)

    xmin = block_info[0]["array-location"][-1][0]
    xmax = xmin + block_data.shape[-1]
    ymin = block_info[0]["array-location"][-2][0]
    ymax = ymin + block_data.shape[-2]
    block_box = shapely.box(xmin, ymin, xmax, ymax)

    # If block does not intersect with region
    if not block_box.intersects(region):
        return block_mask

    transform = from_origin(xmin, ymin, 1, -1)
    rasterize([region], out=block_mask, transform=transform, all_touched=True)
    return block_mask


def get_fluxdensity(x, axis=None, hdr=None):
    beam_area = np.pi * hdr["BMAJ"] * hdr["BMIN"] / (4 * np.log(2))
    beam_area /= hdr["PIX_AREA"]
    return da.nansum(x, axis=axis) / beam_area


def get_rms(x, axis=None):
    return da.sqrt(da.nanmean(x**2, axis=axis))


def get_sumsq(x, axis=None):
    return da.nansum(x**2, axis=axis)


def get_extrema(x, axis=None):
    max_indices = da.nanargmax(da.abs(x).reshape(x.shape[0], -1), axis=1)
    add_indices = da.arange(x.shape[0]) * (x.shape[1] * x.shape[2])
    return da.take(x.ravel(), max_indices + add_indices)


@njit(fastmath=True)
def isnan(x):
    if int(x) == -9223372036854775808:
        return True
    else:
        return False


@njit((nb.float64[:](nb.float32[:, :], nb.float64)), fastmath=True)
def _numba_stats(data, beam_area):
    # psum, pfld, pmean, prms, pstd, psumsq, pmin, pmax, pext
    res = np.array(
        [0, np.nan, np.nan, np.nan, np.nan, 0, np.inf, -np.inf, np.nan]
    )
    pnum = 0

    for i in data.ravel():
        if not isnan(i):
            # sum
            res[0] += i
            # num
            pnum += 1
            # sumsq
            res[5] += i**2
            # min
            if i < res[6]:
                res[6] = i
            # max
            if i > res[7]:
                res[7] = i
    if pnum == 0:
        # sum
        res[0] = np.nan
        # sumsq
        res[5] = np.nan
    else:
        # mean = sum / num
        res[2] = res[0] / pnum
        # rms = sqrt(sumsq / num)
        res[3] = np.sqrt(res[5] / pnum)
        # std = sqrt((sumsq - num * mean**2) / num)
        res[4] = np.sqrt((res[5] - pnum * res[2] ** 2) / pnum)

    if np.abs(res[7]) >= np.abs(res[6]):
        res[8] = res[7]
    else:
        res[8] = res[6]

    # flux density = sum / beam_area
    res[1] = res[0] / beam_area
    return res


@njit(
    (nb.float64[:, :](nb.float32[:, :, :], nb.float64)),
    parallel=True,
    fastmath=True,
)
def numba_stats(data, beam_area):
    # psum, pfld, pmean, prms, pstd, psumsq, pmin, pmax, pext
    res = np.zeros((9, data.shape[0]))
    for i in prange(data.shape[0]):
        res[:, i] = _numba_stats(data[i], beam_area)
    return res


STATS_FUNCS = {
    2: da.nansum,
    3: get_fluxdensity,
    4: da.nanmean,
    5: get_rms,
    6: da.nanstd,
    7: get_sumsq,
    8: da.nanmin,
    9: da.nanmax,
    10: get_extrema,
}


def get_spectral_profile(data, mask, stats_type, hdr=None):
    mdata = data[:, mask]
    return STATS_FUNCS[stats_type](mdata, axis=1, hdr=hdr).astype("<f8")


# def get_spectral_profile_dask(data, region, stats_type, hdr=None):
#     if isinstance(region, shapely.Point):
#         return data[:, region.y, region.x].astype("<f8")
#     if is_box(region):
#         minx, miny, maxx, maxy = [int(i) for i in region.bounds]
#         mdata = data[:, miny : maxy + 1, minx : maxx + 1].astype("<f8")
#     else:
#         mask = data[0].map_blocks(
#             rasterize_chunk, region=region, meta=np.array((), dtype=np.uint8)
#         )
#         mask_3d = da.broadcast_to(mask[None, :, :], data.shape)
#         mdata = da.where(mask_3d, data, da.nan)
#     kwargs = {"axis": (1, 2)}
#     if stats_type == 3:
#         kwargs["hdr"] = hdr
#     spec_profile = STATS_FUNCS[stats_type](mdata, **kwargs)
#     return spec_profile.astype("<f8")


def _get_spectral_profile_dask(data, region, hdr):
    if is_box(region):
        minx, miny, maxx, maxy = [int(i) for i in region.bounds]
        mdata = data[:, miny : maxy + 1, minx : maxx + 1].astype("float64")
    else:
        mask = data[0].map_blocks(
            rasterize_chunk, region=region, meta=np.array((), dtype=np.uint8)
        )
        mask_3d = da.broadcast_to(mask[None, :, :], data.shape)
        mdata = da.where(mask_3d, data, da.nan)

    size = mdata.shape[1] * mdata.shape[2]
    psum = da.nansum(mdata, axis=(1, 2))
    pnum = size - da.sum(da.isnan(mdata), axis=(1, 2))
    pmean = psum / pnum
    psumsq = da.nansum(mdata**2, axis=(1, 2))
    pstd = da.sqrt(
        da.nansum((mdata - pmean[:, None, None]) ** 2, axis=(1, 2)) / pnum
    )
    pmin = da.nanmin(mdata, axis=(1, 2))
    pmax = da.nanmax(mdata, axis=(1, 2))
    res = da.stack([psum, pnum, pmean, psumsq, pstd, pmin, pmax], axis=0)
    return res


async def get_spectral_profile_dask_old(data, region, hdr, client):
    res = await client.compute(_get_spectral_profile_dask(data, region, hdr))
    psum, pnum, pmean, psumsq, pstd, pmin, pmax = res
    beam_area = hdr["BMAJ"] * hdr["BMIN"] / hdr["PIX_AREA"] * 1.13309
    pfld = psum / beam_area
    prms = np.sqrt(psumsq / pnum)
    pext = np.where(np.abs(pmax) >= np.abs(pmin), pmax, pmin)
    profiles = np.stack(
        [psum, pfld, pmean, prms, pstd, psumsq, pmin, pmax, pext], axis=0
    ).astype("float64")
    return profiles


def get_spectral_profile_dask(data, region, hdr):
    if is_box(region):
        minx, miny, maxx, maxy = [int(i) for i in region.bounds]
        mdata = data[:, miny : maxy + 1, minx : maxx + 1]
    else:
        mask = data[0].map_blocks(
            rasterize_chunk, region=region, meta=np.array((), dtype=np.uint8)
        )
        mask_3d = da.broadcast_to(mask[None, :, :], data.shape)
        mdata = da.where(mask_3d, data, da.nan)

    beam_area = (
        np.pi * hdr["BMAJ"] * hdr["BMIN"] / (4 * np.log(2)) / hdr["PIX_AREA"]
    )

    profiles = da.map_blocks(
        numba_stats,
        mdata.astype("float32"),
        beam_area,
        dtype=np.float64,
        chunks=(9, data.chunks[0]),
        drop_axis=[1, 2],
        new_axis=0,
        meta=np.array([], dtype=np.float64),
    )
    return profiles


def parse_region(file_path, file_type):
    if file_type == CARTA.FileType.DS9_REG:
        # Not implemented
        return None
    elif file_type == CARTA.FileType.CRTF:
        return parse_crtf(file_path)
    else:
        return None


def parse_crtf_centerbox_string(s):
    result = {}

    # Match the centerbox and extract numbers
    shape_match = re.search(
        r"centerbox\s*\[\[\s*([\d.]+)pix,\s*([\d.]+)pix\s*\],\s*"
        r"\[\s*([\d.]+)pix,\s*([\d.]+)pix\s*\]\]",
        s,
    )

    if shape_match:
        result["center"] = [
            float(shape_match.group(1)),
            float(shape_match.group(2)),
        ]
        result["width"] = [
            float(shape_match.group(3)),
            float(shape_match.group(4)),
        ]

    # Match all key=value pairs
    kv_pairs = re.findall(r"(\w+)=([\w\-.]+)", s)
    for key, value in kv_pairs:
        # Try to convert value to float or int if possible
        try:
            num_val = float(value)
            if num_val.is_integer():
                num_val = int(num_val)
            result[key] = num_val
        except ValueError:
            result[key] = value

    center = CARTA.Point(x=result["center"][0], y=result["center"][1])
    width = CARTA.Point(x=result["width"][0], y=result["width"][1])

    region_info = CARTA.RegionInfo()
    region_info.region_type = CARTA.RegionType.RECTANGLE
    region_info.control_points.append(center)
    region_info.control_points.append(width)

    region_style = CARTA.RegionStyle()
    if "color" in result:
        color = result["color"].lstrip("#").upper()
        region_style.color = f"#{color}"
    if "linewidth" in result:
        region_style.line_width = result["linewidth"]

    region_style.dash_list.append(0)

    return region_info, region_style


def parse_crtf_point_string(s):
    result = {}

    # Match the symbol and extract numbers
    shape_match = re.search(
        r"symbol\s*\[\[\s*([\d.]+)pix,\s*([\d.]+)pix\s*\]", s
    )

    if shape_match:
        result["point"] = [
            float(shape_match.group(1)),
            float(shape_match.group(2)),
        ]

    # Match all key=value pairs
    kv_pairs = re.findall(r"(\w+)=([\w\-.]+)", s)
    for key, value in kv_pairs:
        # Try to convert value to float or int if possible
        try:
            num_val = float(value)
            if num_val.is_integer():
                num_val = int(num_val)
            result[key] = num_val
        except ValueError:
            result[key] = value

    point = CARTA.Point(x=result["point"][0], y=result["point"][1])

    region_info = CARTA.RegionInfo()
    region_info.region_type = CARTA.RegionType.POINT
    region_info.control_points.append(point)

    region_style = CARTA.RegionStyle()
    if "color" in result:
        color = result["color"].lstrip("#").upper()
        region_style.color = f"#{color}"
    if "linewidth" in result:
        region_style.line_width = result["linewidth"]

    region_style.dash_list.append(0)

    return region_info, region_style


def parse_crtf(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()

    region_list = []

    for line in lines:
        if line.startswith("centerbox"):
            region_list.append(parse_crtf_centerbox_string(line))
        elif line.startswith("symbol"):
            region_list.append(parse_crtf_point_string(line))

    return region_list
