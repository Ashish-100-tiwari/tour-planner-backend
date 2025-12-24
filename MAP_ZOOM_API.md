# Map Zoom API - Quick Reference

## Endpoint

**POST** `/v1/map/generate`

## Authentication

Requires JWT token in Authorization header:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

## Request Body

```json
{
  "origin": "New York",
  "destination": "Boston",
  "zoom": 10,           // Optional: 1-21, null for auto-fit
  "size": "600x400"     // Optional: default "600x400"
}
```

## Response

```json
{
  "map_image_url": "https://maps.googleapis.com/maps/api/staticmap?...",
  "zoom_level": 10,
  "origin": "New York",
  "destination": "Boston"
}
```

## Zoom Levels

| Level | View |
|-------|------|
| 1-3   | World/Continent |
| 4-6   | Country |
| 7-10  | State/Region |
| 11-14 | City (default) |
| 15-17 | Neighborhood |
| 18-21 | Street/Building |

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Zoom level must be between 1 and 21"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "origin"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to generate map image URL"
}
```

## Usage Examples

### JavaScript/Fetch

```javascript
async function getMap(origin, destination, zoom = null) {
    const response = await fetch('http://localhost:8000/v1/map/generate', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            origin,
            destination,
            zoom
        })
    });
    
    if (!response.ok) {
        throw new Error('Failed to generate map');
    }
    
    return await response.json();
}

// Usage
const mapData = await getMap('New York', 'Boston', 12);
document.getElementById('map').src = mapData.map_image_url;
```

### cURL

```bash
# With zoom
curl -X POST "http://localhost:8000/v1/map/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"origin": "New York", "destination": "Boston", "zoom": 10}'

# Auto-fit (no zoom)
curl -X POST "http://localhost:8000/v1/map/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"origin": "New York", "destination": "Boston"}'
```

### Python

```python
import requests

def get_map(origin, destination, zoom=None, token=None):
    url = "http://localhost:8000/v1/map/generate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "origin": origin,
        "destination": destination,
        "zoom": zoom
    }
    
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

# Usage
map_data = get_map("New York", "Boston", zoom=12, token="your_token")
print(map_data["map_image_url"])
```

## Testing

Open [map_zoom_test.html](file:///d:/tourplanner/backend/map_zoom_test.html) in your browser to test the zoom functionality interactively.

## Notes

- **Auto-fit**: When `zoom` is `null`, the map automatically fits the entire route
- **Manual zoom**: When `zoom` is specified (1-21), the map centers on the route with that zoom level
- **Scale**: All maps use `scale=2` for retina display quality
- **Rate limits**: Subject to Google Maps Static API quotas
