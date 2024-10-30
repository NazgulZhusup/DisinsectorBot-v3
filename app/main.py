from flask import Blueprint, render_template, redirect, url_for, session, flash, request, jsonify
from app import db, csrf
from app.model import Order, Client, Disinsector

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if 'user_id' in session and session.get('role') == 'admin':
        status = request.args.get('status', 'Все')
        if status == 'Все':
            orders = Order.query.all()
        else:
            orders = Order.query.filter_by(order_status=status).all()
        return render_template('admin_dashboard.html', orders=orders)
    else:
        return redirect(url_for('auth.admin_login'))

@main_bp.route('/disinsector/dashboard')
def disinsector_dashboard():
    if 'user_id' in session and session.get('role') == 'disinsector':
        disinsector_id = session['user_id']
        disinsector = Disinsector.query.get(disinsector_id)
        if not disinsector:
            flash("Дезинсектор не найден.")
            return redirect(url_for('auth.disinsector_login'))
        orders = Order.query.filter_by(disinsector_id=disinsector_id).all()
        return render_template('disinsector_dashboard.html', disinsector=disinsector, orders=orders)
    else:
        return redirect(url_for('auth.disinsector_login'))

@csrf.exempt
@main_bp.route('/api/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Extract fields
    client_name = data.get('client_name')
    object_type = data.get('object_type')
    insect_quantity = data.get('insect_quantity')
    disinsect_experience = data.get('disinsect_experience')
    phone_number = data.get('phone_number')
    address = data.get('address')

    # Check required fields
    if not all([client_name, object_type, insect_quantity, disinsect_experience, phone_number, address]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Convert disinsect_experience to Boolean
    disinsect_experience_bool = True if disinsect_experience == 'yes' else False

    # Find or create client
    client = Client.query.filter_by(phone=phone_number).first()
    if not client:
        client = Client(name=client_name, phone=phone_number, address=address)
        db.session.add(client)
        db.session.commit()

    # Create new order
    new_order = Order(
        client_id=client.id,
        object_type=object_type,
        insect_quantity=insect_quantity,
        disinsect_experience=disinsect_experience_bool,
        order_status='Новая'
    )
    db.session.add(new_order)
    db.session.commit()

    # Notify disinfectors about new order
    # (Assuming functionality exists elsewhere)

    return jsonify({'status': 'success'}), 200

@main_bp.route('/update_order_status', methods=['POST'])
def update_order_status():
    if 'user_id' in session and session.get('role') == 'disinsector':
        order_id = request.form.get('order_id')
        new_status = request.form.get('new_status')

        if not order_id or not new_status:
            flash("Неверные данные.")
            return redirect(url_for('main.disinsector_dashboard'))

        order = Order.query.get(order_id)
        if order:
            order.order_status = new_status
            db.session.commit()
            flash("Статус заявки обновлен.")
        else:
            flash("Заявка не найдена.")

        return redirect(url_for('main.disinsector_dashboard'))
    else:
        flash("Неавторизованный доступ.")
        return redirect(url_for('auth.disinsector_login'))
