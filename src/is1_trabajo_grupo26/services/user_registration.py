import logging
import re

from flask import Blueprint, redirect, render_template, request, session
from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.services import AuthorConcreteFactory

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__, url_prefix="/users")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
EMAIL_DUPLICADO = "There is already a registered user with that email address"


class RegistrationError(Exception):
    pass


@users_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "GET":
        return render_template("users/registro.html", errors={})

    user_name = (request.form.get("nombre") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    errors: dict[str, str] = {}

    try:
        if not user_name:
            errors["nombre"] = "Name is required"
        if not email:
            errors["email"] = "Email is required"
        if not password:
            errors["password"] = "Password is required"

        if email:
            if not EMAIL_RE.fullmatch(email):
                errors["email"] = "Email is not valid"
            else:
                existing_user = db.session.execute(
                    db.select(Author).where(Author.email == email)
                ).scalar_one_or_none()
                if existing_user is not None:
                    errors["email"] = EMAIL_DUPLICADO

        if password and len(password) < MIN_PASSWORD_LENGTH:
            errors["password"] = f"password must have at least {MIN_PASSWORD_LENGTH} characters"

        if errors:
            return render_template(
                "users/registro.html",
                errors=errors,
                nombre=user_name,
                email=email,
            )

        factory = AuthorConcreteFactory()
        domain_user = factory.createAuthor(
            author_type="user",
            nombre=user_name,
            email=email,
            password=password,
        )

        db_user = Author(
            name=domain_user.get_nombre(),
            email=domain_user.email,
            password=password,
            role=TipoRol.USERGRAL,
        )
        db.session.add(db_user)
        db.session.commit()
        session["user_id"] = db_user.id

        logger.info("user created: %s", email)
        return redirect("/")

    except (RegistrationError, ValueError) as exc:
        logger.warning("Error de dominio en registro (%s): %s", email, exc)
        return render_template(
            "users/registro.html",
            errors={},
            error="No se pudo completar el registro. Verificá los datos.",
            nombre=user_name,
            email=email,
        )

    except IntegrityError:
        db.session.rollback()
        logger.warning("Email duplicado en base de datos (%s)", email)
        return render_template(
            "users/registro.html",
            errors={"email": EMAIL_DUPLICADO},
            nombre=user_name,
            email=email,
        )


@users_bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user", None)
    return redirect("/")