# app/__init__.py

import logging
from logging.handlers import RotatingFileHandler
import os
from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from config import Config
from database import db

csrf = CSRFProtect()
migrate = Migrate()

# app/__init__.py

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    basedir = os.path.abspath(os.path.dirname(__file__))
    load_dotenv(os.path.join(basedir, '..', '.env'))

    # Инициализация расширений
    csrf.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)

    # Импорт моделей для обнаружения Flask-Migrate
    from app.model import Admin, Disinsector, Client, Order

    # Настройка логирования
    if not app.debug and not app.testing:
        # RotatingFileHandler для логов в файл
        file_handler = RotatingFileHandler(app.config['LOG_FILE'], maxBytes=10240, backupCount=10)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'
        )
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

        # StreamHandler для вывода логов в консоль
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('DisinsectorBot-v3 startup')

    # Регистрация Blueprint'ов
    with app.app_context():
        from app.api import api_bp
        from app.auth import auth_bp
        from app.main import main_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(api_bp, url_prefix='/api')

    return app


