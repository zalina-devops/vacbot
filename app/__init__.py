# app\__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
import logging

logger = logging.getLogger(__name__)
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from app.models import Vacancy, BoardCard

    with app.app_context():
        db.create_all()
        logger.debug("✅ База данных инициализирована")

    from app.routes import main
    app.register_blueprint(main)

    return app