import pytest

import is1_trabajo_grupo26.models.author_model
import is1_trabajo_grupo26.models.category
import is1_trabajo_grupo26.models.question
import is1_trabajo_grupo26.models.response
import is1_trabajo_grupo26.models.tag
import is1_trabajo_grupo26.models.vote  # noqa: F401
from is1_trabajo_grupo26 import create_app
from is1_trabajo_grupo26.config import TestingConfig
from is1_trabajo_grupo26.extensions import db as _db


@pytest.fixture
def app():
    app = create_app(TestingConfig)

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.rollback()
        _db.session.remove()
        _db.drop_all()
        _db.engine.dispose()


@pytest.fixture
def db_session(app):
    yield _db.session
    _db.session.rollback()
    _db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()
