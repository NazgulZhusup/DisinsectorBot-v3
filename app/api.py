import asyncio

from flask import Blueprint, request, jsonify
from app.model import Order, Client
from app.shared_functions import assign_and_notify_disinsector, notify_new_order
from database import db
import logging

api_bp = Blueprint('api', __name__)
logger = logging.getLogger('api_bp')


@api_bp.route('/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Проверка на наличие необходимых данных
    required_fields = ['client_name', 'phone_number', 'address', 'object_type', 'insect_quantity']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400

    # Создание клиента, если его нет
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

    # Назначаем дезинсектора на заявку
    assigned_disinsector = assign_and_notify_disinsector(new_order)
    if assigned_disinsector:
        # Отправляем уведомление дезинсектору
        asyncio.create_task(notify_new_order(new_order.id))
        logger.info(f"Заявка {new_order.id} назначена дезинсектору {assigned_disinsector.name}")
    else:
        logger.warning("Нет доступных дезинсекторов для назначения заявки.")
        return jsonify({'error': 'No available disinsector'}), 400

    return jsonify({'message': 'Order created successfully', 'order_id': new_order.id}), 200

