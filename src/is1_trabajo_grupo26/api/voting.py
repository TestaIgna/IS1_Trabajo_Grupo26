from typing import Any

from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.api.errors import (
    ApiError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from is1_trabajo_grupo26.api.validation import get_json_body, require_int
from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.models.vote import Vote, VoteType

voting_api_bp = Blueprint("voting_api", __name__, url_prefix="/votes")

_VOTE_ALIASES: dict[str, VoteType] = {
    "POSITIVE": VoteType.POSITIVE,
    "POSITIVO": VoteType.POSITIVE,
    "NEGATIVE": VoteType.NEGATIVE,
    "NEGATIVO": VoteType.NEGATIVE,
}


def _parse_vote_type(data: dict[str, Any]) -> VoteType:
    raw = data.get("vote") if data.get("vote") is not None else data.get("vote_type")
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError(
            "El campo 'vote' es obligatorio y debe ser POSITIVE o NEGATIVE.",
            details={"vote": "Valores permitidos: POSITIVE/POSITIVO o NEGATIVE/NEGATIVO."},
        )

    vote_type = _VOTE_ALIASES.get(raw.strip().upper())
    if vote_type is None:
        raise ValidationError(
            "El tipo de voto debe ser POSITIVE/POSITIVO o NEGATIVE/NEGATIVO.",
            details={"vote": "Valores permitidos: POSITIVE/POSITIVO o NEGATIVE/NEGATIVO."},
        )
    return vote_type


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


def _resolve_target_score(vote: Vote) -> int:
    target = vote.question if vote.question_id is not None else vote.response
    return target.calculate_score()


def serialize_vote(vote: Vote, *, score: int | None = None) -> dict[str, Any]:
    """Serializa un voto ORM incluyendo la puntuación actual del recurso votado."""
    return {
        "id": vote.id,
        "user_id": vote.user_id,
        "vote": vote.vote.value,
        "question_id": vote.question_id,
        "response_id": vote.response_id,
        "score": _resolve_target_score(vote) if score is None else score,
    }


@voting_api_bp.get("", strict_slashes=False)
def list_votes():
    """Lista votos con filtros opcionales y devuelve puntuación si aplica."""
    question_id = _parse_query_int("question_id")
    response_id = _parse_query_int("response_id")
    user_id = _parse_query_int("user_id")

    if question_id is not None and response_id is not None:
        raise BadRequestError(
            "No se puede filtrar por pregunta y respuesta al mismo tiempo (regla XOR)."
        )

    stmt = db.select(Vote).order_by(Vote.id.asc())
    target_score: int | None = None

    if question_id is not None:
        question = db.session.get(Question, question_id)
        if question is None:
            raise NotFoundError("Pregunta no encontrada.")
        stmt = stmt.where(Vote.question_id == question_id)
        target_score = question.calculate_score()

    if response_id is not None:
        response = db.session.get(Response, response_id)
        if response is None:
            raise NotFoundError("Respuesta no encontrada.")
        stmt = stmt.where(Vote.response_id == response_id)
        target_score = response.calculate_score()

    if user_id is not None:
        stmt = stmt.where(Vote.user_id == user_id)

    votes = db.session.execute(stmt).scalars().all()
    payload: dict[str, Any] = {"votes": [serialize_vote(vote) for vote in votes]}
    if target_score is not None:
        payload["score"] = target_score
    return payload


@voting_api_bp.get("/<int:vote_id>")
def get_vote(vote_id: int):
    """Obtiene un voto puntual junto con la puntuación actual de su objetivo."""
    vote = db.session.get(Vote, vote_id)
    if vote is None:
        raise NotFoundError("Voto no encontrado.")
    return serialize_vote(vote)


@voting_api_bp.post("", strict_slashes=False)
def create_vote():
    """Emite un voto único POSITIVE/NEGATIVE cumpliendo la regla {XOR}."""
    data = get_json_body()
    user_id = require_int(data, "user_id", positive=True)
    question_id = require_int(data, "question_id", positive=True, optional=True)
    response_id = require_int(data, "response_id", positive=True, optional=True)

    # Regla XOR: debe apuntar a una pregunta O a una respuesta, nunca a ambos ni a ninguno
    if (question_id is None) == (response_id is None):
        raise BadRequestError(
            "Un voto debe dirigirse exclusivamente a una pregunta o a una respuesta (regla XOR)."
        )

    vote_type = _parse_vote_type(data)

    user = db.session.get(Author, user_id)
    if user is None:
        raise NotFoundError("Usuario no encontrado.")

    if question_id is not None:
        target = db.session.get(Question, question_id)
        if target is None:
            raise NotFoundError("Pregunta no encontrada.")
    else:
        target = db.session.get(Response, response_id)
        if target is None:
            raise NotFoundError("Respuesta no encontrada.")

    existing = db.session.execute(
        db.select(Vote).where(
            Vote.user_id == user_id,
            Vote.question_id == question_id,
            Vote.response_id == response_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            "El usuario ya emitió un voto para este elemento.",
            details={"vote_id": existing.id},
        )

    vote = Vote(
        user=user,
        vote=vote_type,
        question_id=question_id,
        response_id=response_id,
    )
    db.session.add(vote)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError("El usuario ya emitió un voto para este elemento.") from exc

    db.session.refresh(target)
    return serialize_vote(vote, score=target.calculate_score()), 201


@voting_api_bp.patch("/<int:vote_id>")
def update_vote(vote_id: int):
    """Actualiza el sentido de un voto existente (POSITIVE <-> NEGATIVE)."""
    vote = db.session.get(Vote, vote_id)
    if vote is None:
        raise NotFoundError("Voto no encontrado.")

    data = get_json_body()
    actor_id = require_int(data, "user_id", positive=True, optional=True)
    if actor_id is not None and actor_id != vote.user_id:
        raise ApiError(
            "Solo el autor del voto puede modificarlo.",
            status_code=403,
            code="forbidden",
        )

    if "question_id" in data or "response_id" in data:
        req_q = require_int(data, "question_id", positive=True, optional=True)
        req_r = require_int(data, "response_id", positive=True, optional=True)
        if req_q != vote.question_id or req_r != vote.response_id:
            raise BadRequestError(
                "No se puede reasignar el objetivo de un voto existente (regla XOR)."
            )

    vote.vote = _parse_vote_type(data)
    db.session.commit()

    target = vote.question if vote.question_id is not None else vote.response
    db.session.refresh(target)
    return serialize_vote(vote, score=target.calculate_score())


@voting_api_bp.delete("/<int:vote_id>")
def delete_vote(vote_id: int):
    """Elimina un voto existente y retorna la puntuación recalculada."""
    vote = db.session.get(Vote, vote_id)
    if vote is None:
        raise NotFoundError("Voto no encontrado.")

    actor_id = _parse_query_int("user_id")
    has_payload = bool(request.data and request.data.strip()) or request.is_json
    if actor_id is None and has_payload:
        data = get_json_body()
        actor_id = require_int(data, "user_id", positive=True, optional=True)

    if actor_id is not None and actor_id != vote.user_id:
        raise ApiError(
            "Solo el autor del voto puede eliminarlo.",
            status_code=403,
            code="forbidden",
        )

    question_id = vote.question_id
    response_id = vote.response_id
    target = vote.question if question_id is not None else vote.response

    db.session.delete(vote)
    db.session.commit()
    db.session.refresh(target)

    return {
        "deleted": True,
        "vote_id": vote_id,
        "question_id": question_id,
        "response_id": response_id,
        "score": target.calculate_score(),
    }
