"""
backend/api/middleware/logging.py — Middleware de logging de requests.
"""

from __future__ import annotations

import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("lol_coach.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s → %d (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response
