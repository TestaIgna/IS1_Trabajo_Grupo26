from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.category import Category
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.models.tag import Tag
from is1_trabajo_grupo26.models.vote import Vote, VoteType


def test_create_full_domain_relationships_and_scores(db_session):
    category = Category(name="Ingenieria de Software")
    tag_ia = Tag(title="#ia-help")
    tag_py = Tag(title="python")

    human = Author(
        name="Matias",
        role=TipoRol.USERGRAL,
        email="matias@example.com",
        password="super-secret-password",
    )
    voter = Author(
        name="Brisa",
        role=TipoRol.ADMIN,
        email="brisa@example.com",
        password="another-password",
    )
    bot = Author(name="GeminiBot", role=TipoRol.BOT)

    question = Question(
        title="Como configurar Alembic con SQLite",
        body="Necesito configurar render_as_batch y claves foraneas.",
        date=date(2026, 11, 21),
        category=category,
        author=human,
        tags=[tag_ia, tag_py],
    )
    human_response = Response(
        body="Activa PRAGMA foreign_keys=ON en el evento connect.",
        is_accepted=True,
        question=question,
        author=voter,
    )
    bot_response = Response(
        body="[IA] Usa render_as_batch=True en migrations/env.py.",
        is_accepted=False,
        question=question,
        author=bot,
    )

    db_session.add_all(
        [category, tag_ia, tag_py, human, voter, bot, question, human_response, bot_response]
    )
    db_session.flush()

    q_vote_up = Vote(vote=VoteType.POSITIVE, user=voter, question=question)
    q_vote_down = Vote(vote=VoteType.NEGATIVE, user=human, question=question)
    r_vote_up = Vote(vote=VoteType.POSITIVE, user=human, response=human_response)
    db_session.add_all([q_vote_up, q_vote_down, r_vote_up])
    db_session.commit()

    assert category.questions == [question]
    assert set(question.tags) == {tag_ia, tag_py}
    assert tag_ia.questions == [question]
    assert len(question.responses) == 2
    assert human_response.author is voter
    assert bot_response.author.get_role_type() is TipoRol.BOT
    assert question.calculate_score() == 0
    assert human_response.calculate_score() == 1
    assert bot_response.calculate_score() == 0


def test_question_and_tag_match_issue_33_llm_contract(db_session):
    category = Category(name="Bases de Datos")
    tag_ia = Tag(title="#ia-help")
    author = Author(
        name="Ale",
        email="ale@example.com",
        password="password123",
    )
    question = Question(
        title="Duda sobre ORM",
        body="Que diferencia hay entre flush y commit?",
        category=category,
        author=author,
        tags=[tag_ia],
    )
    db_session.add_all([category, tag_ia, author, question])
    db_session.commit()

    assert question.title == "Duda sobre ORM"
    assert question.body == "Que diferencia hay entre flush y commit?"
    assert len(question.tags) == 1
    assert question.tags[0].title == "#ia-help"
    assert any(tag.title.strip().lower() == "#ia-help" for tag in question.tags)


def test_author_password_hashing_with_werkzeug(db_session):
    human = Author(
        name="Ignacio",
        email="ignacio@example.com",
        password="secret",
    )
    bot = Author(name="LocalBot", role=TipoRol.BOT)
    db_session.add_all([human, bot])
    db_session.commit()

    assert human.password_hash is not None
    assert human.password_hash != "secret"
    assert human.check_password("secret") is True
    assert human.check_password("wrong") is False
    assert human.get_name() == "Ignacio"
    assert human.get_role_type() is TipoRol.USERGRAL

    with pytest.raises(AttributeError):
        _ = human.password

    with pytest.raises(ValueError, match="vacía"):
        human.set_password("")

    assert bot.password_hash is None
    assert bot.check_password("anything") is False


def test_not_null_unique_and_foreign_key_constraints(db_session):
    category = Category(name="Python")
    tag = Tag(title="flask")
    author = Author(
        name="Milena",
        email="milena@example.com",
        password="password123",
    )
    db_session.add_all([category, tag, author])
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.add(Category(name=None))
        db_session.flush()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.add(Category(name="Python"))
        db_session.flush()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.add(Tag(title="flask"))
        db_session.flush()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.add(
            Author(
                name="Duplicado",
                email="milena@example.com",
                password="other",
            )
        )
        db_session.flush()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.add(
            Question(
                title="FK invalida",
                body="No existe esa categoria",
                category_id=999,
                author_id=author.id,
            )
        )
        db_session.flush()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.add(Author(name="HumanoSinCredenciales", role=TipoRol.USERGRAL))
        db_session.flush()
    db_session.rollback()


def test_vote_xor_and_unique_constraints(db_session):
    category = Category(name="Arquitectura")
    user = Author(
        name="Votante",
        email="votante@example.com",
        password="secret",
    )
    q1 = Question(
        title="Pregunta 1",
        body="Detalle 1",
        category=category,
        author=user,
    )
    q2 = Question(
        title="Pregunta 2",
        body="Detalle 2",
        category=category,
        author=user,
    )
    r1 = Response(body="Respuesta 1", question=q1, author=user)
    r2 = Response(body="Respuesta 2", question=q2, author=user)
    db_session.add_all([category, user, q1, q2, r1, r2])
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.add(
            Vote(vote=VoteType.POSITIVE, user=user, question=q1, response=r1)
        )
        db_session.flush()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.add(Vote(vote=VoteType.NEGATIVE, user=user))
        db_session.flush()
    db_session.rollback()

    db_session.add_all(
        [
            Vote(vote=VoteType.POSITIVE, user=user, question=q1),
            Vote(vote=VoteType.NEGATIVE, user=user, question=q2),
            Vote(vote=VoteType.POSITIVE, user=user, response=r1),
            Vote(vote=VoteType.POSITIVE, user=user, response=r2),
        ]
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.add(Vote(vote=VoteType.NEGATIVE, user=user, question=q1))
        db_session.flush()
    db_session.rollback()

    with pytest.raises(IntegrityError):
        db_session.add(Vote(vote=VoteType.NEGATIVE, user=user, response=r1))
        db_session.flush()
    db_session.rollback()
