from typing import Any

from flask import Blueprint
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.api.errors import ConflictError, NotFoundError
from is1_trabajo_grupo26.api.validation import get_json_body, require_non_empty_string
from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.category import Category

categories_bp = Blueprint("categories", __name__, url_prefix="/categories")


def serialize_category(category: Category) -> dict[str, Any]:
    """Serializa una categoría ORM a diccionario JSON."""
    return {
        "id": category.id,
        "name": category.name,
    }


@categories_bp.get("", strict_slashes=False)
def list_categories():
    """Lista todas las categorías ordenadas por ID."""
    categories = (
        db.session.execute(db.select(Category).order_by(Category.id.asc()))
        .scalars()
        .all()
    )
    return {"categories": [serialize_category(cat) for cat in categories]}


@categories_bp.get("/<int:category_id>")
def get_category(category_id: int):
    """Obtiene una categoría por su ID o retorna 404."""
    category = db.session.get(Category, category_id)
    if category is None:
        raise NotFoundError("Categoría no encontrada.")
    return serialize_category(category)


@categories_bp.post("", strict_slashes=False)
def create_category():
    """Crea una categoría nueva validando duplicados (409)."""
    data = get_json_body()
    name = require_non_empty_string(data, "name", max_length=100)

    existing = db.session.execute(
        db.select(Category).where(func.lower(Category.name) == name.lower())
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Ya existe una categoría con ese nombre.")

    category = Category(name=name)
    db.session.add(category)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError("Ya existe una categoría con ese nombre.") from exc

    return serialize_category(category), 201
