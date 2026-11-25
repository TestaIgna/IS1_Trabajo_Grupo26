from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.category import Category
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.models.tag import Tag


def _seed_web_context(app):
    with app.app_context():
        user = Author(
            name="Matías",
            email="matias@example.com",
            password="password123",
            role=TipoRol.USERGRAL,
        )
        cat_py = Category(name="Python")
        cat_db = Category(name="Bases de Datos")
        existing_tag = Tag(title="backend")
        db.session.add_all([user, cat_py, cat_db, existing_tag])
        db.session.commit()
        return user.id, cat_py.id, cat_db.id


def _login_session(client, user_id: int) -> None:
    with client.session_transaction() as flask_session:
        flask_session["user_id"] = user_id


def test_create_question_requires_authenticated_session(client):
    resp = client.get("/questions/nueva", follow_redirects=False)
    assert resp.status_code == 302
    assert "/registro" in resp.location


def test_create_question_get_renders_categories_ia_help_and_recommended_tags(app, client):
    user_id, cat_py_id, cat_db_id = _seed_web_context(app)
    _login_session(client, user_id)

    resp_default = client.get("/questions/nueva")
    assert resp_default.status_code == 200
    html_default = resp_default.data.decode("utf-8")
    assert "Python" in html_default
    assert "Bases de Datos" in html_default
    assert "#ia-help" in html_default
    assert "backend" in html_default

    resp_db = client.get(f"/questions/nueva?category_id={cat_db_id}")
    assert resp_db.status_code == 200
    html_db = resp_db.data.decode("utf-8")
    assert "sqlite" in html_db
    assert "alembic" in html_db

    resp_py = client.get(f"/questions/nueva?category_id={cat_py_id}")
    assert resp_py.status_code == 200
    assert "flask" in resp_py.data.decode("utf-8")


def test_create_question_post_shows_field_errors_for_missing_fields(app, client):
    user_id, _, _ = _seed_web_context(app)
    _login_session(client, user_id)

    resp = client.post(
        "/questions/nueva",
        data={"title": "   ", "body": "", "category_id": ""},
    )
    assert resp.status_code == 400
    html = resp.data.decode("utf-8")
    assert "El título es obligatorio." in html
    assert "La consulta es obligatoria." in html
    assert "Debés seleccionar una categoría válida." in html

    with app.app_context():
        assert db.session.execute(db.select(Question)).scalars().all() == []


def test_create_question_post_rejects_title_over_200_chars_and_preserves_inputs(app, client):
    user_id, cat_py_id, _ = _seed_web_context(app)
    _login_session(client, user_id)

    resp = client.post(
        "/questions/nueva",
        data={
            "title": "x" * 201,
            "body": "Texto de consulta preservado",
            "category_id": str(cat_py_id),
            "selected_tags": ["#ia-help", "flask"],
            "tags": "custom-tag",
        },
    )
    assert resp.status_code == 400
    html = resp.data.decode("utf-8")
    assert "El título no puede superar los 200 caracteres." in html
    assert "Texto de consulta preservado" in html
    assert "custom-tag" in html
    assert f'value="{cat_py_id}" selected' in html

    with app.app_context():
        assert db.session.execute(db.select(Question)).scalars().all() == []


def test_create_question_post_rejects_tags_over_20_chars_without_creating_question_or_tags(
    app,
    client,
):
    user_id, cat_py_id, _ = _seed_web_context(app)
    _login_session(client, user_id)

    resp_free_tag = client.post(
        "/questions/nueva",
        data={
            "title": "Pregunta válida",
            "body": "Consulta válida",
            "category_id": str(cat_py_id),
            "tags": "valida, " + ("a" * 21),
        },
    )
    assert resp_free_tag.status_code == 400
    assert "Las etiquetas no pueden superar los 20 caracteres" in resp_free_tag.data.decode(
        "utf-8"
    )

    resp_selected_tag = client.post(
        "/questions/nueva",
        data={
            "title": "Pregunta válida",
            "body": "Consulta válida",
            "category_id": str(cat_py_id),
            "selected_tags": ["b" * 21],
        },
    )
    assert resp_selected_tag.status_code == 400
    assert (
        "Las etiquetas no pueden superar los 20 caracteres"
        in resp_selected_tag.data.decode("utf-8")
    )

    with app.app_context():
        assert db.session.execute(db.select(Question)).scalars().all() == []
        tag_titles = [t.title for t in db.session.execute(db.select(Tag)).scalars().all()]
        assert tag_titles == ["backend"]


