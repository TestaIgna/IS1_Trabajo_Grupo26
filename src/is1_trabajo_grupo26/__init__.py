from flask import Flask

from is1_trabajo_grupo26.config import Config
from is1_trabajo_grupo26.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)

    db.init_app(app)

    from is1_trabajo_grupo26.api.health import health_bp
    from is1_trabajo_grupo26.services.user_registration import users_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(users_bp)

    from is1_trabajo_grupo26.web.questions import questions_bp

    app.register_blueprint(questions_bp)

    from is1_trabajo_grupo26.api import register_api

    register_api(app)

    from is1_trabajo_grupo26.web.index import web_bp

    app.register_blueprint(web_bp)
    
    return app
