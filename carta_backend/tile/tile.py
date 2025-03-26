import math


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
