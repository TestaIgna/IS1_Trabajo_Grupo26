import os
from logging.config import fileConfig

from alembic import context

# Importar los módulos ORM asegura que queden registrados en db.metadata.
import is1_trabajo_grupo26.models.author_model
import is1_trabajo_grupo26.models.category
import is1_trabajo_grupo26.models.question
import is1_trabajo_grupo26.models.response
import is1_trabajo_grupo26.models.tag
import is1_trabajo_grupo26.models.vote  # noqa: F401
from is1_trabajo_grupo26 import create_app
from is1_trabajo_grupo26.extensions import db

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = db.metadata


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo offline (genera SQL sin conectar)."""
    url = os.getenv("DATABASE_URL", "sqlite:///app.db")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo online usando el engine de Flask."""
    app = create_app()
    with app.app_context():
        try:
            with db.engine.connect() as connection:
                context.configure(
                    connection=connection,
                    target_metadata=target_metadata,
                    render_as_batch=True,
                )

                with context.begin_transaction():
                    context.run_migrations()
        finally:
            db.engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
