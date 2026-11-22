from is1_trabajo_grupo26.extensions import db


class Tag(db.Model):
    """Etiqueta asociada a preguntas (incluye el tag '#ia-help' para bots)."""

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60), nullable=False, unique=True)

    questions = db.relationship(
        "Question",
        secondary="question_tag",
        back_populates="tags",
    )
