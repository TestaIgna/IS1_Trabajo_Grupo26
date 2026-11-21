from is1_trabajo_grupo26.extensions import db


class Category(db.Model):
    """Categoría temática a la que pertenece cada pregunta."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    questions = db.relationship("Question", back_populates="category")
