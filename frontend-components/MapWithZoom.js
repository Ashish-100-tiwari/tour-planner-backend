/**
 * MapWithZoom - Vanilla JavaScript Version
 * 
 * A standalone JavaScript class for adding zoom functionality to maps.
 * No framework dependencies required.
 * 
 * Usage:
 * const mapZoom = new MapWithZoom({
 *   containerId: 'map-container',
 *   origin: 'New York',
 *   destination: 'Boston',
 *   authToken: 'your-jwt-token',
 *   apiBaseUrl: 'http://localhost:8000'
 * });
 */

class MapWithZoom {
    constructor(options) {
        this.container = document.getElementById(options.containerId);
        this.origin = options.origin;
        this.destination = options.destination;
        this.authToken = options.authToken;
        this.apiBaseUrl = options.apiBaseUrl || 'http://localhost:8000';
        this.currentZoom = options.initialZoom || null;
        this.onZoomChange = options.onZoomChange || null;

        this.MIN_ZOOM = 1;
        this.MAX_ZOOM = 21;

        this.init();
    }

    init() {
        if (!this.container) {
            console.error('Container element not found');
            return;
        }

        this.render();
        this.attachEventListeners();
        this.loadMap();
    }

    render() {
        this.container.innerHTML = `
      <div class="map-with-zoom-js">
        <div class="zoom-controls-js">
          <button class="zoom-btn-js zoom-out-js" data-action="zoom-out" title="Zoom out (-)">−</button>
          <div class="zoom-level-js">Auto</div>
          <button class="zoom-btn-js zoom-in-js" data-action="zoom-in" title="Zoom in (+)">+</button>
          <button class="reset-btn-js" data-action="reset" title="Reset (0)">⟲</button>
        </div>
        <div class="map-container-js">
          <div class="map-loading-js">
            <div class="spinner-js"></div>
            <p>Loading map...</p>
          </div>
        </div>
        <div class="map-info-js" style="display: none;">
          <span class="route-info-js"></span>
        </div>
      </div>
    `;

        this.elements = {
            zoomIn: this.container.querySelector('[data-action="zoom-in"]'),
            zoomOut: this.container.querySelector('[data-action="zoom-out"]'),
            reset: this.container.querySelector('[data-action="reset"]'),
            zoomLevel: this.container.querySelector('.zoom-level-js'),
            mapContainer: this.container.querySelector('.map-container-js'),
            mapInfo: this.container.querySelector('.map-info-js'),
            routeInfo: this.container.querySelector('.route-info-js')
        };
    }

    attachEventListeners() {
        this.elements.zoomIn.addEventListener('click', () => this.zoomIn());
        this.elements.zoomOut.addEventListener('click', () => this.zoomOut());
        this.elements.reset.addEventListener('click', () => this.reset());

        // Keyboard shortcuts
        this.keyboardHandler = (e) => {
            if (e.key === '+' || e.key === '=') {
                e.preventDefault();
                this.zoomIn();
            } else if (e.key === '-' || e.key === '_') {
                e.preventDefault();
                this.zoomOut();
            } else if (e.key === '0') {
                e.preventDefault();
                this.reset();
            }
        };
        document.addEventListener('keydown', this.keyboardHandler);

        // Mouse wheel zoom
        this.wheelHandler = (e) => {
            e.preventDefault();

            // Scroll up = zoom in, scroll down = zoom out
            if (e.deltaY < 0) {
                this.zoomIn();
            } else if (e.deltaY > 0) {
                this.zoomOut();
            }
        };
        this.elements.mapContainer.addEventListener('wheel', this.wheelHandler, { passive: false });
    }

    async loadMap(zoom = this.currentZoom) {
        if (!this.origin || !this.destination || !this.authToken) {
            this.showError('Missing required parameters');
            return;
        }

        this.showLoading();

        try {
            const response = await fetch(`${this.apiBaseUrl}/v1/map/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.authToken}`
                },
                body: JSON.stringify({
                    origin: this.origin,
                    destination: this.destination,
                    zoom: zoom,
                    size: '600x400'
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to generate map');
            }

            const data = await response.json();
            this.currentZoom = zoom;
            this.showMap(data);
            this.updateZoomDisplay();

            if (this.onZoomChange) {
                this.onZoomChange(zoom);
            }
        } catch (error) {
            this.showError(error.message);
        }
    }

    showLoading() {
        this.elements.mapContainer.innerHTML = `
      <div class="map-loading-js">
        <div class="spinner-js"></div>
        <p>Loading map...</p>
      </div>
    `;
    }

    showMap(data) {
        this.elements.mapContainer.innerHTML = `
      <img src="${data.map_image_url}" 
           alt="Map from ${data.origin} to ${data.destination}"
           class="map-image-js">
    `;

        this.elements.routeInfo.innerHTML = `
      <strong>From:</strong> ${data.origin} → <strong>To:</strong> ${data.destination}
    `;
        this.elements.mapInfo.style.display = 'block';
    }

    showError(message) {
        this.elements.mapContainer.innerHTML = `
      <div class="map-error-js">
        <p>⚠️ ${message}</p>
        <button onclick="this.closest('.map-with-zoom-js').dispatchEvent(new CustomEvent('retry'))">
          Retry
        </button>
      </div>
    `;

        this.container.addEventListener('retry', () => this.loadMap(), { once: true });
    }

    updateZoomDisplay() {
        const zoomText = this.currentZoom === null ? 'Auto' : `${this.currentZoom}`;
        this.elements.zoomLevel.textContent = zoomText;

        // Update button states
        this.elements.zoomIn.disabled = this.currentZoom === this.MAX_ZOOM;
        this.elements.zoomOut.disabled = this.currentZoom === this.MIN_ZOOM;
        this.elements.reset.disabled = this.currentZoom === null;
    }

    zoomIn() {
        const newZoom = this.currentZoom === null ? 10 : Math.min(this.currentZoom + 1, this.MAX_ZOOM);
        this.loadMap(newZoom);
    }

    zoomOut() {
        const newZoom = this.currentZoom === null ? 10 : Math.max(this.currentZoom - 1, this.MIN_ZOOM);
        this.loadMap(newZoom);
    }

    reset() {
        this.loadMap(null);
    }

    // Update origin/destination and reload
    updateRoute(origin, destination) {
        this.origin = origin;
        this.destination = destination;
        this.currentZoom = null;
        this.loadMap();
    }

    // Cleanup
    destroy() {
        document.removeEventListener('keydown', this.keyboardHandler);
        this.container.innerHTML = '';
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapWithZoom;
}
