import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'supersecretkey')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///disinsect_control.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

TOKEN = '7752853484:AAGqFKHqoY0JBSeJUB3Br4Ypg13PMxLNa4c'