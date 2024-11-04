# app/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app.model import Admin, Disinsector
from database import db
import logging
from sqlalchemy.exc import IntegrityError
from app.forms import RegisterDisinsectorForm

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger('auth')

# Регистрация администратора
@auth_bp.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        new_admin = Admin(email=email, password=hashed_password)

        try:
            db.session.add(new_admin)
            db.session.commit()
            flash('Администратор успешно зарегистрирован!', 'success')
            return redirect(url_for('auth.admin_login'))
        except IntegrityError:
            db.session.rollback()
            flash('Администратор с таким email уже существует.', 'danger')
            logger.error(f"Администратор с email {email} уже существует.")
            return redirect(url_for('auth.admin_register'))
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при регистрации.', 'danger')
            logger.error(f"Ошибка при регистрации администратора: {e}")
            return redirect(url_for('auth.admin_register'))

    return render_template('admin_register.html')

# Вход для администратора
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            admin = db.session.query(Admin).filter_by(email=email).first()
            if admin and check_password_hash(admin.password, password):
                session['user_id'] = admin.id
                session['role'] = 'admin'
                logger.info(f"Admin {admin.email} вошел в систему.")
                return redirect(url_for('main.admin_dashboard'))
            else:
                logger.warning(f"Неудачная попытка входа для email: {email}")
                error = "Неверный email или пароль."
        except Exception as e:
            logger.error(f"Ошибка при входе админа: {e}")
            error = "Произошла ошибка. Пожалуйста, попробуйте позже."
        return render_template('admin_login.html', error=error)
    return render_template('admin_login.html')

# Регистрация дезинсектора (только для администратора)
@auth_bp.route('/register_disinsector', methods=['GET', 'POST'])
def register_disinsector():
    form = RegisterDisinsectorForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        token = form.token.data
        telegram_user_id = form.telegram_user_id.data  # Добавьте поле telegram_user_id в форму

        # Проверка, существует ли уже Disinsector с этим telegram_user_id
        existing_disinsector = Disinsector.query.filter_by(telegram_user_id=telegram_user_id).first()
        if existing_disinsector:
            flash("Дезинсектор с этим Telegram ID уже существует.", "danger")
            logger.warning(f"Попытка регистрации дезинсектора с существующим telegram_user_id: {telegram_user_id}")
            return redirect(url_for('auth.register_disinsector'))

        try:
            new_disinsector = Disinsector(
                name=name,
                email=email,
                password=generate_password_hash(password),
                token=token,
                telegram_user_id=telegram_user_id
            )
            db.session.add(new_disinsector)
            db.session.commit()
            flash("Дезинсектор успешно зарегистрирован.", "success")
            return redirect(url_for('main.admin_dashboard'))
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"IntegrityError при регистрации дезинсектора: {e}")
            flash("Ошибка при регистрации. Возможно, email или токен уже используются.", "danger")
            return redirect(url_for('auth.register_disinsector'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при регистрации дезинсектора: {e}")
            flash("Произошла ошибка при регистрации.", "danger")
            return redirect(url_for('auth.register_disinsector'))

    return render_template('register_disinsector.html', form=form)
# Вход для дезинсектора
@auth_bp.route('/disinsector/login', methods=['GET', 'POST'])
def disinsector_login():
    if request.method == 'POST':
        token = request.form['token']
        try:
            disinsector = db.session.query(Disinsector).filter_by(token=token).first()
            if disinsector:
                session['user_id'] = disinsector.id
                session['role'] = 'disinsector'
                logger.info(f"Disinsector {disinsector.email} вошёл в систему.")
                return redirect(url_for('main.disinsector_dashboard'))
            else:
                flash('Неверный токен.', 'danger')
                return redirect(url_for('auth.disinsector_login'))
        except Exception as e:
            logger.error(f"Ошибка при входе дезинсектора: {e}")
            flash("Произошла ошибка. Пожалуйста, попробуйте позже.", 'danger')
            return redirect(url_for('auth.disinsector_login'))
    return render_template('disinsector_login.html')

# Выход из системы
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))
