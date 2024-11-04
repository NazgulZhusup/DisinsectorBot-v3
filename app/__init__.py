# app/__init__.py

from flask import Flask
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
import logging
from config import Config

from database import db

csrf = CSRFProtect()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Инициализация расширений
    csrf.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)

    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    )

    # Регистрация Blueprint'ов
    from app.auth import auth_bp
    from app.main import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Не вызывайте db.create_all(), полагайтесь на миграции
    return app
