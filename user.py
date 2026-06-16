import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from app.models import Cart, Order, OrderItem, Prescription, Address, Product, User, db
from werkzeug.utils import secure_filename

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'user':
        return redirect(url_for('admin.dashboard'))
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    prescriptions = Prescription.query.filter_by(user_id=current_user.id).all()
    return render_template('user/dashboard.html', orders=orders, prescriptions=prescriptions)

@user_bp.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('user/cart.html', cart_items=cart_items, total=total)

@user_bp.route('/update_cart/<int:item_id>/<action>')
@login_required
def update_cart(item_id, action):
    item = Cart.query.get_or_404(item_id)
    if action == 'add':
        item.quantity += 1
    elif action == 'sub' and item.quantity > 1:
        item.quantity -= 1
    elif action == 'remove':
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for('user.cart'))

@user_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('main.index'))
    
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    if request.method == 'POST':
        # Create Address
        new_address = Address(
            user_id=current_user.id,
            full_name=request.form.get('full_name'),
            phone=request.form.get('phone'),
            address_line=request.form.get('address'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            zip_code=request.form.get('zip_code')
        )
        db.session.add(new_address)
        db.session.flush() # Get address ID
        
        # Create Order
        payment_method = request.form.get('payment_method')
        order = Order(
            user_id=current_user.id,
            address_id=new_address.id,
            total_amount=total,
            payment_method=payment_method
        )
        
        # If paying online (UPI or Card), transfer money to admin wallet
        if payment_method in ['UPI', 'Card']:
            # Find the primary admin (usually the first one)
            admin = User.query.filter_by(role='admin').first()
            if admin:
                if admin.wallet_balance is None:
                    admin.wallet_balance = 0
                admin.wallet_balance += total
            order.status = 'Confirmed' # Auto-confirm paid orders
            
        db.session.add(order)
        db.session.flush()
        
        # Move cart items to order items
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_at_time=item.product.price
            )
            # Update Stock
            item.product.stock -= item.quantity
            db.session.add(order_item)
            db.session.delete(item)
            
        db.session.commit()
        flash('Order placed successfully!', 'success')
        return render_template('user/confirmation.html', order=order)
        
    return render_template('user/checkout.html', total=total)

@user_bp.route('/upload_prescription', methods=['POST'])
@login_required
def upload_prescription():
    if 'prescription' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('user.dashboard'))
    
    file = request.files['prescription']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('user.dashboard'))
        
    if file:
        try:
            filename = secure_filename(file.filename)
            # Ensure filename is unique or add timestamp to avoid overwriting
            from datetime import datetime
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            
            upload_folder = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
                
            upload_path = os.path.join(upload_folder, filename)
            file.save(upload_path)
            
            prescription = Prescription(user_id=current_user.id, file_path=filename)
            db.session.add(prescription)
            db.session.commit()
            flash('Prescription uploaded successfully. Admin will review it soon.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading file: {str(e)}', 'danger')
            current_app.logger.error(f"Upload error: {e}")
    
    return redirect(url_for('user.dashboard'))

@user_bp.route('/track_order/<int:order_id>')
@login_required
def track_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('user.dashboard'))
    return render_template('user/tracking.html', order=order)

@user_bp.route('/cancel_order/<int:order_id>')
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id or (order.status != 'Pending' and order.status != 'Confirmed'):
        flash('Order cannot be cancelled at this stage', 'danger')
        return redirect(url_for('user.dashboard'))
    
    order.status = 'Cancelled'
    db.session.commit()
    flash('Order cancelled successfully', 'success')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.username = request.form.get('username')
        current_user.email = request.form.get('email')
        current_user.phone_number = request.form.get('phone_number')
        
        new_password = request.form.get('new_password')
        if new_password:
            current_user.set_password(new_password)
            
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Email or Phone might already exist.', 'danger')
            
        return redirect(url_for('user.profile'))
        
    return render_template('user/profile.html')
