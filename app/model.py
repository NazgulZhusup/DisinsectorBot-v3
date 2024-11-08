from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import db

class Admin(db.Model):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(128), nullable=False)

    def __repr__(self):
        return f"<Admin {self.email}>"

class Disinsector(db.Model):
    __tablename__ = 'disinsectors'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    token = Column(String(128), unique=True, nullable=False)
    telegram_user_id = Column(Integer, unique=True, nullable=True)  # Уникальный идентификатор Telegram пользователя
    load = Column(Integer, default=0)  # Количество активных заявок
    max_load = Column(Integer, default=5)  # Максимальная загрузка
    last_assigned = Column(DateTime, default=datetime.utcnow)

    orders = relationship('Order', back_populates='disinsector')

    def __repr__(self):
        return f'<Disinsector {self.name}>'
class Client(db.Model):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(String(200), nullable=False)

    orders = relationship("Order", back_populates="client")

    def __repr__(self):
        return f'<Client {self.name}>'

class Order(db.Model):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    disinsector_id = Column(Integer, ForeignKey('disinsectors.id'), nullable=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    order_status = Column(String(50), default='Новая')
    object_type = Column(String(50), nullable=False)
    insect_quantity = Column(String(50), nullable=False)
    disinsect_experience = Column(Boolean, nullable=False)
    estimated_price = Column(String(50), nullable=True)
    final_price = Column(String(50), nullable=True)
    poison_type = Column(String(100), nullable=True)
    insect_type = Column(String(100), nullable=True)
    client_area = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    disinsector = relationship("Disinsector", back_populates="orders")
    client = relationship("Client", back_populates="orders")

    def __repr__(self):
        return f'<Order {self.id}>'
