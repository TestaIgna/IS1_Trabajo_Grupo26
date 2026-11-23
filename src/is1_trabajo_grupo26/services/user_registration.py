import re
import logging

from flask import Blueprint, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.services import AuthorConcreteFactory

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__, url_prefix="/users")

#users_store = {}

EMAIL_RE= re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class RegistrationError(Exception): pass

@users_bp.route("/registro", methods = ["GET","POST"])
def registro():

    if request.method == "GET":
     return render_template("users/registro.html")


    #Validacion de campos obligatorios
    user_name = (request.form.get("nombre") or "").strip()
    email = (request.form.get("email") or "" ).strip().lower()
    password = request.form.get("password") or ""

    try:
        if not user_name or not email or not password:
         raise RegistrationError("All fields are required")
    
        #Validacion de email, que su formato sea valido
        if not EMAIL_RE.fullmatch(email):
         raise RegistrationError("Email is not valid")

        #Validacion de contraseña minima
        if len(password) < 8:
         raise RegistrationError("password must have at least 8 characters")

        #Validacion de email unico en la base de datos
        existing_user = db.session.execute(
            db.select(Author).where(Author.email == email)
            ).scalar_one_or_none()
        if existing_user is not None:
         raise RegistrationError("There is already a registered user with that email address")

        #Validacion de reglas de dominio mediante la Factory
        factory = AuthorConcreteFactory()
        domain_user = factory.createAuthor(
            author_type = "user",
            nombre = user_name,
            email = email,
            password = password
        )

        #Persistencia en SQLite (Author hashea password automaticamente)
        db_user = Author(
            name = domain_user.get_nombre(),
            email = domain_user.email,
            password = password,
            role = TipoRol.USERGRAL
        )
        db.session.add(db_user)
        db.session.commit

        logger.info("user created: %s", email)
        #Se registro al usuario correctamente
        return redirect("/") #Temporal hasta que este la ruta users.login return redirect(url_for("users.login"))

    except RegistrationError as exc:
        logger.warning("Error en registro (%s): %s", email, exc)
        return render_template(
            "users/registro.html",
            error=str(exc),
            nombre = user_name,
            email = email
        )

    except IntegrityError:
        db.session.rollback()
        logger.warning("Email duplicado en base de datos(%s)", email)
        return render_template(
            "users/registro.html",
            error = "There is already a registered user with that email address",
            nombre = user_name,
            email = email
        )

@users_bp.route("/logout")
def logout():
 session.pop("user", None)
 return redirect("/")


