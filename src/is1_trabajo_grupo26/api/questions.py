from typing import Any

from flask import Blueprint, request
from sqlalchemy import func

from is1_trabajo_grupo26.api.answers import serialize_answer
from is1_trabajo_grupo26.api.categories import serialize_category
from is1_trabajo_grupo26.api.errors import NotFoundError, ValidationError
from is1_trabajo_grupo26.api.tags import serialize_tag
from is1_trabajo_grupo26.api.users import serialize_user
from is1_trabajo_grupo26.api.validation import (
    get_json_body,
    require_int,
    require_non_empty_string,
    require_string_list,
)
from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.category import Category
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.models.tag import Tag
from is1_trabajo_grupo26.services.ai_answer_service import (
    generate_ai_response_for_question,
    resolve_ai_strategy,
)

questions_api_bp = Blueprint("questions_api", __name__, url_prefix="/questions")


def serialize_question(
    question: Question,
    *,
    include_answers: bool = False,
) -> dict[str, Any]:
    """Serializa una pregunta ORM con categoría, autor, etiquetas y puntaje."""
    payload: dict[str, Any] = {
        "id": question.id,
        "title": question.title,
        "body": question.body,
        "date": question.date.isoformat(),
        "category": serialize_category(question.category),
        "author": serialize_user(question.author),
        "tags": [serialize_tag(tag) for tag in question.tags],
        "score": question.calculate_score(),
        "answers_count": len(question.responses),
    }
    if include_answers:
        ordered_answers = sorted(question.responses, key=lambda item: item.id or 0)
        payload["answers"] = [serialize_answer(ans) for ans in ordered_answers]
    return payload


def _parse_query_int(param_name: str) -> int | None:
    raw_value = request.args.get(param_name)
    if raw_value is None or raw_value == "":
        return None
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValidationError(
            f"El parámetro '{param_name}' debe ser un número entero.",
            details={param_name: "Debe ser un número entero."},
        ) from exc
    if parsed <= 0:
        raise ValidationError(
            f"El parámetro '{param_name}' debe ser mayor que 0.",
            details={param_name: "Debe ser mayor que 0."},
        )
    return parsed


def _resolve_tags(data: dict[str, Any]) -> list[Tag]:
    resolved: list[Tag] = []
    seen_ids: set[int] = set()

    if "tag_ids" in data and data["tag_ids"] is not None:
        raw_ids = data["tag_ids"]
        if not isinstance(raw_ids, list):
            raise ValidationError(
                "El campo 'tag_ids' debe ser una lista de enteros.",
                details={"tag_ids": "Debe ser una lista de enteros."},
            )
        for item in raw_ids:
            if isinstance(item, bool) or not isinstance(item, int) or item <= 0:
                raise ValidationError(
                    "Todos los elementos de 'tag_ids' deben ser enteros positivos.",
                    details={"tag_ids": "Debe contener solo enteros positivos."},
                )
            tag = db.session.get(Tag, item)
            if tag is None:
                raise NotFoundError(f"Etiqueta con id {item} no encontrada.")
            if tag.id not in seen_ids:
                seen_ids.add(tag.id)
                resolved.append(tag)

    tag_titles = require_string_list(data, "tags", optional=True)
    for title in tag_titles:
        tag = db.session.execute(
            db.select(Tag).where(func.lower(Tag.title) == title.lower())
        ).scalar_one_or_none()
        if tag is None:
            tag = Tag(title=title)
            db.session.add(tag)
            db.session.flush()
        if tag.id not in seen_ids:
            seen_ids.add(tag.id)
            resolved.append(tag)

    return resolved


@questions_api_bp.get("", strict_slashes=False)
def list_questions():
    """Lista preguntas con filtros opcionales por categoría y etiqueta."""
    category_id = _parse_query_int("category_id")
    category_name = (request.args.get("category") or "").strip()
    tag_id = _parse_query_int("tag_id")
    tag_title = (request.args.get("tag") or "").strip()

    stmt = db.select(Question).distinct().order_by(Question.id.asc())
    if category_id is not None:
        stmt = stmt.where(Question.category_id == category_id)
    if category_name:
        stmt = stmt.join(Question.category).where(
            func.lower(Category.name) == category_name.lower()
        )
    if tag_id is not None or tag_title:
        stmt = stmt.join(Question.tags)
        if tag_id is not None:
            stmt = stmt.where(Tag.id == tag_id)
        if tag_title:
            stmt = stmt.where(func.lower(Tag.title) == tag_title.lower())

    questions = db.session.execute(stmt).scalars().all()
    return {"questions": [serialize_question(q) for q in questions]}


