import dask.array as da
import numpy as np
import shapely
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.affinity import rotate

from carta_backend import proto as CARTA


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


def get_region(region_info):
    if region_info.region_type == CARTA.RegionType.RECTANGLE:
        return get_rectangle(region_info)
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

    xmin = block_info[0]['array-location'][-1][0]
    ymin = block_info[0]['array-location'][-2][0]

    transform = from_origin(xmin, ymin, 1, -1)
    block_mask = np.zeros(block_data.shape[-2:], dtype=np.uint8)
    rasterize([region], out=block_mask, transform=transform, all_touched=True)
    return block_mask


def get_fluxdensity(x, axis=None, hdr=None):
    beam_area = np.pi * hdr['BMAJ'] * hdr['BMIN'] / (4 * np.log(2))
    beam_area /= hdr['PIXEL_AREA']
    return da.nansum(x, axis=axis) / beam_area  # Why divide?


def get_rms(x, axis=None):
    return da.sqrt(da.nanmean(x**2, axis=axis))


def get_sumsq(x, axis=None):
    return da.nansum(x**2, axis=axis)


def get_extrema(x, axis=None):
    max_indices = da.nanargmax(da.abs(x).reshape(x.shape[0], -1), axis=1)
    add_indices = da.arange(x.shape[0]) * (x.shape[1] * x.shape[2])
    return da.take(x.ravel(), max_indices + add_indices)


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
    return STATS_FUNCS[stats_type](mdata, axis=1, hdr=hdr).astype('<f8')


def get_spectral_profile_dask(data, region, stats_type, hdr=None):
    mask = data[0].map_blocks(
        rasterize_chunk, region=region, meta=np.array((), dtype=np.uint8))
    mask_3d = da.broadcast_to(mask[None, :, :], data.shape)
    mdata = da.where(mask_3d, data, da.nan)
    kwargs = {"axis": (1, 2)}
    if stats_type == 3:
        kwargs["hdr"] = hdr
    spec_profile = STATS_FUNCS[stats_type](mdata, **kwargs)
    return spec_profile.astype('<f8')
