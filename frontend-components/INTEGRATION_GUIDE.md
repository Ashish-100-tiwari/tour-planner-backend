# Frontend Integration Guide

## Files Created

1. **MapWithZoom.tsx** - Main React component with zoom functionality
2. **MapWithZoom.css** - Styling for the component
3. **ChatWithMapExample.tsx** - Example integration into chat interface

## Installation

Copy the files from `d:\tourplanner\backend\frontend-components\` to your frontend project:

```bash
# Copy to your React/Next.js components directory
cp d:\tourplanner\backend\frontend-components\MapWithZoom.tsx <your-frontend>/components/
cp d:\tourplanner\backend\frontend-components\MapWithZoom.css <your-frontend>/components/
```

## Basic Usage

```tsx
import MapWithZoom from './components/MapWithZoom';

function MyComponent() {
  return (
    <MapWithZoom
      origin="New York"
      destination="Boston"
      authToken={yourAuthToken}
      apiBaseUrl="http://localhost:8000"
    />
  );
}
```

## Integration with Chat Response

When your chat API returns journey details, render the map:

```tsx
// In your chat message handler
const handleChatResponse = (response) => {
  if (response.journey_details) {
    // Render message with map
    return (
      <div>
        <p>{response.choices[0].message.content}</p>
        <MapWithZoom
          origin={response.journey_details.origin}
          destination={response.journey_details.destination}
          authToken={authToken}
        />
      </div>
    );
  }
};
```

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| origin | string | Yes | - | Starting location |
| destination | string | Yes | - | Ending location |
| authToken | string | Yes | - | JWT authentication token |
| apiBaseUrl | string | No | 'http://localhost:8000' | API base URL |
| initialZoom | number \| null | No | null | Initial zoom level (null = auto-fit) |
| onZoomChange | (zoom) => void | No | - | Callback when zoom changes |

## Features

✅ **Zoom Controls**: + and - buttons to zoom in/out
✅ **Keyboard Shortcuts**: 
  - `+` or `=` to zoom in
  - `-` to zoom out
  - `0` to reset to auto-fit
✅ **Auto-fit**: Automatically fits entire route when zoom is null
✅ **Loading States**: Shows spinner while loading
✅ **Error Handling**: Displays errors with retry button
✅ **Responsive**: Works on mobile and desktop
✅ **Dark Mode**: Supports dark mode
✅ **Accessibility**: ARIA labels and keyboard navigation

## Styling Customization

Override CSS variables in your global styles:

```css
.map-with-zoom {
  --zoom-btn-color: #667eea;
  --zoom-btn-hover: #764ba2;
  --border-radius: 12px;
}
```

## TypeScript

The component is fully typed. If you're using JavaScript, simply rename the file to `.jsx` and remove the type annotations.

## Next Steps

1. Copy the component files to your frontend project
2. Import and use `MapWithZoom` in your chat interface
3. Pass the origin and destination from your chat API response
4. Customize the styling to match your app's design

## Example: Full Chat Integration

```tsx
import React, { useState } from 'react';
import MapWithZoom from './components/MapWithZoom';

function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const authToken = useAuth(); // Your auth hook

  const sendMessage = async (text) => {
    const response = await fetch('http://localhost:8000/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: [{ role: 'user', content: text }]
      })
    });

    const data = await response.json();
    
    setMessages([...messages, {
      role: 'assistant',
      content: data.choices[0].message.content,
      journey_details: data.journey_details,
      map_image_url: data.map_image_url
    }]);
  };

  return (
    <div className="chat">
      {messages.map((msg, i) => (
        <div key={i} className="message">
          <p>{msg.content}</p>
          {msg.journey_details && (
            <MapWithZoom
              origin={msg.journey_details.origin}
              destination={msg.journey_details.destination}
              authToken={authToken}
            />
          )}
        </div>
      ))}
    </div>
  );
}
```

## Troubleshooting

**Map not loading?**
- Check that your auth token is valid
- Verify the API base URL is correct
- Check browser console for errors

**Zoom not working?**
- Ensure the backend `/v1/map/generate` endpoint is running
- Check that zoom levels are between 1-21

**Styling issues?**
- Make sure `MapWithZoom.css` is imported
- Check for CSS conflicts with your global styles
