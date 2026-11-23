from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.vote import Vote, VoteType


def register_vote(
    user_id: int,
    vote_type: VoteType | str,
    question_id: int | None = None,
    response_id: int | None = None,
) -> Vote:
    """Registra un voto único (+1 / -1) sobre una pregunta o una respuesta (XOR)."""
    if user_id is None:
        raise ValueError("El user_id es obligatorio para emitir un voto.")

    # Normaliza vote_type por si llega como string ("POSITIVE" / "NEGATIVE")
    normalized_vote = (
        vote_type
        if isinstance(vote_type, VoteType)
        else VoteType(str(vote_type).strip().upper())
    )

    has_question = question_id is not None
    has_response = response_id is not None

    # Regla XOR: debe apuntar a pregunta O a respuesta, nunca a ambos ni a ninguno
    if has_question == has_response:
        raise ValueError(
            "Un voto debe dirigirse exclusivamente a una pregunta o a una respuesta."
        )

    existing_vote = Vote.query.filter_by(
        user_id=user_id,
        question_id=question_id,
        response_id=response_id,
    ).first()

    if existing_vote is not None:
        raise ValueError("El usuario ya emitió un voto para este elemento.")

    new_vote = Vote(
        user_id=user_id,
        vote=normalized_vote,
        question_id=question_id,
        response_id=response_id,
    )

    db.session.add(new_vote)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError(
            "No se pudo registrar el voto (posible voto duplicado o referencia inválida)."
        ) from exc

    return new_vote