from datetime import date

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.vote import calculate_vote_score


class Response(db.Model):
    """Respuesta publicada a una pregunta por un usuario o bot LLM."""

    __tablename__ = "responses"

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    is_accepted = db.Column(db.Boolean, nullable=False, default=False)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("authors.id", ondelete="CASCADE"),
        nullable=False,
    )

    question = db.relationship("Question", back_populates="responses")
    author = db.relationship("Author", back_populates="responses")
    votes = db.relationship(
        "Vote",
        back_populates="response",
        cascade="all, delete-orphan",
    )

    def calculate_score(self) -> int:
        """Retorna la puntuación acumulada de la respuesta."""
        return calculate_vote_score(self.votes)
