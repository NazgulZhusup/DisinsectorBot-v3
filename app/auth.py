# api.py

from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import asc
from app.model import Order, Disinsector, Client
from app.shared_functions import get_next_disinsector, send_notification_to_disinsector_and_start_questions
from database import db
from app.utils import send_telegram_message
import logging


api_bp = Blueprint('api', __name__)
logger = logging.getLogger('api_bp')


def assign_order_to_disinsector(order):
    try:
        # Фильтрация дезинсекторов с токеном, telegram_user_id и нагрузкой меньше max_load
        available_disinsectors = Disinsector.query.filter(
            Disinsector.token.isnot(None),
            Disinsector.telegram_user_id.isnot(None),
            Disinsector.load < Disinsector.max_load
        ).order_by(Disinsector.last_assigned).all()

        if not available_disinsectors:
            # Логирование, если нет доступных дезинсекторов
            logger.warning("Нет доступных дезинсекторов для назначения заявки.")
            return None

        # Получаем первого доступного дезинсектора по очереди
        disinsector = available_disinsectors[0]

        # Назначаем заявку дезинсектору
        order.disinsector_id = disinsector.id
        disinsector.last_assigned = datetime.utcnow()
        disinsector.load += 1  # Увеличиваем загрузку дезинсектора
        db.session.commit()

        # Лог успешного назначения заявки
        logger.info(f"Заявка {order.id} назначена дезинсектору {disinsector.name} (ID: {disinsector.id})")

        # Отправляем уведомление дезинсектору
        message = f"🔔 Новая заявка №{order.id}. Адрес: {order.client.address}"
        send_telegram_message(disinsector.token, disinsector.telegram_user_id, message)

        return disinsector
    except Exception as e:
        logger.error(f"Ошибка при назначении заявки дезинсектору: {e}")
        db.session.rollback()  # Откат изменений в случае ошибки
        return None


@api_bp.route('/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['client_name', 'phone_number', 'address', 'object_type', 'insect_quantity']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400

    # Создаем клиента, если его нет
    client = Client.query.filter_by(phone=data['phone_number']).first()
    if not client:
        client = Client(name=data['client_name'], phone=data['phone_number'], address=data['address'])
        db.session.add(client)
        db.session.commit()

    # Создаем новый заказ
    new_order = Order(
        client_id=client.id,
        object_type=data['object_type'],
        insect_quantity=data['insect_quantity'],
        disinsect_experience=data.get('disinsect_experience', False),
        order_status='Новая'
    )
    db.session.add(new_order)
    db.session.commit()

    # Назначаем дезинсектора по очереди
    assigned_disinsector = get_next_disinsector()
    if assigned_disinsector:
        new_order.disinsector_id = assigned_disinsector.id
        db.session.commit()

        # Отправляем уведомление дезинсектору
        send_notification_to_disinsector_and_start_questions(assigned_disinsector, new_order)
        logger.info(f"Заявка {new_order.id} назначена дезинсектору {assigned_disinsector.name}")
    else:
        logger.warning("Нет доступных дезинсекторов для назначения заявки.")
        return jsonify({'error': 'No available disinsector'}), 400

    return jsonify({'message': 'Order created successfully', 'order_id': new_order.id}), 200