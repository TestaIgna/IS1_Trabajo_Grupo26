from werkzeug.security import check_password_hash, generate_password_hash

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol


class Author(db.Model):
    """Modelo persistente de autor (usuario humano o bot LLM)."""

    __tablename__ = "authors"
    __table_args__ = (
        db.CheckConstraint(
            "(role = 'BOT') OR (email IS NOT NULL AND password_hash IS NOT NULL)",
            name="ck_author_human_requires_credentials",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(
        db.Enum(TipoRol, native_enum=False, length=20),
        nullable=False,
        default=TipoRol.USERGRAL,
    )
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)

    questions = db.relationship(
        "Question",
        back_populates="author",
        cascade="all, delete-orphan",
    )
    responses = db.relationship(
        "Response",
        back_populates="author",
        cascade="all, delete-orphan",
    )
    votes = db.relationship(
        "Vote",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def password(self) -> str:
        """Impide leer la contraseña expuesta directamente."""
        raise AttributeError("password es un atributo de solo escritura.")

    @password.setter
    def password(self, raw_password: str) -> None:
        self.set_password(raw_password)

    def set_password(self, raw_password: str) -> None:
        """Valida y almacena el hash seguro de la contraseña con werkzeug.security."""
        if not isinstance(raw_password, str) or not raw_password:
            raise ValueError("La contraseña no puede estar vacía.")
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verifica si una contraseña coincide con el hash almacenado."""
        if not self.password_hash or not isinstance(raw_password, str):
            return False
        return check_password_hash(self.password_hash, raw_password)

    def get_name(self) -> str:
        """Retorna el nombre visible del autor."""
        return self.name

    def get_role_type(self) -> TipoRol:
        """Retorna el rol del autor normalizado como TipoRol."""
        return TipoRol.from_value(self.role)
