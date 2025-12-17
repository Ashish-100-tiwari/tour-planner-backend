# Chat Endpoint Curl Examples

## Step 1: Sign In to Get Access Token

```bash
curl -X POST http://localhost:8000/auth/signin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password123"
  }'
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

## Step 2: Use Chat Endpoint (Authenticated Users Only)

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "What are the best tourist places in Paris?"
      }
    ],
    "temperature": 0.7,
    "max_tokens": 512
  }'
```

**Note:** Replace `YOUR_ACCESS_TOKEN` with the actual token from the signin response.

**Response:**
```json
{
  "id": "chatcmpl-123456789",
  "object": "chat.completion",
  "created": 1702671234,
  "model": "llama-3.2-3b-instruct",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Paris has many amazing tourist attractions..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 120,
    "total_tokens": 135
  }
}
```

## If You Try Without Authentication

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "What are the best tourist places in Paris?"
      }
    ]
  }'
```

**Response (401 Unauthorized):**
```json
{
  "detail": "Not authenticated"
}
```
