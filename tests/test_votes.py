import pytest

from is1_trabajo_grupo26 import create_app
from is1_trabajo_grupo26.config import TestingConfig
from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.category import Category
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.models.vote import VoteType
from is1_trabajo_grupo26.services.vote_service import register_vote


@pytest.fixture
def ctx():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        user = Author(
            name="Mile",
            email="mile@x.com",
            password="12345699",
            role=TipoRol.USERGRAL,
        )
        cat = Category(name="General")
        db.session.add_all([user, cat])
        db.session.flush()

        q = Question(
            title="Pregunta",
            body="Cuerpo",
            category_id=cat.id,
            author_id=user.id,
        )
        db.session.add(q)
        db.session.flush()

        r = Response(
            body="Respuesta",
            question_id=q.id,
            author_id=user.id,
        )
        db.session.add(r)
        db.session.commit()

        yield app, {"u": user.id, "q": q.id, "r": r.id}


def test_vote_question_positive_and_negative(ctx):
    _, ids = ctx
    v_pos = register_vote(ids["u"], "positive", question_id=ids["q"])
    assert v_pos.id is not None
    assert v_pos.vote == VoteType.POSITIVE
    assert v_pos.question_id == ids["q"]
    assert v_pos.response_id is None


def test_vote_response_negative(ctx):
    _, ids = ctx
    v_neg = register_vote(ids["u"], VoteType.NEGATIVE, response_id=ids["r"])
    assert v_neg.id is not None
    assert v_neg.vote == VoteType.NEGATIVE
    assert v_neg.response_id == ids["r"]
    assert v_neg.question_id is None


def test_duplicate_vote_on_question_rejected(ctx):
    _, ids = ctx
    register_vote(ids["u"], "POSITIVE", question_id=ids["q"])
    with pytest.raises(ValueError):
        register_vote(ids["u"], "NEGATIVE", question_id=ids["q"])


def test_duplicate_vote_on_response_rejected(ctx):
    _, ids = ctx
    register_vote(ids["u"], "POSITIVE", response_id=ids["r"])
    with pytest.raises(ValueError):
        register_vote(ids["u"], "NEGATIVE", response_id=ids["r"])


def test_xor_both_or_none_rejected(ctx):
    _, ids = ctx
    with pytest.raises(ValueError):
        register_vote(
            ids["u"],
            "POSITIVE",
            question_id=ids["q"],
            response_id=ids["r"],
        )
    with pytest.raises(ValueError):
        register_vote(ids["u"], "POSITIVE")


def test_invalid_vote_type_rejected(ctx):
    _, ids = ctx
    with pytest.raises(ValueError):
        register_vote(ids["u"], "INVALID", question_id=ids["q"])


def test_api_votes_create_and_reject_duplicate(ctx):
    app, ids = ctx
    client = app.test_client()
    payload = {
        "user_id": ids["u"],
        "vote": "POSITIVE",
        "question_id": ids["q"],
    }

    created = client.post("/api/votes", json=payload)
    assert created.status_code == 201
    data = created.get_json()
    assert data["vote"] == "POSITIVE"
    assert data["question_id"] == ids["q"]
    assert data["response_id"] is None

    duplicate = client.post("/api/votes", json=payload)
    assert duplicate.status_code in (400, 409)