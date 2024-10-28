from flask import Blueprint, render_template, redirect, url_for, session, flash, request
from app.model import Disinsector, Order, Client
from app import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' in session and session.get('role') == 'admin':
        orders = Order.query.all()
        return render_template('admin_dashboard.html', orders=orders)
    return redirect(url_for('auth.admin_login'))

@main_bp.route('/disinsector/dashboard')
def disinsector_dashboard():
    if 'user_id' in session and session.get('role') == 'disinsector':
        disinsector_id = session['user_id']
        orders = Order.query.filter_by(disinsector_id=disinsector_id).all()
        return render_template('disinsector_dashboard.html', orders=orders)
    return redirect(url_for('auth.disinsector_login'))
