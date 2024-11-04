# database.py

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import scoped_session, sessionmaker
from config import Config
from contextlib import contextmanager

db = SQLAlchemy()

SessionFactory = sessionmaker(bind=db.engine)
Session = scoped_session(SessionFactory)

@contextmanager
def get_session():
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
