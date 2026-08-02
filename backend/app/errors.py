import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.requests import ClientDisconnect

log = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ClientDisconnect)
    async def client_disconnect_handler(request: Request, exc: ClientDisconnect) -> Response:
        # Slack (and other platforms) routinely disconnect immediately after
        # sending a webhook — before we finish reading the body. This is normal
        # network behaviour, not a server error. Log at DEBUG to avoid noise.
        log.debug(
            "[CHECKPOINT: CLIENT_DISCONNECT] Client disconnected early on %s %s",
            request.method,
            request.url.path,
        )
        return Response(status_code=200)

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
        log.error("[CHECKPOINT: ERROR 500] File not found: %s", exc)
        return JSONResponse(status_code=500, content={"detail": f"File not found: {exc}"})

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        log.error("[CHECKPOINT: ERROR 400] Value error: %s", exc)
        return JSONResponse(status_code=400, content={"detail": f"Invalid input: {exc}"})

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
        log.error("[CHECKPOINT: ERROR 502] Upstream error: %s", exc)
        return JSONResponse(status_code=502, content={"detail": f"Upstream error: {exc}"})

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("[CHECKPOINT: ERROR 500] Generic server error: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

