from enum import Enum

from is1_trabajo_grupo26.extensions import db


class VoteType(str, Enum):
    """Tipos de voto permitidos sobre preguntas y respuestas."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


Type_vote = VoteType


def calculate_vote_score(votes: list["Vote"]) -> int:
    """Calcula la puntuación neta sumando votos positivos y restando negativos."""
    return sum(1 if v.vote == VoteType.POSITIVE else -1 for v in votes)


class Vote(db.Model):
    """Voto emitido por un usuario sobre una pregunta o una respuesta (XOR)."""

    __tablename__ = "votes"
    __table_args__ = (
        db.CheckConstraint(
            "(question_id IS NOT NULL AND response_id IS NULL) "
            "OR (question_id IS NULL AND response_id IS NOT NULL)",
            name="ck_vote_question_xor_response",
        ),
        db.UniqueConstraint("user_id", "question_id", name="uq_vote_user_question"),
        db.UniqueConstraint("user_id", "response_id", name="uq_vote_user_response"),
    )

    id = db.Column(db.Integer, primary_key=True)
    vote = db.Column(
        db.Enum(VoteType, native_enum=False, length=20),
        nullable=False,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("authors.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=True,
    )
    response_id = db.Column(
        db.Integer,
        db.ForeignKey("responses.id", ondelete="CASCADE"),
        nullable=True,
    )

    user = db.relationship("Author", back_populates="votes")
    question = db.relationship("Question", back_populates="votes")
    response = db.relationship("Response", back_populates="votes")
