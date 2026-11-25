import logging
from typing import Any

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

_HTTP_ERROR_MAP: dict[int, tuple[str, str]] = {
    400: ("bad_request", "Solicitud inválida."),
    404: ("not_found", "Recurso no encontrado."),
    405: ("method_not_allowed", "Método HTTP no permitido."),
    409: ("conflict", "Conflicto con el estado actual del recurso."),
    422: ("unprocessable_entity", "Los datos enviados no son válidos."),
    500: ("internal_server_error", "Error interno del servidor."),
}


class ApiError(Exception):
    """Excepción base para errores controlados de la API REST."""

    default_status_code = 400
    default_code = "bad_request"
    default_message = "Solicitud inválida."

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        resolved_message = message or self.default_message
        super().__init__(resolved_message)
        self.message = resolved_message
        self.status_code = (
            status_code if status_code is not None else self.default_status_code
        )
        self.code = code or self.default_code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        """Serializa el error en el formato JSON uniforme de la API."""
        payload: dict[str, Any] = {
            "error": self.message,
            "code": self.code,
            "status": self.status_code,
        }
        if self.details is not None:
            payload["details"] = self.details
        return payload


class BadRequestError(ApiError):
    """Error 400 para cuerpos JSON ausentes o malformados."""

    default_status_code = 400
    default_code = "bad_request"
    default_message = "Solicitud inválida."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=self.default_status_code,
            code=code or self.default_code,
            details=details,
        )


class NotFoundError(ApiError):
    """Error 404 para recursos inexistentes en la API."""

    default_status_code = 404
    default_code = "not_found"
    default_message = "Recurso no encontrado."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=self.default_status_code,
            code=code or self.default_code,
            details=details,
        )


class ConflictError(ApiError):
    """Error 409 para conflictos de unicidad o estado (duplicados, etc.)."""

    default_status_code = 409
    default_code = "conflict"
    default_message = "Conflicto con el estado actual del recurso."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=self.default_status_code,
            code=code or self.default_code,
            details=details,
        )


class ValidationError(ApiError):
    """Error 422 para fallos de validación semántica en campos JSON."""

    default_status_code = 422
    default_code = "unprocessable_entity"
    default_message = "Los datos enviados no son válidos."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=self.default_status_code,
            code=code or self.default_code,
            details=details,
        )


class InternalServerError(ApiError):
    """Error 500 para fallos internos inesperados dentro de /api."""

    default_status_code = 500
    default_code = "internal_server_error"
    default_message = "Error interno del servidor."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=self.default_status_code,
            code=code or self.default_code,
            details=details,
        )


def is_api_request() -> bool:
    """Indica si la petición actual apunta a un endpoint bajo /api."""
    path = request.path or ""
    return path == "/api" or path.startswith("/api/")


def build_error_response(
    status_code: int,
    message: str,
    *,
    code: str | None = None,
    details: dict[str, Any] | None = None,
):
    """Construye una respuesta Flask JSON uniforme para errores de la API."""
    resolved_code = code or _HTTP_ERROR_MAP.get(status_code, ("api_error", ""))[0]
    payload: dict[str, Any] = {
        "error": message,
        "code": resolved_code,
        "status": status_code,
    }
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status_code


def _http_exception_to_json(exc: HTTPException):
    status_code = exc.code or 500
    code, default_message = _HTTP_ERROR_MAP.get(
        status_code,
        ("http_error", exc.description or "Error HTTP en la solicitud."),
    )
    return build_error_response(status_code, default_message, code=code)


def register_error_handlers(app: Flask) -> None:
    """Registra manejadores uniformes de error JSON acotados a rutas /api."""

    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError):
        return build_error_response(
            exc.status_code,
            exc.message,
            code=exc.code,
            details=exc.details,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        if not is_api_request():
            return exc
        return _http_exception_to_json(exc)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(exc: Exception):
        if isinstance(exc, HTTPException):
            return handle_http_exception(exc)

        if not is_api_request():
            raise exc

        if app.config.get("PROPAGATE_EXCEPTIONS") or (
            app.testing and app.config.get("PROPAGATE_EXCEPTIONS") is not False
        ):
            raise exc

        logger.exception("Error interno no controlado en la API (%s)", request.path)
        return build_error_response(
            500,
            "Error interno del servidor.",
            code="internal_server_error",
        )
