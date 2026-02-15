# Data Models

Database models and schema definitions using SQLAlchemy.

## Responsibility

The models layer defines the **data structure and persistence schema**.

It is responsible for:
- SQLAlchemy ORM models (tables, columns, relationships)
- Database schema definitions
- Data validation rules at the model level
- Data transfer objects (DTOs) for API contracts
- Type definitions for data structures

## What the Models Layer Does NOT Do

- **No business logic** - models are data containers, not actors
- **No query execution** - queries belong in services or repositories
- **No session management** - handled by database utilities
- **No API logic** - models are decoupled from HTTP layer

## Current Structure

### `base.py`
SQLAlchemy declarative base. All models inherit from `Base`.

### `__init__.py`
Package exports for easy imports.

## Migrations

Database migrations are managed with Alembic in `/alembic`.

No concrete business models exist yet.
