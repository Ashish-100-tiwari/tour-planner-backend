import React, { useState, useEffect } from 'react';
import './MapWithZoom.css';

/**
 * MapWithZoom Component
 * 
 * A React component that displays a map with zoom in/out controls.
 * Updates the map image dynamically when users zoom.
 * 
 * Props:
 * - origin: string - Starting location
 * - destination: string - Ending location
 * - authToken: string - JWT authentication token
 * - apiBaseUrl: string - Base URL for API (default: 'http://localhost:8000')
 * - initialZoom: number | null - Initial zoom level (default: null for auto-fit)
 * - onZoomChange: (zoom: number | null) => void - Callback when zoom changes
 */

interface MapWithZoomProps {
  origin: string;
  destination: string;
  authToken: string;
  apiBaseUrl?: string;
  initialZoom?: number | null;
  onZoomChange?: (zoom: number | null) => void;
}

interface MapData {
  map_image_url: string;
  zoom_level: number | null;
  origin: string;
  destination: string;
}

const MapWithZoom: React.FC<MapWithZoomProps> = ({
  origin,
  destination,
  authToken,
  apiBaseUrl = 'http://localhost:8000',
  initialZoom = null,
  onZoomChange
}) => {
  const [mapData, setMapData] = useState<MapData | null>(null);
  const [currentZoom, setCurrentZoom] = useState<number | null>(initialZoom);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const MIN_ZOOM = 1;
  const MAX_ZOOM = 21;

  // Fetch map with current zoom level
  const fetchMap = async (zoom: number | null = currentZoom) => {
    if (!origin || !destination || !authToken) {
      setError('Missing required parameters');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/v1/map/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          origin,
          destination,
          zoom,
          size: '600x400'
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate map');
      }

      const data: MapData = await response.json();
      setMapData(data);
      setCurrentZoom(zoom);

      if (onZoomChange) {
        onZoomChange(zoom);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load map');
      console.error('Map fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load map on mount or when origin/destination changes
  useEffect(() => {
    fetchMap(initialZoom);
  }, [origin, destination]);

  // Zoom in handler
  const handleZoomIn = () => {
    const newZoom = currentZoom === null ? 10 : Math.min(currentZoom + 1, MAX_ZOOM);
    fetchMap(newZoom);
  };

  // Zoom out handler
  const handleZoomOut = () => {
    const newZoom = currentZoom === null ? 10 : Math.max(currentZoom - 1, MIN_ZOOM);
    fetchMap(newZoom);
  };

  // Reset to auto-fit
  const handleReset = () => {
    fetchMap(null);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        handleZoomIn();
      } else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        handleZoomOut();
      } else if (e.key === '0') {
        e.preventDefault();
        handleReset();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentZoom]);

  // Mouse wheel zoom
  useEffect(() => {
    const mapContainer = document.querySelector('.map-container');
    if (!mapContainer) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();

      // Scroll up = zoom in, scroll down = zoom out
      if (e.deltaY < 0) {
        handleZoomIn();
      } else if (e.deltaY > 0) {
        handleZoomOut();
      }
    };

    mapContainer.addEventListener('wheel', handleWheel as EventListener, { passive: false });
    return () => mapContainer.removeEventListener('wheel', handleWheel as EventListener);
  }, [currentZoom]);

  return (
    <div className="map-with-zoom">
      {/* Zoom Controls */}
      <div className="zoom-controls">
        <button
          className="zoom-btn zoom-out"
          onClick={handleZoomOut}
          disabled={loading || currentZoom === MIN_ZOOM}
          aria-label="Zoom out"
          title="Zoom out (or press -)"
        >
          −
        </button>

        <div className="zoom-level">
          {currentZoom === null ? 'Auto' : `${currentZoom}`}
        </div>

        <button
          className="zoom-btn zoom-in"
          onClick={handleZoomIn}
          disabled={loading || currentZoom === MAX_ZOOM}
          aria-label="Zoom in"
          title="Zoom in (or press +)"
        >
          +
        </button>

        <button
          className="reset-btn"
          onClick={handleReset}
          disabled={loading || currentZoom === null}
          aria-label="Reset zoom"
          title="Reset to auto-fit (or press 0)"
        >
          ⟲
        </button>
      </div>

      {/* Map Display */}
      <div className="map-container">
        {loading && (
          <div className="map-loading">
            <div className="spinner"></div>
            <p>Loading map...</p>
          </div>
        )}

        {error && (
          <div className="map-error">
            <p>⚠️ {error}</p>
            <button onClick={() => fetchMap(currentZoom)}>Retry</button>
          </div>
        )}

        {mapData && !loading && (
          <img
            src={mapData.map_image_url}
            alt={`Map from ${origin} to ${destination}`}
            className="map-image"
          />
        )}

        {!mapData && !loading && !error && (
          <div className="map-placeholder">
            <p>No map data available</p>
          </div>
        )}
      </div>

      {/* Map Info */}
      {mapData && (
        <div className="map-info">
          <span className="route-info">
            <strong>From:</strong> {mapData.origin} → <strong>To:</strong> {mapData.destination}
          </span>
        </div>
      )}
    </div>
  );
};

export default MapWithZoom;
