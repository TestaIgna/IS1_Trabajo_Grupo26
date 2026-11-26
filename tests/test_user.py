import pytest

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author


def test_registro_user_valido(client):
    response = client.post(
        "/users/registro",
        data={
            "nombre": "Bruno Diaz",
            "email": "bruno@ejemplo.com",
            "password": "password123",
        },
    )

    assert response.status_code == 302


def test_registro_password_corta(client):
    response = client.post(
        "/users/registro",
        data={
            "nombre": "Matias Lopez",
            "email": "matilopez@gmail.com",
            "password": "123",
        },
    )
    assert response.status_code == 200
    assert "8" in response.get_data(as_text=True)


def test_registro_campos_vacios(client):
    response = client.post(
        "/users/registro",
        data={
            "nombre": "",
            "email": "",
            "password": "",
        },
    )

    assert response.status_code == 200
    assert "required" in response.get_data(as_text=True)


def test_registro_email_invalid(client):
    response = client.post(
        "/users/registro",
        data={
            "nombre": "Ana Ruiz",
            "email": "ana@gmail",
            "password": "pswrd347",
        },
    )

    assert response.status_code == 200
    assert "not valid" in response.get_data(as_text=True)


def test_registro_email_dup(client):
    payload = {
        "nombre": "Juan Perez",
        "email": "duplicado@ejemplo.com",
        "password": "passwrd487",
    }

    response_1 = client.post("/users/registro", data=payload)
    assert response_1.status_code == 302

    response_2 = client.post(
        "/users/registro",
        data={
            "nombre": "Diaz Gutierrez",
            "email": "duplicado@ejemplo.com",
            "password": "password764",
        },
    )

    assert response_2.status_code == 200
    assert "already" in response_2.get_data(as_text=True)


def test_login_get_muestra_formulario(client):
    response = client.get("/users/login")
    assert response.status_code == 200
    assert "Iniciar sesión" in response.get_data(as_text=True)


def test_login_valido(client):
    client.post(
        "/users/registro",
        data={
            "nombre": "Carla Gomez",
            "email": "carla@ejemplo.com",
            "password": "password123",
        },
    )
    client.get("/users/logout")

    response = client.post(
        "/users/login",
        data={
            "email": "carla@ejemplo.com",
            "password": "password123",
        },
    )

    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" in sess


def test_login_campos_vacios(client):
    response = client.post(
        "/users/login",
        data={
            "email": "",
            "password": "",
        },
    )

    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "El email es obligatorio." in html
    assert "La contraseña es obligatoria." in html


def test_login_credenciales_incorrectas(client):
    client.post(
        "/users/registro",
        data={
            "nombre": "Lucas Pereyra",
            "email": "lucas@ejemplo.com",
            "password": "password123",
        },
    )
    client.get("/users/logout")

    response = client.post(
        "/users/login",
        data={
            "email": "lucas@ejemplo.com",
            "password": "clave_equivocada",
        },
    )

    assert response.status_code == 401
    assert "Email o contraseña incorrectos." in response.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_login_bot_no_permitido(app, client):
    with app.app_context():
        bot = Author(
            name="Bot IA",
            email="bot_login@ejemplo.com",
            password="password123",
            role=TipoRol.BOT,
        )
        db.session.add(bot)
        db.session.commit()

    response = client.post(
        "/users/login",
        data={
            "email": "bot_login@ejemplo.com",
            "password": "password123",
        },
    )

    assert response.status_code == 401
    assert "Email o contraseña incorrectos." in response.get_data(as_text=True)


def test_logout_limpia_sesion(client):
    client.post(
        "/users/registro",
        data={
            "nombre": "Elena Silva",
            "email": "elena@ejemplo.com",
            "password": "password123",
        },
    )

    response = client.get("/users/logout")
    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" not in sess