from typing import Any

from flask import Blueprint, request

from is1_trabajo_grupo26.api.errors import ApiError, NotFoundError, ValidationError
from is1_trabajo_grupo26.api.users import serialize_user
from is1_trabajo_grupo26.api.validation import get_json_body, require_int
from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.response import Response

answers_api_bp = Blueprint("answers_api", __name__, url_prefix="/answers")


def serialize_answer(response: Response) -> dict[str, Any]:
    """Serializa una respuesta ORM junto con su autor y puntuación."""
    return {
        "id": response.id,
        "body": response.body,
        "date": response.date.isoformat(),
        "is_accepted": response.is_accepted,
        "question_id": response.question_id,
        "author": serialize_user(response.author),
        "score": response.calculate_score(),
    }


@answers_api_bp.patch("/<int:answer_id>/accept")
def accept_answer(answer_id: int):
    """Marca (o desmarca) una respuesta como aceptada para su pregunta."""
    response = db.session.get(Response, answer_id)
    if response is None:
        raise NotFoundError("Respuesta no encontrada.")

    is_accepted = True
    has_payload = bool(request.data and request.data.strip()) or request.is_json
    if has_payload:
        data = get_json_body()
        actor_id = require_int(data, "author_id", positive=True, optional=True)
        if actor_id is None:
            actor_id = require_int(data, "user_id", positive=True, optional=True)
        if actor_id is not None and actor_id != response.question.author_id:
            raise ApiError(
                "Solo el autor de la pregunta puede aceptar una respuesta.",
                status_code=403,
                code="forbidden",
            )

        if "is_accepted" in data and data["is_accepted"] is not None:
            if not isinstance(data["is_accepted"], bool):
                raise ValidationError(
                    "El campo 'is_accepted' debe ser booleano.",
                    details={"is_accepted": "Debe ser true o false."},
                )
            is_accepted = data["is_accepted"]

    if is_accepted:
        other_accepted = (
            db.session.execute(
                db.select(Response).where(
                    Response.question_id == response.question_id,
                    Response.id != response.id,
                    Response.is_accepted.is_(True),
                )
            )
            .scalars()
            .all()
        )
        for other in other_accepted:
            other.is_accepted = False

    response.is_accepted = is_accepted
    db.session.commit()
    return serialize_answer(response)
