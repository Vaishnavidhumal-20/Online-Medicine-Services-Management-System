from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from app.models import Order, User, DeliveryPartner, db
from functools import wraps
from datetime import datetime

delivery_bp = Blueprint('delivery', __name__)

def delivery_partner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'delivery_partner':
            flash('Delivery Partner access required.', 'danger')
            return redirect(url_for('auth.login', role='delivery_partner'))
        return f(*args, **kwargs)
    return decorated_function

@delivery_bp.route('/dashboard')
@delivery_partner_required
def dashboard():
    # Stats for the delivery partner
    total_assigned = Order.query.filter_by(delivery_partner_id=current_user.id).count()
    active_deliveries = Order.query.filter_by(delivery_partner_id=current_user.id).filter(Order.status.in_(['Order Confirmed', 'Packed', 'Out for Delivery', 'Reached Nearby Location'])).count()
    completed_deliveries = Order.query.filter_by(delivery_partner_id=current_user.id, status='Delivered').count()
    
    recent_orders = Order.query.filter_by(delivery_partner_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('delivery/dashboard.html', 
                           total_assigned=total_assigned,
                           active_deliveries=active_deliveries,
                           completed_deliveries=completed_deliveries,
                           recent_orders=recent_orders)

@delivery_bp.route('/assigned_orders')
@delivery_partner_required
def assigned_orders():
    orders = Order.query.filter_by(delivery_partner_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('delivery/assigned_orders.html', orders=orders)

@delivery_bp.route('/order_details/<int:order_id>')
@delivery_partner_required
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    if order.delivery_partner_id != current_user.id:
        flash('Unauthorized access to this order.', 'danger')
        return redirect(url_for('delivery.dashboard'))
    return render_template('delivery/order_details.html', order=order)

@delivery_bp.route('/update_status/<int:order_id>', methods=['POST'])
@delivery_partner_required
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    if order.delivery_partner_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('delivery.dashboard'))
    
    new_status = request.form.get('status')
    otp = request.form.get('otp')
    manual_location = request.form.get('current_location')
    manual_time = request.form.get('estimated_delivery')
    
    if new_status == 'Delivered':
        if otp != order.delivery_otp:
            flash('Invalid OTP. Please enter the correct OTP from the customer.', 'danger')
            return redirect(url_for('delivery.order_details', order_id=order.id))
        
        # Increment total deliveries for the partner
        partner_profile = DeliveryPartner.query.filter_by(user_id=current_user.id).first()
        if partner_profile:
            partner_profile.total_deliveries += 1
            
    order.status = new_status
    
    # Handle Location and Time (Manual or Simulated Defaults)
    if manual_location:
        order.current_location = manual_location
    else:
        # Fallback to smart simulation if manual is empty
        if new_status == 'Packed': order.current_location = "Warehouse (Packed)"
        elif new_status == 'Out for Delivery': order.current_location = "En route to your city"
        elif new_status == 'Reached Nearby Location': order.current_location = "At Baramati Hub / 1km away"
        elif new_status == 'Delivered': order.current_location = "At Customer Residence"

    if manual_time:
        order.estimated_delivery_time = manual_time
    else:
        # Fallback to smart simulation if manual is empty
        if new_status == 'Packed': order.estimated_delivery_time = "Within 4-6 hours"
        elif new_status == 'Out for Delivery': order.estimated_delivery_time = "Within 1-2 hours"
        elif new_status == 'Reached Nearby Location': order.estimated_delivery_time = "Within 15 minutes"
        elif new_status == 'Delivered': order.estimated_delivery_time = "Delivered Successfully"

    db.session.commit()
    flash(f'Order status updated to {new_status}', 'success')
    return redirect(url_for('delivery.order_details', order_id=order.id))

@delivery_bp.route('/notifications')
@delivery_partner_required
def notifications():
    return render_template('delivery/notifications.html')
