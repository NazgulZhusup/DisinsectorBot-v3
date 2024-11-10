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

