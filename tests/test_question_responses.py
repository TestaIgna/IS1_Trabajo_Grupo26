import pytest

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.response import Response

pytest_plugins = ["test_response"]

def _detalle(client, question_id) -> str:
    response = client.get(f"/questions/{question_id}")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _login(client, user_id) -> None:
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def test_detail_list_existing_responses(client, datos):
    _, _, _, question_id = datos
    html = _detalle(client, question_id)
    assert "Respuesta de Usuario" in html
    assert "Respuesta de Bot" in html
    assert "Respuesta automática" in html


def test_publish_answer_appears_in_detail(client, datos):
    _, otro_user_id, _, question_id = datos
    _login(client, otro_user_id)

    response = client.post(
        f"/questions/{question_id}/answers",
        data={"body": "Mi respuesta desde el test"},
    )
    assert response.status_code == 302
    assert "Mi respuesta desde el test" in _detalle(client, question_id)


def test_accept_button_only_for_question_author(client, datos):
    autor_pregunta_id, otro_user_id, _, question_id = datos

    _login(client, otro_user_id)
    assert "Aceptar respuesta" not in _detalle(client, question_id)

    _login(client, autor_pregunta_id)
    assert "Aceptar respuesta" in _detalle(client, question_id)


def test_accepted_answer_is_marked_in_detail(app, client, datos):
    autor_pregunta_id, otro_user_id, _, question_id = datos
    with app.app_context():
        rta = Response(
            body="Para aceptar",
            question_id=question_id,
            author_id=otro_user_id,
        )
        db.session.add(rta)
        db.session.commit()
        rta_id = rta.id

    _login(client, autor_pregunta_id)
    client.post(f"/questions/answers/{rta_id}/accept")

    html = _detalle(client, question_id)
    assert "Respuesta aceptada" in html
    assert "Quitar aceptación" in html