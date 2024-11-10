# init_db.py
from app import create_app
from database import db

app = create_app()

with app.app_context():
    db.create_all()
    print("База данных инициализирована.")

print("SQLALCHEMY_DATABASE_URI:", app.config['SQLALCHEMY_DATABASE_URI'])
