# app/auth.py

from flask import Blueprint, render_template, redirect, url_for, session, flash, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.model import Admin, Disinsector
from app import db
from sqlalchemy.exc import IntegrityError
from app.forms import RegisterDisinsectorForm, RegisterAdminForm, LoginAdminForm
from app.utils import send_telegram_message
import requests

auth_bp = Blueprint('auth', __name__)

# Регистрация администратора
@auth_bp.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    form = RegisterAdminForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        confirm_password = form.confirm_password.data

        current_app.logger.info(f"Попытка регистрации администратора с email: {email}")

        # Проверка, совпадают ли пароли (дополнительная проверка, хотя EqualTo уже это делает)
        if password != confirm_password:
            flash('Пароли не совпадают.', 'danger')
            current_app.logger.warning(f"Пароли не совпадают для email: {email}")
            return redirect(url_for('auth.admin_register'))

        hashed_password = generate_password_hash(password)

        new_admin = Admin(email=email, password=hashed_password)

        try:
            db.session.add(new_admin)
            db.session.commit()
            flash('Администратор успешно зарегистрирован!', 'success')
            current_app.logger.info(f"Администратор с email {email} успешно зарегистрирован.")
            return redirect(url_for('auth.admin_login'))
        except IntegrityError:
            db.session.rollback()
            flash('Администратор с таким email уже существует.', 'danger')
            current_app.logger.error(f"Администратор с email {email} уже существует.")
            return redirect(url_for('auth.admin_register'))
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при регистрации.', 'danger')
            current_app.logger.error(f"Ошибка при регистрации администратора: {e}")
            return redirect(url_for('auth.admin_register'))

    return render_template('admin_register.html', form=form)

# Вход для администратора
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LoginAdminForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data

        try:
            admin = Admin.query.filter_by(email=email).first()
            if admin and check_password_hash(admin.password, password):
                session['admin_id'] = admin.id  # Используем 'admin_id' для администраторов
                current_app.logger.info(f"Admin {admin.email} вошел в систему.")
                return redirect(url_for('main.admin_dashboard'))
            else:
                current_app.logger.warning(f"Неудачная попытка входа для email: {email}")
                flash("Неверный email или пароль.", 'danger')
        except Exception as e:
            current_app.logger.error(f"Ошибка при входе админа: {e}")
            flash("Произошла ошибка. Пожалуйста, попробуйте позже.", 'danger')
    return render_template('admin_login.html', form=form)

# Регистрация дезинсектора (только для администратора)
@auth_bp.route('/admin/register_disinsector', methods=['GET', 'POST'])
def register_disinsector():
    if 'admin_id' in session:
        form = RegisterDisinsectorForm()
        if form.validate_on_submit():
            name = form.name.data.strip()
            email = form.email.data.strip().lower()
            token = form.token.data.strip()
            password = form.password.data  # Получаем пароль из формы

            current_app.logger.info(f"Попытка регистрации дезинсектора с email: {email}")

            # Проверяем, есть ли уже дезинсектор с таким email
            existing_disinsector = Disinsector.query.filter_by(email=email).first()
            if existing_disinsector:
                flash('Дезинсектор с таким email уже существует.', 'danger')
                current_app.logger.warning(f"Дезинсектор с email {email} уже существует.")
                return redirect(url_for('auth.register_disinsector'))

            # Создаём нового дезинсектора
            new_disinsector = Disinsector(
                name=name,
                email=email,
                token=token,
                password=generate_password_hash(password)  # Хэшируем пароль
                # telegram_user_id не устанавливается здесь
            )
            try:
                db.session.add(new_disinsector)
                db.session.commit()
                flash(f"Дезинсектор {name} успешно зарегистрирован!", 'success')
                current_app.logger.info(f"Дезинсектор с email {email} успешно зарегистрирован.")
                # Отправка сообщения только если telegram_user_id установлен
                if new_disinsector.telegram_user_id:
                    send_telegram_message(new_disinsector.token, new_disinsector.telegram_user_id, "Добро пожаловать!")
                return redirect(url_for('main.admin_dashboard'))
            except IntegrityError:
                db.session.rollback()
                flash('Дезинсектор с таким email уже существует.', 'danger')
                current_app.logger.error(f"Дезинсектор с email {email} уже существует.")
                return redirect(url_for('auth.register_disinsector'))
            except Exception as e:
                db.session.rollback()
                flash('Произошла ошибка при регистрации.', 'danger')
                current_app.logger.error(f"Ошибка при регистрации дезинсектора: {e}")
                return redirect(url_for('auth.register_disinsector'))
        else:
            if request.method == 'POST':
                current_app.logger.warning(f"Форма регистрации дезинсектора не прошла валидацию: {form.errors}")
        return render_template('register_disinsector.html', form=form)
    else:
        flash('Требуется авторизация администратора.', 'warning')
        return redirect(url_for('auth.admin_login'))

# Вход для дезинсектора
@auth_bp.route('/login', methods=['GET', 'POST'])
def disinsector_login():
    if request.method == 'POST':
        email = request.form.get('email')
        token = request.form.get('token')

        disinsector = Disinsector.query.filter_by(email=email).first()

        if disinsector and disinsector.token == token:
            # Устанавливаем 'disinsector_id' для сессии
            session['disinsector_id'] = disinsector.id

            if disinsector.token and disinsector.telegram_user_id:
                welcome_text = f"Добро пожаловать, {disinsector.name}! Вы успешно вошли в свой кабинет."
                send_telegram_message(disinsector.token, disinsector.telegram_user_id, welcome_text)
                flash('Вы успешно вошли в систему и получили приветственное сообщение в Telegram!', 'success')
                current_app.logger.info(f"Отправлено приветственное сообщение дезинсектору {disinsector.name} (ID: {disinsector.id})")
            else:
                flash('У вас не установлен Telegram User ID или токен бота.', 'warning')
                current_app.logger.warning(f"Дезинсектор {disinsector.name} не имеет токена бота или Telegram User ID.")

            return redirect(url_for('main.disinsector_dashboard'))
        else:
            flash('Неверный email или токен.', 'danger')
            current_app.logger.warning(f"Неудачная попытка входа для email: {email}")

    return render_template('disinsector_login.html')

# Выход из системы
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('main.index'))
