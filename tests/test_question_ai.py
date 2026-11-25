from is1_trabajo_grupo26 import create_app
from is1_trabajo_grupo26.config import TestingConfig
from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.category import Category
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.models.tag import Tag


def _make_client():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        user = Author(
            name="Tester",
            email="tester@example.com",
            password="hashed-password",
            role=TipoRol.USERGRAL,
        )
        category = Category(name="Python")
        db.session.add_all([user, category])
        db.session.flush()

        q_with_tag = Question(
            title="Duda con Flask #ia-help",
            body="¿Cómo conecto un Blueprint?",
            author_id=user.id,
            category=category,
        )
        q_without_tag = Question(
            title="Duda normal",
            body="Sin etiqueta de IA",
            author_id=user.id,
            category=category,
        )
        db.session.add_all([q_with_tag, q_without_tag])
        db.session.commit()
        q1_id = q_with_tag.id
        q2_id = q_without_tag.id

    return app, app.test_client(), q1_id, q2_id


def test_generate_ai_answer_creates_bot_response():
    app, client, q1_id, _ = _make_client()

    res = client.post(
        f"/questions/{q1_id}/generate-ai",
        data={"provider": "local"},
        follow_redirects=False,
    )

    assert res.status_code == 302
    with app.app_context():
        responses = (
            db.session.execute(db.select(Response).where(Response.question_id == q1_id))
            .scalars()
            .all()
        )
        assert len(responses) == 1
        assert responses[0].author.role == TipoRol.BOT
        assert responses[0].author.name == "Local Bot"


def test_generate_ai_answer_requires_ia_help_tag():
    app, client, _, q2_id = _make_client()

    res = client.post(
        f"/questions/{q2_id}/generate-ai",
        data={"provider": "gemini"},
        follow_redirects=False,
    )

    assert res.status_code == 302
    with app.app_context():
        responses = (
            db.session.execute(db.select(Response).where(Response.question_id == q2_id))
            .scalars()
            .all()
        )
        assert len(responses) == 0


def test_generate_ai_answer_accepts_ia_help_tag_object():
    app, client, _, q2_id = _make_client()
    with app.app_context():
        question = db.session.get(Question, q2_id)
        question.tags.append(Tag(title="#ia-help"))
        db.session.commit()

    res = client.post(f"/questions/{q2_id}/generate-ai", data={"provider": "local"})

    assert res.status_code == 302
    with app.app_context():
        responses = (
            db.session.execute(db.select(Response).where(Response.question_id == q2_id))
            .scalars()
            .all()
        )
        assert len(responses) == 1


def test_question_detail_shows_category_tags_and_responses():
    app, client, q1_id, _ = _make_client()
    with app.app_context():
        question = db.session.get(Question, q1_id)
        question.tags.append(Tag(title="#ia-help"))
        responder = db.session.execute(db.select(Author)).scalars().all()[0]
        db.session.add(Response(body="Respuesta de prueba", question=question, author=responder))
        db.session.commit()

    response = client.get(f"/questions/{q1_id}")

    assert response.status_code == 200
    assert b"Duda con Flask" in response.data
    assert b"Python" in response.data
    assert b"#ia-help" in response.data
    assert b"Respuesta de prueba" in response.data
    assert b"Asistente IA" in response.data


def test_question_detail_returns_404_when_missing():
    _, client, _, _ = _make_client()

    response = client.get("/questions/9999")

    assert response.status_code == 404


def test_registered_user_can_publish_answer():
    app, client, q1_id, _ = _make_client()
    with app.app_context():
        user = db.session.execute(db.select(Author)).scalars().all()[0]
        user_id = user.id

    with client.session_transaction() as flask_session:
        flask_session["user_id"] = user_id

    response = client.post(
        f"/questions/{q1_id}/answers",
        data={"body": "Mi respuesta nueva"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Mi respuesta nueva" in response.data
