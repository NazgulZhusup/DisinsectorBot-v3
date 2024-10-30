# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
import os

db = SQLAlchemy()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)

    # Определяем абсолютный путь к базе данных
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'entoforce_database.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Рекомендуется отключить

    csrf.init_app(app)
    db.init_app(app)

    # Регистрация Blueprints
    from app.auth import auth_bp
    from app.main import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
