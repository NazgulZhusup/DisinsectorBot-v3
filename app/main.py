# app/main.py

from flask import Blueprint, render_template, redirect, url_for, session, flash, request, jsonify
from app import csrf
from app.model import Order, Client, Disinsector
from database import db
from sqlalchemy import func
from sqlalchemy.orm import joinedload
import requests
import logging

main_bp = Blueprint('main', __name__)
logger = logging.getLogger('main')
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('main.log')
stream_handler = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if 'admin_id' in session:
        status = request.args.get('status', 'Все')
        try:
            query = db.session.query(Order).options(
                joinedload(Order.client),
                joinedload(Order.disinsector)
            )
            if status != 'Все':
                query = query.filter_by(order_status=status)
            orders = query.all()
        except Exception as e:
            logger.error(f"Ошибка при получении заявок для админ-дэшборда: {e}")
            flash("Произошла ошибка при загрузке заявок.", 'danger')
            return redirect(url_for('main.index'))
        return render_template('admin_dashboard.html', orders=orders)
    else:
        flash("Пожалуйста, войдите как администратор.", 'warning')
        return redirect(url_for('auth.admin_login'))

@main_bp.route('/disinsector/dashboard')
def disinsector_dashboard():
    if 'disinsector_id' in session:
        disinsector_id = session['disinsector_id']
        try:
            disinsector = Disinsector.query.get(disinsector_id)
            if not disinsector:
                flash("Дезинсектор не найден.", 'danger')
                return redirect(url_for('auth.disinsector_login'))
            orders = Order.query.filter_by(disinsector_id=disinsector_id).all()
        except Exception as e:
            logger.error(f"Ошибка при загрузке дезинсектор-дэшборда: {e}")
            flash("Произошла ошибка при загрузке заявок.", 'danger')
            return redirect(url_for('main.index'))
        return render_template('disinsector_dashboard.html', disinsector=disinsector, orders=orders)
    else:
        flash("Пожалуйста, войдите как дезинсектор.", 'warning')
        return redirect(url_for('auth.disinsector_login'))

# Функция назначения заявки дезинсектору
def assign_order_to_disinsector(order, session_db):
    """
    Назначает заявку дезинсектору с наименьшим количеством текущих заказов.
    """
    try:
        disinsectors = session_db.query(
            Disinsector,
            func.count(Order.id).label('order_count')
        ).outerjoin(Order).filter(
            Order.order_status.in_(['Новая', 'В процессе'])
        ).group_by(Disinsector.id).order_by('order_count').all()

        if not disinsectors:
            logger.warning("Нет доступных дезинсекторам для назначения заявки.")
            return None

        assigned_disinsector = disinsectors[0][0]
        order.disinsector = assigned_disinsector
        order.order_status = 'В процессе'
        session_db.commit()

        logger.info(f"Заявка {order.id} назначена дезинсектору {assigned_disinsector.email}.")
        return assigned_disinsector
    except Exception as e:
        logger.error(f"Ошибка при назначении дезинсектора для заявки {order.id}: {e}")
        session_db.rollback()
        return None

@csrf.exempt
@main_bp.route('/api/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    client_name = data.get('client_name')
    object_type = data.get('object_type')
    insect_quantity = data.get('insect_quantity')
    disinsect_experience = data.get('disinsect_experience')
    phone_number = data.get('phone_number')
    address = data.get('address')

    if not all([client_name, object_type, insect_quantity, disinsect_experience, phone_number, address]):
        return jsonify({'error': 'Missing required fields'}), 400

    disinsect_experience_bool = True if str(disinsect_experience).lower() == 'yes' else False

    try:
        client = Client.query.filter_by(phone=phone_number).first()
        if not client:
            client = Client(name=client_name, phone=phone_number, address=address)
            db.session.add(client)
            db.session.commit()

        new_order = Order(
            client_id=client.id,
            object_type=object_type,
            insect_quantity=insect_quantity,
            disinsect_experience=disinsect_experience_bool,
            order_status='Новая'
        )
        db.session.add(new_order)
        db.session.commit()

        disinsector = assign_order_to_disinsector(new_order, db.session)

        if disinsector:
            db.session.refresh(new_order)

            message = (
                f"🔔 **Новая заявка №{new_order.id}** 🔔\n\n"
                f"**Клиент:** {client.name}\n"
                f"**Телефон:** {client.phone}\n"
                f"**Адрес:** {client.address}\n"
                f"**Объект:** {object_type}\n"
                f"**Количество насекомых:** {insect_quantity}\n"
                f"**Опыт дезинсекции:** {'Да' if disinsect_experience_bool else 'Нет'}\n\n"
                f"Перейдите в ваш бот для управления заявкой."
            )

            telegram_api_url = f"https://api.telegram.org/bot{disinsector.token}/sendMessage"
            payload = {
                'chat_id': disinsector.telegram_user_id,
                'text': message,
                'parse_mode': 'Markdown'
            }

            try:
                response = requests.post(telegram_api_url, data=payload)
                if response.status_code != 200:
                    logger.error(f"Не удалось отправить сообщение дезинсектору {disinsector.id}: {response.text}")
            except requests.RequestException as e:
                logger.error(f"Ошибка при отправке сообщения дезинсектору {disinsector.id}: {e}")
        else:
            logger.error(f"Не удалось назначить дезинсектора для заявки {new_order.id}.")

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error(f"Ошибка при создании заявки: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@main_bp.route('/update_order_status', methods=['POST'])
def update_order_status():
    if 'disinsector_id' in session:
        order_id = request.form.get('order_id')
        new_status = request.form.get('new_status')

        if not order_id or not new_status:
            flash("Неверные данные.", 'danger')
            return redirect(url_for('main.disinsector_dashboard'))

        try:
            disinsector = Disinsector.query.get(session['disinsector_id'])
            if not disinsector:
                flash("Дезинсектор не найден.", 'danger')
                return redirect(url_for('auth.disinsector_login'))

            order = Order.query.filter_by(id=order_id, disinsector_id=disinsector.id).first()
            if order:
                order.order_status = new_status
                db.session.commit()
                flash("Статус заявки обновлен.", 'success')
            else:
                flash("Заявка не найдена или у вас нет прав на её изменение.", 'danger')
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса заявки {order_id}: {e}")
            flash("Произошла ошибка при обновлении статуса заявки.", 'danger')

        return redirect(url_for('main.disinsector_dashboard'))
    else:
        flash("Неавторизованный доступ.", 'danger')
        return redirect(url_for('auth.disinsector_login'))

