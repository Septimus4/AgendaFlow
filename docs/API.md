# API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

Most endpoints are public except `/rebuild` which requires a Bearer token:

```
Authorization: Bearer your_rebuild_token
```

## Endpoints

### POST /ask

Ask event-related questions and get intelligent answers.

**Request Body:**

```json
{
  "question": "string (required)",
  "from_date": "string (optional, ISO 8601)",
  "to_date": "string (optional, ISO 8601)",
  "category": "string (optional)",
  "price": "string (optional)",
  "arrondissement": "integer (optional, 1-20)",
  "language": "string (optional, 'fr' or 'en')"
}
```

**Categories:**
- music
- theater
- exhibition
- kids
- festival
- cinema
- dance
- literature
- workshop

**Price Constraints:**
- free
- cheap

**Response:**

```json
{
  "answer": "string",
  "events": [
    {
      "title": "string",
      "start_datetime": "string (ISO 8601)",
      "venue_name": "string",
      "city": "string",
      "arrondissement": "string",
      "price": "string",
      "url": "string",
      "categories": ["string"]
    }
  ],
  "sources": ["string"],
  "filters_applied": {
    "start_date": "datetime",
    "end_date": "datetime",
    "category": "string",
    "price_constraint": "string",
    "arrondissement": "integer"
  },
  "latency_ms": "integer",
  "retrieval_ms": "integer",
  "generation_ms": "integer",
  "trace_id": "string"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quels concerts de jazz ce week-end ?",
    "category": "music",
    "price": "free"
  }'
```

### POST /rebuild

Rebuild the event index from OpenAgenda.

**Headers:**
```
Authorization: Bearer your_rebuild_token
```

**Request Body:**

```json
{
  "mode": "string (optional, 'full' or 'incremental')",
  "since": "string (optional, ISO 8601)"
}
```

**Response:**

```json
{
  "status": "string",
  "events_fetched": "integer",
  "events_indexed": "integer",
  "duration_seconds": "float",
  "manifest_hash": "string"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/rebuild \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{"mode": "full"}'
```

### GET /health

Check service health and readiness.

**Response:**

```json
{
  "status": "string ('healthy' or 'degraded')",
  "index_loaded": "boolean",
  "index_size": "integer",
  "timestamp": "string (ISO 8601)"
}
```

**Example:**

```bash
curl http://localhost:8000/health
```

### GET /metrics

Prometheus-compatible metrics endpoint.

**Response:**

Prometheus text format with metrics:
- `agendaflow_requests_total` - Total requests counter
- `agendaflow_request_duration_seconds` - Request latency histogram
- `agendaflow_retrieval_duration_seconds` - Retrieval latency histogram
- `agendaflow_generation_duration_seconds` - Generation latency histogram

**Example:**

```bash
curl http://localhost:8000/metrics
```

### GET /

Root endpoint with service information.

**Response:**

```json
{
  "service": "AgendaFlow",
  "version": "0.1.0",
  "description": "RAG service for Paris event queries",
  "endpoints": {
    "POST /ask": "Ask event-related questions",
    "POST /rebuild": "Rebuild event index (requires auth)",
    "GET /health": "Health check",
    "GET /metrics": "Prometheus metrics"
  }
}
```

## Error Responses

All endpoints may return error responses:

**400 Bad Request:**
```json
{
  "detail": "Error message"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Authorization header missing"
}
```

**403 Forbidden:**
```json
{
  "detail": "Invalid token"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error: ..."
}
```

**503 Service Unavailable:**
```json
{
  "detail": "Index not loaded. Please build the index first using POST /rebuild."
}
```

## Rate Limiting

The service includes basic rate limiting (configurable via environment variables). Default: 30 requests per minute.

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
