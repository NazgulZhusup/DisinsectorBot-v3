# app/shared_functions.py

from app.model import Disinsector
from database import db
from datetime import datetime
from app.utils import send_telegram_message
import logging

logger = logging.getLogger('shared_functions')


def get_next_disinsector():
    try:
        # Получаем всех доступных дезинсекторов
        available_disinsectors = Disinsector.query.filter(
            Disinsector.token.isnot(None),
            Disinsector.telegram_user_id.isnot(None),
            Disinsector.load < Disinsector.max_load
        ).order_by(Disinsector.last_assigned).all()

        if not available_disinsectors:
            logger.warning("Нет доступных дезинсекторов.")
            return None

        # Возвращаем первого доступного дезинсектора
        next_disinsector = available_disinsectors[0]
        next_disinsector.last_assigned = datetime.utcnow()  # Обновляем метку времени для очередности
        db.session.commit()

        logger.info(f"Выбран дезинсектор с ID: {next_disinsector.id}")
        return next_disinsector
    except Exception as e:
        logger.error(f"Ошибка при выборе дезинсектора: {e}")
        db.session.rollback()
        return None


async def send_notification_to_disinsector_and_start_questions(disinsector, order):
    try:
        message = (
            f"🔔 Новая заявка №{order.id}.\n"
            f"Адрес: {order.client.address}\n"
            f"Объект: {order.object_type}\n"
            "Согласны принять заявку?"
        )
        send_telegram_message(disinsector.token, disinsector.telegram_user_id, message)
        logging.info(f"Уведомление отправлено дезинсектору {disinsector.name}")
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления: {e}")