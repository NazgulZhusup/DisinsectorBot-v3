# config.py

import os
from pathlib import Path
from dotenv import load_dotenv

basedir = Path(__file__).parent
load_dotenv(dotenv_path=basedir / '.env')

class Config:

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + str(basedir / 'entoforce_database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')  # Используйте переменные окружения для безопасности
    CLIENT_BOT_TOKEN = os.getenv('CLIENT_BOT_TOKEN', 'YOUR_CLIENT_BOT_TOKEN_HERE')
    API_KEY = os.getenv('API_KEY', 'your_default_api_key')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')

