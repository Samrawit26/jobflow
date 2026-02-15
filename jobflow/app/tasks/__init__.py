"""
Tasks and async infrastructure package.

This package provides the async/task boundary for background job processing.
Currently inert - no active connections or workers.
"""

from .redis_client import get_redis_client

__all__ = ["get_redis_client"]
