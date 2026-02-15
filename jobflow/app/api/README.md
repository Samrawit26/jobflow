# API Layer

FastAPI application and HTTP endpoint definitions.

## Responsibility

The API layer is the **HTTP boundary** of the application.

It is responsible for:
- Defining HTTP routes and methods
- Request validation (input sanitization, type checking)
- Response formatting (status codes, JSON serialization)
- API authentication and authorization
- Error handling and HTTP error responses

## What the API Layer Does NOT Do

- **No business logic** - delegates to `core/` or `services/`
- **No direct database access** - uses models and services
- **No complex orchestration** - calls execution scripts when needed
- **No LLM prompts or probabilistic behavior** - purely deterministic

## Current Endpoints

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

Returns 200 OK when the application is running.
