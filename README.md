# Tour Planner Backend API

A FastAPI-based backend service for a tour planning application with LLM-powered chat, Google Maps integration, and user authentication.

## Features

- 🤖 **LLM Chat Completions** - Powered by Llama 3.2 3B Instruct (GGUF format)
- 🗺️ **Google Maps Integration** - Route planning with zoom controls
- 🔐 **JWT Authentication** - Secure user signup/signin
- 💾 **MongoDB** - User data and conversation history storage
- 📝 **Conversation Memory** - TTL-based message history (30 minutes)

## Prerequisites

- Python 3.10+
- MongoDB Atlas account (or local MongoDB)
- Google Maps API key
- GGUF model file (Llama-3.2-3B-Instruct-Q8_0.gguf or similar)

## Installation

1. **Clone the repository and navigate to backend:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment:**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create `.env` file:**
   ```env
   MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/?appName=Cluster0
   DATABASE_NAME=tourplanner
   SECRET_KEY=your-secret-key-change-this-in-production
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   GOOGLE_MAPS_API_KEY=your-google-maps-api-key
   N_CTX=2048
   N_THREADS=4
   N_GPU_LAYERS=0
   MODEL_PATH=models/Llama-3.2-3B-Instruct-Q8_0.gguf
   PORT=8000
   ```

6. **Download model file:**
   - Place your GGUF model file in the `models/` directory
   - Update `MODEL_PATH` in `.env` if using a different model

## Running the Server

```bash
python main.py
```

The server will start on `http://0.0.0.0:8000` (or the port specified in `.env`).

## API Endpoints

### Authentication

#### Sign Up
```bash
POST /auth/signup
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "confirm_password": "password123"
}
```

#### Sign In
```bash
POST /auth/signin
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```

#### Get Current User
```bash
GET /auth/me
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Chat Completions

```bash
POST /v1/chat/completions
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "messages": [
    {
      "role": "user",
      "content": "Plan a trip from New York to Boston"
    }
  ],
  "temperature": 0.5,
  "max_tokens": 100
}
```

**Response includes:**
- `choices[0].message.content` - LLM response
- `journey_details` - Detected origin/destination (if found)
- `map_image_url` - Google Maps static image URL (if journey detected)

### Map Generation

```bash
POST /v1/map/generate
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "origin": "New York",
  "destination": "Boston",
  "zoom": 10,        // Optional: 1-21, null for auto-fit
  "size": "600x400"  // Optional: default "600x400"
}
```

**Response:**
```json
{
  "map_image_url": "https://maps.googleapis.com/maps/api/staticmap?...",
  "zoom_level": 10,
  "origin": "New York",
  "destination": "Boston"
}
```

### Conversation Management

#### Clear Conversation History
```bash
DELETE /v1/conversations/clear
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Health Check

```bash
GET /health
GET /
```

## Frontend Integration

### React/TypeScript Component

The `frontend-components/` directory contains ready-to-use React components:

- **MapWithZoom.tsx** - Map component with zoom controls
- **MapWithZoom.css** - Styling
- **ChatWithMapExample.tsx** - Example chat integration

**Basic Usage:**
```tsx
import MapWithZoom from './components/MapWithZoom';

<MapWithZoom
  origin="New York"
  destination="Boston"
  authToken={yourAuthToken}
  apiBaseUrl="http://localhost:8000"
  initialZoom={null}  // null = auto-fit
/>
```

**Features:**
- ✅ Zoom controls (+/- buttons)
- ✅ Keyboard shortcuts (+/- keys)
- ✅ Mouse wheel scroll zoom
- ✅ Reset to auto-fit
- ✅ Loading states and error handling

## Example cURL Commands

### Complete Flow

```bash
# 1. Sign up
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "password123",
    "confirm_password": "password123"
  }'

# 2. Sign in
curl -X POST http://localhost:8000/auth/signin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password123"
  }'

# 3. Use chat (replace YOUR_TOKEN with actual token)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": "Plan a trip from New York to Boston"
    }]
  }'

# 4. Generate map
curl -X POST http://localhost:8000/v1/map/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "New York",
    "destination": "Boston",
    "zoom": 12
  }'
```

## Deployment

### Render.com

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Deploy on Render:**
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml`
   - Set environment variables (see `.env` example above)

3. **Environment Variables on Render:**
   - `MONGODB_URL` - MongoDB Atlas connection string
   - `DATABASE_NAME` - Database name
   - `SECRET_KEY` - JWT secret key
   - `GOOGLE_MAPS_API_KEY` - Google Maps API key
   - `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration (default: 30)
   - `PORT` - Port (Render sets this automatically)

**Note:** LLM model files are too large for Render's free tier. Consider:
- Using a smaller model (< 500MB)
- Disabling LLM features for production
- Using an external LLM API (OpenAI, Anthropic, etc.)

## Project Structure

```
backend/
├── main.py                 # FastAPI application
├── auth.py                 # Authentication routes
├── database.py             # MongoDB connection
├── conversation_memory.py # Message history management
├── google_maps_service.py  # Maps API integration
├── travel_agent_prompt.py  # LLM system prompts
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment config
├── Procfile               # Process file
├── models/                # GGUF model files
└── frontend-components/   # React components for frontend
```

## Troubleshooting

### Model Loading Issues

- **ctransformers fails:** Falls back to llama-cpp-python automatically
- **Model not found:** Check `MODEL_PATH` in `.env` matches your file location
- **Out of memory:** Use a smaller quantized model (Q4_K_M instead of Q8_0)

### Authentication Issues

- **401 Unauthorized:** User doesn't exist - sign up first
- **Token expired:** Sign in again to get a new token
- **Database connection:** Check `MONGODB_URL` in `.env`

### MongoDB Connection Issues (Windows)

MongoDB Atlas may have SSL issues on Windows. The code automatically tries multiple TLS configurations. If all fail:
- Use local MongoDB for development
- Or ensure you have the latest certificates installed

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## License

This project is part of the Tour Planner application.

