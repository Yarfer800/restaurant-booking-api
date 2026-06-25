from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 500
    detail: str = "Internal Server Error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "Not found"


class ConflictError(AppError):
    status_code = 409
    detail = "Conflict"


class ValidationError(AppError):
    status_code = 400
    detail = "Invalid data"


class AuthError(AppError):
    status_code = 401
    detail = "Authentication required"


class ForbiddenError(AppError):
    status_code = 403
    detail = "Forbidden"


class RateLimitError(AppError):
    status_code = 429
    detail = "Too many requests"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
