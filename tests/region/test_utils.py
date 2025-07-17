import numpy as np
import shapely
from rasterio.features import rasterize
from rasterio.transform import from_origin

from carta_backend.region.utils import get_region_slices_mask


class TestGetRegionSlicesMask:
    """Test cases for get_region_slices_mask function."""

    def test_none_region_returns_none(self):
        """Test that None region returns None."""
        result = get_region_slices_mask(None)
        assert result is None

    def test_rectangle_region_no_image_shape(self):
        """Test rectangle region without image shape constraints."""
        # Create a simple rectangle from (1, 1) to (4, 3)
        region = shapely.box(1, 1, 4, 3)

        slicex, slicey, mask = get_region_slices_mask(region)

        # Expected slices
        assert slicex == slice(1, 4)
        assert slicey == slice(1, 3)

        # Verify mask dimensions
        assert mask.shape == (2, 3)  # (y2-y1, x2-x1)

        # Verify mask is properly rasterized
        assert mask.dtype == np.uint8
        assert np.all(mask > 0)  # Should be filled

    def test_rectangle_region_with_image_shape(self):
        """Test rectangle region with image shape constraints."""
        # Create a rectangle that extends beyond image bounds
        region = shapely.box(-1, -1, 5, 4)
        image_shape = (3, 4)  # height=3, width=4

        slicex, slicey, mask = get_region_slices_mask(region, image_shape)

        # Should be clipped to image bounds
        assert slicex == slice(0, 4)  # clipped to [0, image_width]
        assert slicey == slice(0, 3)  # clipped to [0, image_height]

        # Verify mask dimensions match the clipped region size
        expected_mask_shape = (3, 4)  # clipped to image bounds
        assert mask.shape == expected_mask_shape

    def test_rectangle_region_completely_outside_image(self):
        """Test rectangle region completely outside image bounds."""
        region = shapely.box(10, 10, 15, 15)
        image_shape = (5, 5)

        slicex, slicey, mask = get_region_slices_mask(region, image_shape)

        # Slices should be empty (start >= end)
        assert slicex.start >= slicex.stop or slicex == slice(5, 5)
        assert slicey.start >= slicey.stop or slicey == slice(5, 5)

        # Mask should be empty when region is completely outside
        assert mask.shape == (0, 0)

    def test_rectangle_region_partially_outside_image(self):
        """Test rectangle region partially outside image bounds."""
        region = shapely.box(2, 2, 6, 5)
        image_shape = (4, 4)  # height=4, width=4

        slicex, slicey, mask = get_region_slices_mask(region, image_shape)

        # Should be clipped to image bounds
        assert slicex == slice(2, 4)  # clipped at x=4
        assert slicey == slice(2, 4)  # clipped at y=4

        # Mask should be clipped to image bounds
        assert mask.shape == (2, 2)  # clipped intersection

    def test_fractional_bounds_are_floored_and_ceiled(self):
        """Test that fractional bounds are properly floored and ceiled."""
        region = shapely.box(1.3, 1.7, 3.2, 2.8)

        slicex, slicey, mask = get_region_slices_mask(region)

        # x bounds: floor(1.3)=1, ceil(3.2)=4
        # y bounds: floor(1.7)=1, ceil(2.8)=3
        assert slicex == slice(1, 4)
        assert slicey == slice(1, 3)

        # Mask dimensions based on ceiled bounds
        assert mask.shape == (2, 3)  # (3-1, 4-1)

    def test_complex_polygon_region(self):
        """Test with a more complex polygon region."""
        # Create a triangle
        region = shapely.Polygon([(1, 1), (4, 1), (2.5, 3)])

        slicex, slicey, mask = get_region_slices_mask(region)

        # Bounds should be calculated correctly
        bounds = shapely.bounds(region)
        x1, y1, x2, y2 = bounds
        expected_x1, expected_y1 = int(np.floor(x1)), int(np.floor(y1))
        expected_x2, expected_y2 = int(np.ceil(x2)), int(np.ceil(y2))

        assert slicex == slice(expected_x1, expected_x2)
        assert slicey == slice(expected_y1, expected_y2)

        # Mask should be properly rasterized
        assert mask.dtype == np.uint8
        assert mask.shape == (
            expected_y2 - expected_y1,
            expected_x2 - expected_x1,
        )

    def test_single_point_region(self):
        """Test with a single point region."""
        region = shapely.Point(2, 3)

        slicex, slicey, mask = get_region_slices_mask(region)

        # Point should create empty mask due to zero area
        assert slicex == slice(2, 2)  # Point has zero width
        assert slicey == slice(3, 3)  # Point has zero height
        assert mask.shape == (0, 0)  # Empty mask for zero-area region

    def test_zero_area_region(self):
        """Test with a zero-area region (line)."""
        region = shapely.LineString([(1, 1), (3, 1)])

        slicex, slicey, mask = get_region_slices_mask(region)

        # Line should create empty mask due to zero area
        assert slicex == slice(1, 3)
        assert slicey == slice(1, 1)  # Horizontal line has zero height
        assert mask.shape == (0, 0)  # Empty mask for zero-area region

    def test_mask_slicing_correctness(self):
        """Test that mask slicing produces correct results."""
        region = shapely.box(1, 1, 4, 3)
        image_shape = (5, 6)

        slicex, slicey, mask = get_region_slices_mask(region, image_shape)

        # Create expected mask manually for comparison
        bounds = shapely.bounds(region)
        x1, y1 = int(np.floor(bounds[0])), int(np.floor(bounds[1]))
        x2, y2 = int(np.ceil(bounds[2])), int(np.ceil(bounds[3]))

        expected_mask = np.zeros((y2 - y1, x2 - x1), dtype=np.uint8)
        rasterize(
            [region], out=expected_mask, transform=from_origin(x1, y1, 1, -1)
        )

        # The returned mask should match the expected one
        np.testing.assert_array_equal(mask, expected_mask)

    def test_large_region_with_small_image(self):
        """Test behavior with large region and small image."""
        region = shapely.box(-100, -100, 200, 200)
        image_shape = (10, 10)

        slicex, slicey, mask = get_region_slices_mask(region, image_shape)

        # Should be completely clipped to image bounds
        assert slicex == slice(0, 10)
        assert slicey == slice(0, 10)

        # Mask should be clipped to image bounds
        assert mask.shape == (10, 10)  # clipped to image shape

    def test_image_shape_boundary_conditions(self):
        """Test various boundary conditions with image shape."""
        region = shapely.box(0, 0, 3, 3)

        # Test with exact match
        result = get_region_slices_mask(region, image_shape=(3, 3))
        slicex, slicey, mask = result
        assert slicex == slice(0, 3)
        assert slicey == slice(0, 3)

        # Test with image smaller than region
        result = get_region_slices_mask(region, image_shape=(2, 2))
        slicex, slicey, mask = result
        assert slicex == slice(0, 2)
        assert slicey == slice(0, 2)

        # Test with image larger than region
        result = get_region_slices_mask(region, image_shape=(5, 5))
        slicex, slicey, mask = result
        assert slicex == slice(0, 3)
        assert slicey == slice(0, 3)