def test_create_question_post_rejects_invalid_category(app, client):
    user_id, _, _ = _seed_web_context(app)
    _login_session(client, user_id)

    resp = client.post(
        "/questions/nueva",
        data={
            "title": "Pregunta válida",
            "body": "Consulta válida",
            "category_id": "9999",
        },
    )
    assert resp.status_code == 400
    assert "Debés seleccionar una categoría válida." in resp.data.decode("utf-8")

    with app.app_context():
        assert db.session.execute(db.select(Question)).scalars().all() == []


def test_create_question_post_accepts_boundary_lengths_and_selected_tags_with_ia_help(
    app,
    client,
):
    user_id, cat_py_id, _ = _seed_web_context(app)
    _login_session(client, user_id)

    exact_title = "T" * 200
    exact_tag = "e" * 20

    resp = client.post(
        "/questions/nueva",
        data={
            "title": exact_title,
            "body": "Consulta con longitud límite y etiquetas seleccionadas.",
            "category_id": str(cat_py_id),
            "selected_tags": ["#ia-help", "flask"],
            "tags": f"FLASK, {exact_tag}",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/questions/" in resp.location

    with app.app_context():
        questions = db.session.execute(db.select(Question)).scalars().all()
        assert len(questions) == 1
        created = questions[0]
        assert created.title == exact_title
        assert [t.title for t in created.tags] == ["#ia-help", "flask", exact_tag]

    detail_resp = client.get(resp.location)
    assert detail_resp.status_code == 200
    detail_html = detail_resp.data.decode("utf-8")
    assert "#ia-help" in detail_html
    assert "Asistente IA" in detail_html


def test_vote_answer_positive_negative_duplicate_and_auth(app, client):
    user1_id, cat_py_id, _ = _seed_web_context(app)
    with app.app_context():
        user2 = Author(
            name="Ignacio",
            email="ignacio@example.com",
            password="password123",
            role=TipoRol.USERGRAL,
        )
        db.session.add(user2)
        db.session.flush()
        user2_id = user2.id

        question = Question(
            title="Pregunta para votar respuesta",
            body="Detalle",
            category_id=cat_py_id,
            author_id=user1_id,
        )
        answer = Response(
            body="Respuesta votable",
            question=question,
            author_id=user2_id,
        )
        db.session.add_all([question, answer])
        db.session.commit()
        question_id = question.id
        answer_id = answer.id

    detail = client.get(f"/questions/{question_id}")
    assert detail.status_code == 200
    assert f'/questions/answers/{answer_id}/vote' in detail.data.decode("utf-8")

    unauth = client.post(
        f"/questions/answers/{answer_id}/vote",
        data={"vote": "POSITIVE"},
        follow_redirects=False,
    )
    assert unauth.status_code == 302
    assert "/registro" in unauth.location

    _login_session(client, user1_id)
    up_resp = client.post(
        f"/questions/answers/{answer_id}/vote",
        data={"vote": "POSITIVE"},
        follow_redirects=False,
    )
    assert up_resp.status_code == 302
    assert f"/questions/{question_id}" in up_resp.location

    with app.app_context():
        assert db.session.get(Response, answer_id).calculate_score() == 1

    dup_resp = client.post(
        f"/questions/answers/{answer_id}/vote",
        data={"vote": "NEGATIVE"},
        follow_redirects=True,
    )
    assert dup_resp.status_code == 200
    assert "El usuario ya emitió un voto" in dup_resp.data.decode("utf-8")
    with app.app_context():
        assert db.session.get(Response, answer_id).calculate_score() == 1

    _login_session(client, user2_id)
    invalid_resp = client.post(
        f"/questions/answers/{answer_id}/vote",
        data={"vote": "INVALID"},
        follow_redirects=True,
    )
    assert invalid_resp.status_code == 200
    assert "El voto seleccionado no es válido." in invalid_resp.data.decode("utf-8")

    down_resp = client.post(
        f"/questions/answers/{answer_id}/vote",
        data={"vote": "NEGATIVE"},
        follow_redirects=False,
    )
    assert down_resp.status_code == 302
    with app.app_context():
        assert db.session.get(Response, answer_id).calculate_score() == 0

    missing_resp = client.post(
        "/questions/answers/9999/vote",
        data={"vote": "POSITIVE"},
    )
    assert missing_resp.status_code == 404
