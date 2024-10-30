from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.model import Admin, Disinsector
from app.forms import RegisterDisinsectorForm

auth_bp = Blueprint('auth', __name__)


# Регистрация администратора
@auth_bp.route('/register_admin', methods=['GET', 'POST'])
def register_admin():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        # Проверяем, есть ли уже администратор с таким email
        existing_admin = Admin.query.filter_by(email=email).first()
        if existing_admin:
            flash('Администратор с таким email уже существует.')
            return redirect(url_for('auth.register_admin'))

        new_admin = Admin(email=email, password=password)
        db.session.add(new_admin)
        db.session.commit()

        flash("Администратор успешно зарегистрирован!")
        return redirect(url_for('auth.admin_login'))

    return render_template('register_admin.html')


# Вход для администратора
@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        admin = Admin.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password, password):
            session['user_id'] = admin.id
            session['role'] = 'admin'
            return redirect(url_for('main.admin_dashboard'))
        else:
            flash('Неверный email или пароль.')
            return redirect(url_for('auth.admin_login'))

    return render_template('admin_login.html')


# Регистрация дезинсектора (только для администратора)
@auth_bp.route('/register_disinsector', methods=['GET', 'POST'])
def register_disinsector():
    if 'user_id' in session and session.get('role') == 'admin':
        form = RegisterDisinsectorForm()
        if form.validate_on_submit():
            name = form.name.data
            email = form.email.data
            password = generate_password_hash(form.password.data)
            token = form.token.data

            # Проверяем, есть ли уже дезинсектор с таким email
            existing_disinsector = Disinsector.query.filter_by(email=email).first()
            if existing_disinsector:
                flash('Дезинсектор с таким email уже существует.')
                return redirect(url_for('auth.register_disinsector'))

            new_disinsector = Disinsector(name=name, email=email, password=password, token=token)
            db.session.add(new_disinsector)
            db.session.commit()
            flash(f"Дезинсектор {name} успешно зарегистрирован!")
            return redirect(url_for('main.admin_dashboard'))

        return render_template('register_disinsector.html', form=form)
    else:
        return redirect(url_for('auth.admin_login'))
# Вход для дезинсектора
@auth_bp.route('/disinsector/login', methods=['GET', 'POST'])
def disinsector_login():
    if request.method == 'POST':
        token = request.form['token']

        disinsector = Disinsector.query.filter_by(token=token).first()
        if disinsector:
            session['user_id'] = disinsector.id
            session['role'] = 'disinsector'
            return redirect(url_for('main.disinsector_dashboard'))
        else:
            flash('Неверный токен.')
            return redirect(url_for('auth.disinsector_login'))

    return render_template('disinsector_login.html')


# Выход из системы
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))
