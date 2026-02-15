# Tasks / Async Infrastructure

Asynchronous task queue and background job infrastructure.

## Purpose

This package defines the **async/task boundary** for background job processing.

It provides:
- Redis connection management
- Task queue client definitions
- Background job interfaces
- Async task infrastructure setup

## Responsibility

The tasks layer is responsible for:
- Redis client initialization and connection pooling
- Task queue configuration (e.g., Celery, RQ, or custom)
- Background job registration and routing
- Async task serialization/deserialization
- Task retry and failure handling policies
- Queue monitoring utilities

## What the Tasks Layer Does NOT Do

- **No business logic** - delegates to execution scripts in `/execution`
- **No direct API calls** - tasks are triggered by services or API layer
- **No worker implementation here** - actual workers live in `/services/worker` if needed
- **No task execution** - this defines infrastructure, not runtime
- **No FastAPI dependencies** - decoupled from HTTP layer

## Architecture Pattern

```
API/Service → enqueue task → Redis Queue → Worker → Execution Script
```

The tasks layer only handles the "enqueue task" and queue infrastructure parts.

## Current Structure

### `redis_client.py`
Redis connection placeholder. No actual connection established yet.

### `__init__.py`
Package exports for task infrastructure.

## When to Use Background Tasks

Use async tasks for:
- Long-running operations (>2 seconds)
- Operations that can fail and need retries
- Scheduled/periodic jobs
- Email sending, file processing, external API calls
- Anything that shouldn't block an HTTP request

Do NOT use async tasks for:
- Simple CRUD operations
- Operations requiring immediate user feedback
- Transactions that must complete atomically with the request

## Status

Currently inert. No workers running, no tasks enqueued, no Redis connection active.
