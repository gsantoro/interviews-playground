from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import CapacityError, KeyNotFound, TypeMismatch


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(KeyNotFound)
    def handle_key_not_found(request: Request, exc: KeyNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TypeMismatch)
    def handle_type_mismatch(request: Request, exc: TypeMismatch) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(CapacityError)
    def handle_capacity_error(request: Request, exc: CapacityError) -> JSONResponse:
        return JSONResponse(status_code=507, content={"detail": str(exc)})
