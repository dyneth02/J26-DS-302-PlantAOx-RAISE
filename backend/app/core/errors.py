"""Shared exception types + FastAPI exception handlers.

Any component's service layer raises these instead of a bare FastAPI
HTTPException, so artifact-availability semantics stay consistent across
components: a missing/unreadable accepted artifact is always a 503 (the
capability is temporarily absent, not a client error), an unknown
fold/peptide/model id is always a 404.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ArtifactUnavailableError(RuntimeError):
    """An accepted research artifact this endpoint needs is missing, unreadable,
    or fails its integrity check in THIS checkout. Never caught and silently
    substituted with mock data -- surfaced to the client as 503."""

    def __init__(self, message: str, *, artifact_path: str | None = None) -> None:
        super().__init__(message)
        self.artifact_path = artifact_path


class ResourceNotFoundError(ValueError):
    """A client asked for an id (fold, peptide, model) that does not exist
    in the accepted artifacts. Surfaced as 404."""


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ArtifactUnavailableError)
    async def _artifact_unavailable(request: Request, exc: ArtifactUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": "artifact_unavailable",
                "detail": str(exc),
                "artifact_path": exc.artifact_path,
            },
        )

    @app.exception_handler(ResourceNotFoundError)
    async def _resource_not_found(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "detail": str(exc)},
        )
