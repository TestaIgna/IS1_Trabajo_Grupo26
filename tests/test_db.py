import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from is1_trabajo_grupo26.extensions import db


def test_testing_uses_in_memory_sqlite(app):
    assert app.config["TESTING"] is True
    assert str(db.engine.url) == "sqlite:///:memory:"


def test_sqlite_foreign_keys_enabled(db_session):
    assert db_session.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

    db_session.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
    db_session.execute(
        text(
            "CREATE TABLE child ("
            "id INTEGER PRIMARY KEY, "
            "parent_id INTEGER NOT NULL REFERENCES parent(id)"
            ")"
        )
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text("INSERT INTO child (id, parent_id) VALUES (1, 999)")
        )
        db_session.flush()

    db_session.rollback()


def test_db_session_rollback(db_session):
    db_session.execute(
        text("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    )
    db_session.commit()

    db_session.execute(text("INSERT INTO items (id, name) VALUES (1, 'uno')"))
    assert db_session.execute(text("SELECT COUNT(*) FROM items")).scalar_one() == 1

    db_session.rollback()
    assert db_session.execute(text("SELECT COUNT(*) FROM items")).scalar_one() == 0
