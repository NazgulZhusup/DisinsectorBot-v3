# config.py

import os

# Определяем базовую директорию проекта (директорию, где находится config.py)
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Абсолютный путь к базе данных
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'entoforce_database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your_secret_key'  # Замените на ваш реальный секретный ключ
    CLIENT_BOT_TOKEN = '7752853484:AAGqFKHqoY0JBSeJUB3Br4Ypg13PMxLNa4c'  # Ваш токен бота
