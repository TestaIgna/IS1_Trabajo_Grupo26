import os


class Config:
    """Configuración base de la aplicación.

    Lee los valores desde variables de entorno para no hardcodear credenciales
    ni acoplar el proyecto a un motor de base de datos específico.
    """

    # Clave secreta que usa Flask para firmar sesiones y cookies.
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-key")

    # URL de conexión para SQLAlchemy.
    # En local usa SQLite por defecto; en otro entorno basta con definir
    # DATABASE_URL (por ejemplo, una conexión a PostgreSQL).
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///app.db")

    # Desactiva el seguimiento de modificaciones de Flask-SQLAlchemy
    # (evita consumo innecesario de memoria).
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestingConfig(Config):
    """Configuración aislada para ejecutar los tests con pytest.

    Usa SQLite en memoria RAM para no modificar la base local (app.db)
    y garantizar que cada test comience limpio.
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
