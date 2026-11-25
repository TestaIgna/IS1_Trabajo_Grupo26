from flask import Blueprint, jsonify, request

from is1_trabajo_grupo26.models.vote import VoteType
from is1_trabajo_grupo26.services.vote_service import register_vote

votes_bp = Blueprint("votes", __name__, url_prefix="/api/votes")


@votes_bp.post("")
def create_vote():
    """Registra un voto (POSITIVE o NEGATIVE) sobre una pregunta o una respuesta."""
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    raw_vote = data.get("vote") or data.get("vote_type")
    question_id = data.get("question_id")
    response_id = data.get("response_id")

    if user_id is None or not isinstance(raw_vote, str):
        return (
            jsonify({"error": "Se requieren user_id y vote (POSITIVE o NEGATIVE)."}),
            400,
        )

    normalized_vote = raw_vote.strip().upper()
    if normalized_vote not in VoteType.__members__:
        return (
            jsonify({"error": "El tipo de voto debe ser POSITIVE o NEGATIVE."}),
            400,
        )

    try:
        vote = register_vote(
            user_id=user_id,
            vote_type=VoteType[normalized_vote],
            question_id=question_id,
            response_id=response_id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return (
        jsonify(
            {
                "id": vote.id,
                "user_id": vote.user_id,
                "vote": vote.vote.value,
                "question_id": vote.question_id,
                "response_id": vote.response_id,
            }
        ),
        201,
    )