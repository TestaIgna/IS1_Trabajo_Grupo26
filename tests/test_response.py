from datetime import date
import pytest
from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.extensions import db
from is1_trabajo_grupo26.models.author import TipoRol
from is1_trabajo_grupo26.models.author_model import Author
from is1_trabajo_grupo26.models.category import Category
from is1_trabajo_grupo26.models.question import Question
from is1_trabajo_grupo26.models.response import Response
from is1_trabajo_grupo26.models.vote import Vote, VoteType


@pytest.fixture
def datos(app):
    """Usuario autor de la pregunta, otro usuario, un Bot y una Question."""
    with app.app_context():
        autor_pregunta = Author(
            name="Sofia Ramos",
            email="maeil@ejemplo.com",
            password="contraseña789",
        )

        otro_user = Author(
            name="Juan Ruiz",
            email="JR@example.com",
            password="password783",
        )

        bot = Author(
            name="Bot Helper",
            email="bot@example.com",
            password="hashed-password",
            role=TipoRol.BOT,
        )

        category = Category(name="testing")
        db.session.add_all([autor_pregunta, otro_user, bot, category])
        db.session.flush()

        question = Question(
            title="¿Como pruebo el Response?",
            body="Quiero poder verificar valores por defecto",
            author_id=autor_pregunta.id,
            category=category,
        )
        db.session.add(question)
        db.session.flush()

        rta_user = Response(
            body="Respuesta de Usuario",
            question_id=question.id,
            author_id=autor_pregunta.id,
        )

        rta_bot = Response(
            body="Respuesta de Bot",
            question_id=question.id,
            author_id=bot.id,
        )
        db.session.add_all([rta_user, rta_bot])
        db.session.commit()
        return autor_pregunta.id, otro_user.id, bot.id, question.id


# Respuesta asociada a una Question y Author (USERGRAL y BOT)
def test_create_response_for_usergral_and_bot(app, datos):
    autor_pregunta_id, otro_user_id, bot_id, question_id = datos
    with app.app_context():
        rta_user = Response(
            body="Usa fixtures de pytest",
            question_id=question_id,
            author_id=otro_user_id,
        )

        rta_bot = Response(
            body="Podes usar una base en memoria",
            question_id=question_id,
            author_id=bot_id,
        )
        db.session.add_all([rta_user, rta_bot])
        db.session.commit()

        assert rta_user.author.role == TipoRol.USERGRAL
        assert rta_user.date == date.today()
        assert rta_user.is_accepted is False

        assert rta_bot.author.id == bot_id
        assert rta_bot.author.role == TipoRol.BOT
        assert rta_bot.date == date.today()
        assert rta_bot.is_accepted is False


# Valida que no se puede guardar una respuesta sin cuerpo, sin autor o sin pregunta
def test_response_requieres_question_and_author_and_body(app, datos):
    _, otro_user_id, _, question_id = datos
    with app.app_context():
        with pytest.raises(IntegrityError):
            db.session.add(Response(body="Sin autor", question_id=question_id))
            db.session.flush()
        db.session.rollback()

        with pytest.raises(IntegrityError):
            db.session.add(Response(body="Sin pregunta", author_id=otro_user_id))
            db.session.flush()
        db.session.rollback()

        with pytest.raises(IntegrityError):
            db.session.add(
                Response(body=None, question_id=question_id, author_id=otro_user_id)
            )
            db.session.flush()
        db.session.rollback()


# Calcula el puntaje de una respuesta
def test_calculate_score(app, datos):
    _, otro_user_id, bot_id, question_id = datos
    with app.app_context():
        voter1 = Author(
            name="Florencia Torres",
            email="TorresFlor@gmail.com",
            password="contraseña222",
        )

        voter2 = Author(
            name="Delfina Ruiz",
            email="RDejemplo@gmail.com",
            password="pswrd789",
        )

        rta = Response(
            body="Respuesta para probar el puntaje en especifico",
            question_id=question_id,
            author_id=otro_user_id,
        )

        rta_gral = Response(
            body="Respuesta para caso general",
            question_id=question_id,
            author_id=bot_id,
        )
        db.session.add_all([voter1, voter2, rta, rta_gral])
        db.session.flush()

        # Caso voto positivo
        voto_posit = Vote(
            user_id=voter1.id,
            response_id=rta.id,
            vote=VoteType.POSITIVE,
        )
        db.session.add(voto_posit)
        db.session.flush()
        assert rta.calculate_score() == 1

        # Caso voto negativo
        voto_neg = Vote(
            user_id=voter2.id,
            response_id=rta.id,
            vote=VoteType.NEGATIVE,
        )
        db.session.add(voto_neg)
        db.session.flush()
        db.session.refresh(rta)
        assert rta.calculate_score() == 0

        # Caso general
        voto1 = Vote(
            user_id=voter1.id,
            response_id=rta_gral.id,
            vote=VoteType.POSITIVE,
        )
        voto2 = Vote(
            user_id=voter2.id,
            response_id=rta_gral.id,
            vote=VoteType.NEGATIVE,
        )
        db.session.add_all([voto1, voto2])
        db.session.commit()
        assert rta_gral.calculate_score() == 0


# Respuesta vinculada a una pregunta
def test_response_belongs_to_one_question(app, datos):
    _, otro_user_id, _, question_id = datos
    with app.app_context():
        question = db.session.get(Question, question_id)
        rta = Response(
            body="Una respuesta",
            question_id=question_id,
            author_id=otro_user_id,
        )
        db.session.add(rta)
        db.session.commit()

        assert rta.question is question
        assert rta in question.responses


# Solo el autor de la pregunta puede marcarla como aceptada
def test_question_author_can_accept_response(app, client, datos):
    autor_pregunta_id, otro_user_id, _, question_id = datos
    with app.app_context():
        rta = Response(
            body="Una respuesta",
            question_id=question_id,
            author_id=otro_user_id,
        )
        db.session.add(rta)
        db.session.commit()
        rta_id = rta.id

    with client.session_transaction() as sess:
        sess["user_id"] = autor_pregunta_id

    response = client.post(f"/questions/answers/{rta_id}/accept")
    assert response.status_code == 302

    with app.app_context():
        rta_db = db.session.get(Response, rta_id)
        assert rta_db.is_accepted is True


# Otro usuario NO PUEDE marcarla como aceptada
def test_other_user_cannot_accept_response(app, client, datos):
    _, otro_user_id, bot_id, question_id = datos
    with app.app_context():
        rta = Response(
            body="Una respuesta",
            question_id=question_id,
            author_id=bot_id,
        )
        db.session.add(rta)
        db.session.commit()
        rta_id = rta.id

    with client.session_transaction() as sess:
        sess["user_id"] = otro_user_id

    response = client.post(f"/questions/answers/{rta_id}/accept")
    assert response.status_code in (302, 403)

    with app.app_context():
        rta_db = db.session.get(Response, rta_id)
        assert rta_db.is_accepted is False