# app/model.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import db

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(Integer, primary_key=True, index=True)
    email = db.Column(String(120), unique=True, nullable=False)
    password = db.Column(String(128), nullable=False)

    def __repr__(self):
        return f"<Admin {self.email}>"

class Disinsector(db.Model):
    __tablename__ = 'disinsectors'
    id = db.Column(Integer, primary_key=True, index=True)
    name = db.Column(String(100), nullable=False)
    email = db.Column(String(120), unique=True, nullable=False)
    password = db.Column(String(128), nullable=False)
    token = db.Column(String(128), unique=True, nullable=False)
    telegram_user_id = db.Column(Integer, unique=True, nullable=True)

    orders = db.relationship('Order', back_populates='disinsector')

    def __repr__(self):
        return f'<Disinsector {self.name}>'

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(Integer, primary_key=True, index=True)
    name = db.Column(String(100), nullable=False)
    phone = db.Column(String(20), nullable=False)
    address = db.Column(String(200), nullable=False)

    orders = db.relationship("Order", back_populates="client")

    def __repr__(self):
        return f'<Client {self.name}>'

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(Integer, primary_key=True, index=True)
    disinsector_id = db.Column(Integer, ForeignKey('disinsectors.id'), nullable=True)
    client_id = db.Column(Integer, ForeignKey('clients.id'), nullable=False)
    order_status = db.Column(String(50), default='Новая')
    object_type = db.Column(String(50), nullable=False)
    insect_quantity = db.Column(String(50), nullable=False)
    disinsect_experience = db.Column(Boolean, nullable=False)
    estimated_price = db.Column(String(50), nullable=True)
    final_price = db.Column(String(50), nullable=True)
    poison_type = db.Column(String(100), nullable=True)
    insect_type = db.Column(String(100), nullable=True)
    client_area = db.Column(String(100), nullable=True)
    created_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    disinsector = db.relationship("Disinsector", back_populates="orders")
    client = db.relationship("Client", back_populates="orders")

    def __repr__(self):
        return f'<Order {self.id}>'