@questions_api_bp.get("/<int:question_id>")
def get_question(question_id: int):
    """Obtiene el detalle de una pregunta con sus respuestas."""
    question = db.session.get(Question, question_id)
    if question is None:
        raise NotFoundError("Pregunta no encontrada.")
    return serialize_question(question, include_answers=True)


@questions_api_bp.post("", strict_slashes=False)
def create_question():
    """Crea una pregunta y dispara respuesta automática de IA si incluye #ia-help."""
    data = get_json_body()
    title = require_non_empty_string(data, "title", max_length=200)
    body = require_non_empty_string(data, "body")
    category_id = require_int(data, "category_id", positive=True)
    author_id = require_int(data, "author_id", positive=True)

    auto_answer_ai = data.get("auto_answer_ai", True)
    if not isinstance(auto_answer_ai, bool):
        raise ValidationError(
            "El campo 'auto_answer_ai' debe ser booleano.",
            details={"auto_answer_ai": "Debe ser true o false."},
        )

    ai_provider = data.get("ai_provider", "local")
    try:
        resolve_ai_strategy(ai_provider)
    except ValueError as exc:
        raise ValidationError(str(exc), details={"ai_provider": str(exc)}) from exc

    category = db.session.get(Category, category_id)
    if category is None:
        raise NotFoundError("Categoría no encontrada.")

    author = db.session.get(Author, author_id)
    if author is None:
        raise NotFoundError("Autor no encontrado.")

    tags = _resolve_tags(data)
    question = Question(
        title=title,
        body=body,
        category=category,
        author=author,
        tags=tags,
    )
    db.session.add(question)
    db.session.flush()

    if auto_answer_ai:
        generate_ai_response_for_question(question, provider=ai_provider)

    db.session.commit()
    return serialize_question(question, include_answers=True), 201


@questions_api_bp.patch("/<int:question_id>")
def update_question(question_id: int):
    """Actualiza parcialmente título, cuerpo, categoría o tags de una pregunta."""
    question = db.session.get(Question, question_id)
    if question is None:
        raise NotFoundError("Pregunta no encontrada.")

    data = get_json_body()
    updatable = {"title", "body", "category_id", "tags", "tag_ids"}
    if not any(field in data for field in updatable):
        raise ValidationError("Debe enviar al menos un campo para actualizar.")

    if "title" in data:
        question.title = require_non_empty_string(data, "title", max_length=200)
    if "body" in data:
        question.body = require_non_empty_string(data, "body")
    if "category_id" in data:
        category_id = require_int(data, "category_id", positive=True)
        category = db.session.get(Category, category_id)
        if category is None:
            raise NotFoundError("Categoría no encontrada.")
        question.category = category
    if "tags" in data or "tag_ids" in data:
        question.tags = _resolve_tags(data)

    db.session.commit()
    return serialize_question(question, include_answers=True)


@questions_api_bp.delete("/<int:question_id>")
def delete_question(question_id: int):
    """Elimina una pregunta y sus respuestas/votos asociados por cascada."""
    question = db.session.get(Question, question_id)
    if question is None:
        raise NotFoundError("Pregunta no encontrada.")

    db.session.delete(question)
    db.session.commit()
    return "", 204


@questions_api_bp.get("/<int:question_id>/answers")
def list_question_answers(question_id: int):
    """Lista todas las respuestas asociadas a una pregunta."""
    question = db.session.get(Question, question_id)
    if question is None:
        raise NotFoundError("Pregunta no encontrada.")

    answers = (
        db.session.execute(
            db.select(Response)
            .where(Response.question_id == question.id)
            .order_by(Response.id.asc())
        )
        .scalars()
        .all()
    )
    return {"answers": [serialize_answer(ans) for ans in answers]}


@questions_api_bp.post("/<int:question_id>/answers")
def create_question_answer(question_id: int):
    """Publica una nueva respuesta humana o manual sobre una pregunta."""
    question = db.session.get(Question, question_id)
    if question is None:
        raise NotFoundError("Pregunta no encontrada.")

    data = get_json_body()
    body = require_non_empty_string(data, "body")
    author_id = require_int(data, "author_id", positive=True)

    author = db.session.get(Author, author_id)
    if author is None:
        raise NotFoundError("Autor no encontrado.")

    response = Response(body=body, question=question, author=author)
    db.session.add(response)
    db.session.commit()
    return serialize_answer(response), 201
