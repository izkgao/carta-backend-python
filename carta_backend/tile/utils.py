import math
from time import perf_counter_ns

import numba as nb
import numpy as np
from numba import njit
from zfpy import compress_numpy

from carta_backend import proto as CARTA
from carta_backend.config.config import MAX_COMPRESSION_QUALITY
from carta_backend.log import logger

pflog = logger.bind(name="Performance")


def layer_to_mip(layer, image_shape, tile_shape=(256, 256)):
    """
    Convert a layer value to a mip value. mip is the downsampling factor.

    Parameters
    ----------
    layer : int
        The zoom level in the tiling hierarchy
    image_shape : tuple
        (height, width) of the original image in pixels
    tile_shape : tuple, optional
        (height, width) of a single tile in pixels, default (256, 256)

    Returns
    -------
    int
        The corresponding mip (downsampling factor)
    """
    total_tiles_x = math.ceil(image_shape[1] / tile_shape[1])
    total_tiles_y = math.ceil(image_shape[0] / tile_shape[0])
    max_mip = max(total_tiles_x, total_tiles_y)
    total_layers = math.ceil(math.log2(max_mip))
    return 2 ** (total_layers - layer)


def mip_to_layer(mip, image_shape, tile_shape=(256, 256)):
    """
    Convert a mip value to a layer value. mip is the downsampling factor.

    Parameters
    ----------
    mip : int
        The downsampling factor
    image_shape : tuple
        (height, width) of the original image in pixels
    tile_shape : tuple, optional
        (height, width) of a single tile in pixels, default (256, 256)

    Returns
    -------
    int
        The corresponding layer (zoom level)
    """
    total_tiles_x = math.ceil(image_shape[1] / tile_shape[1])
    total_tiles_y = math.ceil(image_shape[0] / tile_shape[0])
    max_mip = max(total_tiles_x, total_tiles_y)
    return math.ceil(math.log2(max_mip / mip))


def get_tile_slice(x, y, layer, image_shape, tile_shape=(256, 256)):
    """
    Generate slices to directly extract a tile from a coarsened array
    without rechunking. Accounts for trim_excess=True in coarsen operation.

    Parameters
    ----------
    x : int
        Tile x-coordinate (column)
    y : int
        Tile y-coordinate (row)
    layer : int
        Pyramid layer (determines mip level)
    image_shape : tuple
        Original image shape (height, width)
    tile_shape : tuple, optional
        Shape of the desired tiles (height, width), default (256, 256)

    Returns
    -------
    tuple
        (y_slice, x_slice) - Slices to extract the tile from the
                             coarsened array
    """
    # Calculate mip level (downsampling factor)
    mip = layer_to_mip(layer, image_shape, tile_shape)

    # With trim_excess=True, the coarsened dimensions are:
    # - Original dimension // mip (integer division)
    # This trims any excess that doesn't fit evenly
    coarsened_height = image_shape[0] // mip
    coarsened_width = image_shape[1] // mip

    # Calculate starting positions in the coarsened array
    start_y = y * tile_shape[0]
    start_x = x * tile_shape[1]

    # Calculate ending positions (with bounds checking)
    end_y = min(start_y + tile_shape[0], coarsened_height)
    end_x = min(start_x + tile_shape[1], coarsened_width)

    # Create slices
    y_slice = slice(start_y, end_y)
    x_slice = slice(start_x, end_x)

    return y_slice, x_slice


def get_tile_original_slice(x, y, layer, image_shape, tile_shape=(256, 256)):
    # Calculate mip level (downsampling factor)
    mip = layer_to_mip(layer, image_shape, tile_shape)

    # Calculate starting positions in the original array
    start_y = y * tile_shape[0] * mip
    start_x = x * tile_shape[1] * mip

    # Calculate ending positions (with bounds checking)
    end_y = min(start_y + tile_shape[0] * mip, image_shape[0])
    end_x = min(start_x + tile_shape[1] * mip, image_shape[1])

    # Create slices
    y_slice = slice(start_y, end_y)
    x_slice = slice(start_x, end_x)

    return y_slice, x_slice


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


@njit(nb.float32[:, :](nb.float32[:, :]))
def fill_nan_with_block_average(data):
    """
    Fill NaN values in a 2D array with the average of non-NaN
    values in 4x4 blocks.

    Parameters
    ----------
    data : numpy.ndarray
        2D float32 array that may contain NaN values

    Returns
    -------
    numpy.ndarray
        2D float32 array with NaN values replaced by block
        averages where possible
    """
    h, w = data.shape
    # Create a copy to avoid modifying the original array
    result = data.copy()
    flat_result = result.ravel()

    for i in range(0, w, 4):
        for j in range(0, h, 4):
            block_start = j * w + i
            valid_count = 0
            sum_val = 0.0

            # Limit block size at image edges
            block_width = min(4, w - i)
            block_height = min(4, h - j)

            # Calculate sum and count of non-NaN values in block
            for x in range(block_width):
                for y in range(block_height):
                    idx = block_start + (y * w) + x
                    v = flat_result[idx]
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
                        if np.isnan(flat_result[idx]):
                            flat_result[idx] = average
    return result


def _compress_tile(data, precision):
    prev_ratio = -1
    while True:
        comp_data = compress_numpy(
            data, precision=precision, write_header=False
        )
        comp_ratio = data.nbytes / len(comp_data)
        if comp_ratio == prev_ratio:
            break
        elif comp_ratio <= 20 or precision == MAX_COMPRESSION_QUALITY:
            break
        else:
            precision = (precision + MAX_COMPRESSION_QUALITY + 1) // 2
    return comp_data, precision


def compress_tile(data, compression_type, compression_quality):
    if compression_type == CARTA.CompressionType.ZFP:
        comp_data, precision = _compress_tile(data, compression_quality)
    elif compression_type == CARTA.CompressionType.SZ:
        # Not implemented yet
        comp_data = data.tobytes()
        precision = compression_quality
    else:
        comp_data = data.tobytes()
        precision = compression_quality
    return comp_data, precision


def compute_tile(
    tile_data: np.ndarray,
    compression_type: CARTA.CompressionType,
    compression_quality: int,
):
    # NaN encodings
    t0 = perf_counter_ns()
    tile_height, tile_width = tile_data.shape
    nan_encodings = get_nan_encodings_block(tile_data).tobytes()
    dt = (perf_counter_ns() - t0) / 1e6
    msg = f"Get nan encodings in {dt:.3f} ms"
    pflog.debug(msg)

    # Fill NaNs
    t0 = perf_counter_ns()
    tile_data = fill_nan_with_block_average(tile_data)
    dt = (perf_counter_ns() - t0) / 1e6
    msg = f"Fill NaN with block average in {dt:.3f} ms"
    pflog.debug(msg)

    # Compress data
    t0 = perf_counter_ns()

    comp_data, precision = compress_tile(
        tile_data, compression_type, compression_quality
    )

    dt = (perf_counter_ns() - t0) / 1e6
    msg = f"Compress {tile_width}x{tile_height} tile data in {dt:.3f} ms "
    msg += f"at {tile_data.size / 1e6 / dt * 1000:.3f} MPix/s"
    pflog.debug(msg)

    return comp_data, precision, nan_encodings, tile_data.shape
