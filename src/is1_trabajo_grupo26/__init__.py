from flask import Flask

from is1_trabajo_grupo26.config import Config
from is1_trabajo_grupo26.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)

    db.init_app(app)

    from is1_trabajo_grupo26.api.health import health_bp

    app.register_blueprint(health_bp)

    from is1_trabajo_grupo26.web.questions import questions_bp

    app.register_blueprint(questions_bp)
    
    return app
