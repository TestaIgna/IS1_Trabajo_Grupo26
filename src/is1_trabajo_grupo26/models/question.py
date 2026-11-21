from datetime import date

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.vote import calculate_vote_score

question_tag = db.Table(
    "question_tag",
    db.Column(
        "question_id",
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "tag_id",
        db.Integer,
        db.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Question(db.Model):
    """Pregunta publicada por un autor dentro de una categoría."""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("authors.id", ondelete="CASCADE"),
        nullable=False,
    )

    category = db.relationship("Category", back_populates="questions")
    author = db.relationship("Author", back_populates="questions")
    tags = db.relationship(
        "Tag",
        secondary=question_tag,
        back_populates="questions",
    )
    responses = db.relationship(
        "Response",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    votes = db.relationship(
        "Vote",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    def calculate_score(self) -> int:
        """Retorna la puntuación acumulada de la pregunta."""
        return calculate_vote_score(self.votes)
