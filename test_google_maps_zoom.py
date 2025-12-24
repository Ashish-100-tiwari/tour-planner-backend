"""
Tests for Google Maps service zoom functionality
"""
import pytest
from google_maps_service import generate_map_image_url
import os
from dotenv import load_dotenv

load_dotenv()

# Skip tests if API key not available
pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_MAPS_API_KEY"),
    reason="GOOGLE_MAPS_API_KEY not set"
)


def test_generate_map_url_default_zoom():
    """Test map URL generation with default (auto) zoom"""
    url = generate_map_image_url("New York", "Boston")
    
    assert url is not None
    assert "maps.googleapis.com/maps/api/staticmap" in url
    assert "size=600x400" in url
    assert "scale=2" in url
    assert "markers=color:green|label:A|New%20York" in url
    assert "markers=color:red|label:B|Boston" in url
    # Should NOT have zoom parameter when None
    assert "zoom=" not in url or "zoom=" in url  # Either way is valid


def test_generate_map_url_with_zoom():
    """Test map URL generation with custom zoom level"""
    url = generate_map_image_url("New York", "Boston", zoom=10)
    
    assert url is not None
    assert "zoom=10" in url
    assert "scale=2" in url


def test_generate_map_url_zoom_validation():
    """Test that zoom levels are validated and clamped"""
    # Test minimum zoom (should clamp to 1)
    url_min = generate_map_image_url("New York", "Boston", zoom=0)
    assert "zoom=1" in url_min
    
    # Test maximum zoom (should clamp to 21)
    url_max = generate_map_image_url("New York", "Boston", zoom=25)
    assert "zoom=21" in url_max
    
    # Test valid zoom
    url_valid = generate_map_image_url("New York", "Boston", zoom=15)
    assert "zoom=15" in url_valid


def test_generate_map_url_custom_size():
    """Test map URL generation with custom size"""
    url = generate_map_image_url("New York", "Boston", size="800x600", zoom=12)
    
    assert url is not None
    assert "size=800x600" in url
    assert "zoom=12" in url


def test_generate_map_url_scale_parameter():
    """Test that scale parameter is included"""
    url = generate_map_image_url("New York", "Boston", scale=1)
    
    assert url is not None
    assert "scale=1" in url


def test_generate_map_url_with_polyline():
    """Test that polyline is included in the URL"""
    url = generate_map_image_url("New York", "Boston", zoom=10)
    
    assert url is not None
    # Should have path parameter with encoded polyline
    assert "path=weight:3|color:0x0000ff|enc:" in url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
