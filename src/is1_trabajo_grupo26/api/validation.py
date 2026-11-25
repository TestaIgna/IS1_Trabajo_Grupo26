from collections.abc import Iterable
from typing import Any

from flask import request

from is1_trabajo_grupo26.api.errors import BadRequestError, ValidationError


def get_json_body() -> dict[str, Any]:
    """Obtiene y valida que el cuerpo HTTP sea un objeto JSON válido."""
    if not request.is_json:
        raise BadRequestError(
            "El cuerpo de la petición debe tener Content-Type application/json."
        )

    data = request.get_json(silent=True)
    if data is None:
        raise BadRequestError("El cuerpo JSON es inválido o está malformado.")

    if not isinstance(data, dict):
        raise BadRequestError("El cuerpo JSON debe ser un objeto.")

    return data


def require_fields(data: dict[str, Any], fields: Iterable[str]) -> None:
    """Valida que todos los campos requeridos estén presentes y no sean None."""
    missing = [field for field in fields if field not in data or data[field] is None]
    if missing:
        raise ValidationError(
            "Faltan campos obligatorios.",
            details={"missing_fields": missing},
        )


def require_non_empty_string(
    data: dict[str, Any],
    field: str,
    *,
    max_length: int | None = None,
) -> str:
    """Valida que un campo sea str no vacío tras hacer strip y opcionalmente acotado."""
    if field not in data or data[field] is None:
        raise ValidationError(
            f"El campo '{field}' es obligatorio.",
            details={field: "El campo es obligatorio."},
        )

    value = data[field]
    if not isinstance(value, str):
        raise ValidationError(
            f"El campo '{field}' debe ser una cadena de texto.",
            details={field: "Debe ser una cadena de texto."},
        )

    normalized = value.strip()
    if not normalized:
        raise ValidationError(
            f"El campo '{field}' no puede estar vacío.",
            details={field: "No puede estar vacío."},
        )

    if max_length is not None and len(normalized) > max_length:
        raise ValidationError(
            f"El campo '{field}' supera el máximo de {max_length} caracteres.",
            details={field: f"Máximo {max_length} caracteres."},
        )

    return normalized


def require_int(
    data: dict[str, Any],
    field: str,
    *,
    positive: bool = False,
    optional: bool = False,
) -> int | None:
    """Valida un campo entero (rechazando bool) con opción de positividad y opcionalidad."""
    if field not in data or data[field] is None:
        if optional:
            return None
        raise ValidationError(
            f"El campo '{field}' es obligatorio.",
            details={field: "El campo es obligatorio."},
        )

    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(
            f"El campo '{field}' debe ser un número entero.",
            details={field: "Debe ser un número entero."},
        )

    if positive and value <= 0:
        raise ValidationError(
            f"El campo '{field}' debe ser un entero positivo.",
            details={field: "Debe ser mayor que 0."},
        )

    return value


def require_string_list(
    data: dict[str, Any],
    field: str,
    *,
    optional: bool = True,
) -> list[str]:
    """Valida una lista de cadenas no vacías y retorna sus valores normalizados."""
    if field not in data or data[field] is None:
        if optional:
            return []
        raise ValidationError(
            f"El campo '{field}' es obligatorio.",
            details={field: "El campo es obligatorio."},
        )

    value = data[field]
    if not isinstance(value, list):
        raise ValidationError(
            f"El campo '{field}' debe ser una lista de cadenas.",
            details={field: "Debe ser una lista."},
        )

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(
                f"Todos los elementos de '{field}' deben ser cadenas no vacías.",
                details={field: "Todos los elementos deben ser cadenas no vacías."},
            )
        normalized.append(item.strip())

    return normalized
