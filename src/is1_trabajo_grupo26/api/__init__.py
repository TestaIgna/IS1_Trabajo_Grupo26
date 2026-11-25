from flask import Blueprint, Flask

from is1_trabajo_grupo26.api.errors import (
    ApiError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    ValidationError,
    register_error_handlers,
)
from is1_trabajo_grupo26.api.validation import (
    get_json_body,
    require_fields,
    require_int,
    require_non_empty_string,
    require_string_list,
)

# Punto centralizado para registrar sub-blueprints de la API (/api/...)
API_SUB_BLUEPRINTS: tuple[Blueprint, ...] = ()


def create_api_blueprint() -> Blueprint:
    """Construye una instancia fresca del blueprint raíz /api y sus sub-blueprints."""
    api_bp = Blueprint("api", __name__, url_prefix="/api")

    @api_bp.get("", strict_slashes=False)
    def api_index():
        """Endpoint base para comprobar la disponibilidad del prefijo /api."""
        return {"status": "ok", "api": "v1"}

    for sub_bp in API_SUB_BLUEPRINTS:
        api_bp.register_blueprint(sub_bp)

    return api_bp


def register_api(app: Flask) -> None:
    """Registra el blueprint /api y los manejadores uniformes de errores JSON."""
    app.register_blueprint(create_api_blueprint())
    register_error_handlers(app)


__all__ = [
    "API_SUB_BLUEPRINTS",
    "ApiError",
    "BadRequestError",
    "ConflictError",
    "InternalServerError",
    "NotFoundError",
    "ValidationError",
    "create_api_blueprint",
    "get_json_body",
    "register_api",
    "require_fields",
    "require_int",
    "require_non_empty_string",
    "require_string_list",
]
