from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

HTTP_ERRORS = {
    400: ("bad_request", "Bad request"),
    401: ("unauthorized", "Authentication required"),
    403: ("forbidden", "Forbidden"),
    404: ("not_found", "Not found"),
    409: ("conflict", "Conflict"),
    422: ("validation_error", "Request validation failed"),
    429: ("rate_limited", "Too many requests"),
    500: ("internal_error", "Internal server error"),
}
HTTP_ERROR_FALLBACK = ("http_error", "Request failed")


def _body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    del request
    code, message = HTTP_ERRORS.get(exc.status_code, HTTP_ERROR_FALLBACK)
    return JSONResponse(
        status_code=exc.status_code,
        content=_body(code, message),
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    del request, exc
    return JSONResponse(
        status_code=422,
        content=_body("validation_error", "Request validation failed"),
    )


async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    del request, exc
    return JSONResponse(
        status_code=500,
        content=_body("internal_error", "Internal server error"),
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
