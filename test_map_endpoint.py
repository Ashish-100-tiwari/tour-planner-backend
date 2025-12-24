"""
Tests for the /v1/map/generate endpoint
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from auth import create_access_token
import os
from dotenv import load_dotenv

load_dotenv()

client = TestClient(app)

# Create a test token
test_user = {"email": "test@example.com", "name": "Test User"}
test_token = create_access_token(test_user)
headers = {"Authorization": f"Bearer {test_token}"}


pytestmark = pytest.mark.skipif(
    not os.getenv("GOOGLE_MAPS_API_KEY"),
    reason="GOOGLE_MAPS_API_KEY not set"
)


def test_generate_map_success():
    """Test successful map generation"""
    response = client.post(
        "/v1/map/generate",
        json={
            "origin": "New York",
            "destination": "Boston",
            "zoom": 10
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "map_image_url" in data
    assert "zoom_level" in data
    assert "origin" in data
    assert "destination" in data
    
    assert data["zoom_level"] == 10
    assert data["origin"] == "New York"
    assert data["destination"] == "Boston"
    assert "maps.googleapis.com" in data["map_image_url"]


def test_generate_map_default_zoom():
    """Test map generation with default zoom (None)"""
    response = client.post(
        "/v1/map/generate",
        json={
            "origin": "San Francisco",
            "destination": "Los Angeles"
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["zoom_level"] is None
    assert "map_image_url" in data


def test_generate_map_invalid_zoom():
    """Test map generation with invalid zoom level"""
    # Zoom too low
    response = client.post(
        "/v1/map/generate",
        json={
            "origin": "New York",
            "destination": "Boston",
            "zoom": 0
        },
        headers=headers
    )
    
    assert response.status_code == 400
    assert "Zoom level must be between 1 and 21" in response.json()["detail"]
    
    # Zoom too high
    response = client.post(
        "/v1/map/generate",
        json={
            "origin": "New York",
            "destination": "Boston",
            "zoom": 25
        },
        headers=headers
    )
    
    assert response.status_code == 400


def test_generate_map_custom_size():
    """Test map generation with custom size"""
    response = client.post(
        "/v1/map/generate",
        json={
            "origin": "Paris",
            "destination": "London",
            "zoom": 8,
            "size": "800x600"
        },
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "size=800x600" in data["map_image_url"]


def test_generate_map_no_auth():
    """Test that endpoint requires authentication"""
    response = client.post(
        "/v1/map/generate",
        json={
            "origin": "New York",
            "destination": "Boston"
        }
    )
    
    assert response.status_code == 401


def test_generate_map_missing_fields():
    """Test map generation with missing required fields"""
    response = client.post(
        "/v1/map/generate",
        json={
            "origin": "New York"
            # Missing destination
        },
        headers=headers
    )
    
    assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
