import re
from typing import Any

from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.api.errors import ConflictError, NotFoundError, ValidationError
from is1_trabajo_grupo26.api.validation import get_json_body, require_non_empty_string
from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import Role_Type
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.services import AuthorConcreteFactory

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

users_api_bp = Blueprint("users_api", __name__, url_prefix="/users")


def serialize_user(author: Author) -> dict[str, Any]:
    """Serializa un autor ORM sin exponer contraseñas ni hashes."""
    return {
        "id": author.id,
        "name": author.name,
        "email": author.email,
        "role": author.get_role_type().value,
    }


def _parse_role(raw_role: Any) -> Role_Type:
    if not isinstance(raw_role, str):
        raise ValidationError(
            "El campo 'role' debe ser una cadena de texto.",
            details={"role": "Valores permitidos: USERGRAL, ADMIN o BOT."},
        )
    try:
        return Role_Type.from_value(raw_role)
    except ValueError as exc:
        raise ValidationError(
            str(exc),
            details={"role": "Valores permitidos: USERGRAL, ADMIN o BOT."},
        ) from exc


def _validate_unique_email(email: str) -> None:
    existing = db.session.execute(
        db.select(Author).where(Author.email == email)
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("Ya existe un usuario registrado con ese email.")


@users_api_bp.get("", strict_slashes=False)
def list_users():
    """Lista los autores registrados con filtro opcional por rol."""
    stmt = db.select(Author).order_by(Author.id.asc())
    raw_role = request.args.get("role")
    if raw_role is not None:
        role_filter = _parse_role(raw_role)
        stmt = stmt.where(Author.role == role_filter)

    authors = db.session.execute(stmt).scalars().all()
    return {"users": [serialize_user(author) for author in authors]}


@users_api_bp.get("/<int:user_id>")
def get_user(user_id: int):
    """Obtiene un autor por su ID sin exponer credenciales."""
    author = db.session.get(Author, user_id)
    if author is None:
        raise NotFoundError("Usuario no encontrado.")
    return serialize_user(author)


@users_api_bp.post("", strict_slashes=False)
def create_user():
    """Crea un autor humano o BOT validando dominio, unicidad y seguridad."""
    data = get_json_body()
    name = require_non_empty_string(data, "name", max_length=120)
    raw_role = data.get("role")
    role = Role_Type.USERGRAL if raw_role is None else _parse_role(raw_role)

    factory = AuthorConcreteFactory()

    if role is Role_Type.BOT:
        email: str | None = None
        if data.get("email") is not None:
            email = require_non_empty_string(data, "email", max_length=255).lower()
            if not EMAIL_RE.fullmatch(email):
                raise ValidationError(
                    "El formato del email no es válido.",
                    details={"email": "Debe tener un formato de email válido."},
                )
            _validate_unique_email(email)

        try:
            domain_bot = factory.createAuthor(
                author_type="llm",
                nombre=name,
                rol=role,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        db_user = Author(
            name=domain_bot.getName(),
            role=domain_bot.getRoleType(),
            email=email,
        )
    else:
        email = require_non_empty_string(data, "email", max_length=255).lower()
        if not EMAIL_RE.fullmatch(email):
            raise ValidationError(
                "El formato del email no es válido.",
                details={"email": "Debe tener un formato de email válido."},
            )

        password = require_non_empty_string(data, "password")
        if len(password) < 8:
            raise ValidationError(
                "La contraseña debe tener al menos 8 caracteres.",
                details={"password": "Debe tener al menos 8 caracteres."},
            )

        _validate_unique_email(email)

        try:
            domain_user = factory.createAuthor(
                author_type="user",
                nombre=name,
                rol=role,
                email=email,
                password=password,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        db_user = Author(
            name=domain_user.getName(),
            email=domain_user.email,
            password=password,
            role=domain_user.getRoleType(),
        )

    db.session.add(db_user)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError("Ya existe un usuario registrado con ese email.") from exc

    return serialize_user(db_user), 201
