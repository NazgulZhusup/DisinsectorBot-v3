from app import db
from datetime import datetime

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

class Disinsector(db.Model):
    __tablename__ = 'disinsectors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    token = db.Column(db.String(200), unique=True, nullable=False)
    user_id = db.Column(db.Integer, nullable=True)  # Telegram user ID

    # Связь с заказами
    orders = db.relationship('Order', backref='disinsector', lazy=True)

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)

    # Связь с заказами
    orders = db.relationship('Order', backref='client', lazy=True)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    disinsector_id = db.Column(db.Integer, db.ForeignKey('disinsectors.id'), nullable=True)
    order_status = db.Column(db.String(50), default='Новая')
    object_type = db.Column(db.String(50), nullable=False)
    insect_quantity = db.Column(db.String(50), nullable=False)
    disinsect_experience = db.Column(db.Boolean, nullable=False)
    estimated_price = db.Column(db.Float, nullable=True)
    final_price = db.Column(db.Float, nullable=True)
    poison_type = db.Column(db.String(100), nullable=True)
    insect_type = db.Column(db.String(100), nullable=True)
    client_area = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
