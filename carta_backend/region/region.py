import math

import numpy as np
import shapely
from rasterio.features import rasterize
from shapely.affinity import rotate

from carta_backend import proto as CARTA


def get_rectangle_coords(region_info):
    points = region_info.control_points
    center = [points[0].x, points[0].y]
    size = [points[1].x, points[1].y]
    xmin = center[0] - size[0] / 2
    xmax = xmin + size[0]
    ymin = center[1] - size[1] / 2
    ymax = ymin + size[1]
    rect = shapely.box(xmin, ymin, xmax, ymax)
    rect = rotate(rect, region_info.rotation)
    coords = rect.exterior.coords
    return coords


def get_region_slices_mask(region_info):
    # Currently rectangle only
    if region_info.region_type == CARTA.RegionType.RECTANGLE:
        coords = get_rectangle_coords(region_info)
    else:
        return None

    # Get slices
    x1 = math.floor(min([i[0] for i in coords]))
    y1 = math.floor(min([i[1] for i in coords]))
    x2 = math.ceil(max([i[0] for i in coords])) + 1
    y2 = math.ceil(max([i[1] for i in coords])) + 1
    slicex = slice(x1, x2)
    slicey = slice(y1, y2)

    # Make a new polygon for making an array mask
    coords = np.array(coords)
    coords[:, 0] -= x1
    coords[:, 1] -= y1
    poly = shapely.Polygon(coords)

    # Make an array mask
    mask = rasterize([poly], out_shape=(y2 - y1, x2 - x1)).astype(bool)
    return slicex, slicey, mask


def _get_rms(x, axis=None):
    return np.sqrt(np.nanmean(x**2, axis=axis))


def _get_sumsq(x, axis=None):
    return np.nansum(x**2, axis=axis)

# def _get_extrema(x, axis=None):
#     return np.nanmin(x, axis=axis), np.nanmax(x, axis=axis)


STATS_FUNCS = {
    2: np.nansum,
    3: None,
    4: np.nanmean,
    5: _get_rms,
    6: np.nanstd,
    7: _get_sumsq,
    8: np.nanmin,
    9: np.nanmax,
}


def get_spectral_profile(data, mask, stats_type):
    mdata = data[:, mask]
    return STATS_FUNCS[stats_type](mdata, axis=1)
