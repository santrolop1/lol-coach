"""
backend/api/exception_handlers.py — Manejadores de errores globales.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


async def riot_api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"error": "riot_api_error", "detail": str(exc)},
    )


async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)},
    )
