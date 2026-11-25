from typing import Any

from flask import Blueprint
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.api.errors import ConflictError, NotFoundError
from is1_trabajo_grupo26.api.validation import get_json_body, require_non_empty_string
from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.tag import Tag

tags_bp = Blueprint("tags", __name__, url_prefix="/tags")

MAX_TAG_LENGTH = 20


def serialize_tag(tag: Tag) -> dict[str, Any]:
    """Serializa una etiqueta ORM a diccionario JSON."""
    return {
        "id": tag.id,
        "title": tag.title,
    }


@tags_bp.get("", strict_slashes=False)
def list_tags():
    """Lista todas las etiquetas ordenadas por ID."""
    tags = db.session.execute(db.select(Tag).order_by(Tag.id.asc())).scalars().all()
    return {"tags": [serialize_tag(tag) for tag in tags]}


@tags_bp.get("/<int:tag_id>")
def get_tag(tag_id: int):
    """Obtiene una etiqueta por su ID o retorna 404."""
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        raise NotFoundError("Etiqueta no encontrada.")
    return serialize_tag(tag)


@tags_bp.post("", strict_slashes=False)
def create_tag():
    """Crea una etiqueta nueva validando duplicados (409)."""
    data = get_json_body()
    title = require_non_empty_string(data, "title", max_length=MAX_TAG_LENGTH)

    existing = db.session.execute(
        db.select(Tag).where(func.lower(Tag.title) == title.lower())
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Ya existe una etiqueta con ese título.")

    tag = Tag(title=title)
    db.session.add(tag)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError("Ya existe una etiqueta con ese título.") from exc

    return serialize_tag(tag), 201
