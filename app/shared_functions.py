# app/shared_functions.py

from app.model import Disinsector, Order
from database import db
from datetime import datetime
from app.utils import send_telegram_message
import logging

logger = logging.getLogger('shared_functions')


def assign_and_notify_disinsector(order):
    """
    Назначает дезинсектора для заявки и отправляет ему уведомление.
    """
    try:
        available_disinsectors = Disinsector.query.filter(
            Disinsector.token.isnot(None),
            Disinsector.telegram_user_id.isnot(None),
            Disinsector.load < Disinsector.max_load
        ).order_by(Disinsector.last_assigned).all()

        if not available_disinsectors:
            logger.warning("Нет доступных дезинсекторов для назначения заявки.")
            return None

        # Назначение дезинсектора
        disinsector = available_disinsectors[0]
        order.disinsector_id = disinsector.id
        disinsector.last_assigned = datetime.utcnow()
        disinsector.load += 1
        db.session.commit()

        # Уведомление дезинсектора
        notify_new_order(disinsector, order)
        logger.info(f"Заявка {order.id} назначена дезинсектору {disinsector.name} (ID: {disinsector.id})")
        return disinsector

    except Exception as e:
        logger.error(f"Ошибка при назначении дезинсектора: {e}")
        db.session.rollback()
        return None


def notify_new_order(disinsector, order):
    """
    Отправляет уведомление дезинсектору о новой заявке.
    """
    try:
        message = (
            f"🔔 Новая заявка №{order.id}.\n"
            f"Адрес: {order.client.address}\n"
            f"Объект: {order.object_type}\n"
            "Согласны принять заявку?"
        )
        send_telegram_message(disinsector.token, disinsector.telegram_user_id, message)
        logger.info(f"Уведомление отправлено дезинсектору {disinsector.name}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления дезинсектору: {e}")
