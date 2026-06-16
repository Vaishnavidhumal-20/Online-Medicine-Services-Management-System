from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
import csv
import io
from flask_login import login_required, current_user
from app.models import Product, Category, Order, User, Prescription, DeliveryPartner, Expense, OrderItem, db
from functools import wraps
from sqlalchemy import func
from werkzeug.security import generate_password_hash
import random
import string

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login', role='admin'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    stats = {
        'total_orders': Order.query.count(),
        'total_products': Product.query.count(),
        'total_users': User.query.filter_by(role='user').count(),
        'total_delivery_partners': User.query.filter_by(role='delivery_partner').count(),
        'pending_prescriptions': Prescription.query.filter_by(status='Pending').count(),
        'orders_out_for_delivery': Order.query.filter_by(status='Out for Delivery').count(),
        'completed_deliveries': Order.query.filter_by(status='Delivered').count(),
        'cancelled_orders': Order.query.filter_by(status='Cancelled').count(),
        'wallet_balance': float(current_user.wallet_balance or 0)
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', stats=stats, recent_orders=recent_orders)

@admin_bp.route('/manage_products')
@admin_required
def manage_products():
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)

@admin_bp.route('/add_product', methods=['POST'])
@admin_required
def add_product():
    from app.models import ProductImage
    name = request.form.get('name')
    price = float(request.form.get('price', 0))
    stock = int(request.form.get('stock', 0))
    category_id = request.form.get('category_id')
    description = request.form.get('description')
    image_url = request.form.get('image_url')
    additional_urls = request.form.get('additional_image_urls', '').split('\n')
    
    new_product = Product(
        name=name, price=price, stock=stock, 
        category_id=category_id, description=description, image_url=image_url
    )
    db.session.add(new_product)
    db.session.flush()

    for url in additional_urls:
        url = url.strip()
        if url:
            db.session.add(ProductImage(product_id=new_product.id, image_url=url))
            
    db.session.commit()
    flash('Product added successfully', 'success')
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/edit_product/<int:product_id>', methods=['POST'])
@admin_required
def edit_product(product_id):
    from app.models import ProductImage
    product = Product.query.get_or_404(product_id)
    product.name = request.form.get('name')
    product.price = float(request.form.get('price', 0))
    product.stock = int(request.form.get('stock', 0))
    product.category_id = request.form.get('category_id')
    product.description = request.form.get('description')
    product.image_url = request.form.get('image_url')
    
    # Update additional images
    additional_urls = request.form.get('additional_image_urls', '').split('\n')
    ProductImage.query.filter_by(product_id=product_id).delete()
    for url in additional_urls:
        url = url.strip()
        if url:
            db.session.add(ProductImage(product_id=product_id, image_url=url))
            
    db.session.commit()
    flash('Product updated successfully', 'success')
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/delete_product/<int:product_id>')
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully', 'danger')
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/manage_orders')
@admin_required
def manage_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    delivery_partners = User.query.filter_by(role='delivery_partner').all()
    return render_template('admin/orders.html', orders=orders, delivery_partners=delivery_partners)

@admin_bp.route('/assign_delivery/<int:order_id>', methods=['POST'])
@admin_required
def assign_delivery(order_id):
    order = Order.query.get_or_404(order_id)
    partner_id = request.form.get('delivery_partner_id')
    
    if partner_id:
        order.delivery_partner_id = partner_id
        order.status = 'Order Confirmed'
        # Generate random OTP for delivery tracking
        order.delivery_otp = ''.join(random.choices(string.digits, k=4))
        db.session.commit()
        flash(f'Delivery partner assigned to Order #{order.id}', 'success')
    else:
        flash('Please select a delivery partner', 'warning')
        
    return redirect(url_for('admin.manage_orders'))

@admin_bp.route('/manage_delivery_partners')
@admin_required
def manage_delivery_partners():
    partners = User.query.filter_by(role='delivery_partner').all()
    return render_template('admin/delivery_partners.html', partners=partners)

@admin_bp.route('/add_delivery_partner', methods=['POST'])
@admin_required
def add_delivery_partner():
    username = request.form.get('username')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')
    vehicle = request.form.get('vehicle_number')
    
    # Check if user already exists
    if User.query.filter((User.username == username) | (User.email == email) | (User.phone_number == phone)).first():
        flash('User with this username, email or phone already exists', 'danger')
        return redirect(url_for('admin.manage_delivery_partners'))
    
    new_user = User(username=username, email=email, phone_number=phone, role='delivery_partner')
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.flush() # Get user id
    
    new_partner = DeliveryPartner(user_id=new_user.id, vehicle_number=vehicle)
    db.session.add(new_partner)
    db.session.commit()
    
    flash('Delivery Partner added successfully', 'success')
    return redirect(url_for('admin.manage_delivery_partners'))

@admin_bp.route('/edit_delivery_partner/<int:user_id>', methods=['POST'])
@admin_required
def edit_delivery_partner(user_id):
    user = User.query.get_or_404(user_id)
    partner = DeliveryPartner.query.filter_by(user_id=user_id).first()
    
    user.username = request.form.get('username')
    user.email = request.form.get('email')
    user.phone_number = request.form.get('phone')
    if partner:
        partner.vehicle_number = request.form.get('vehicle_number')
        partner.availability_status = request.form.get('availability_status')
    
    db.session.commit()
    flash('Delivery Partner updated successfully', 'success')
    return redirect(url_for('admin.manage_delivery_partners'))

@admin_bp.route('/delete_delivery_partner/<int:user_id>')
@admin_required
def delete_delivery_partner(user_id):
    user = User.query.get_or_404(user_id)
    partner = DeliveryPartner.query.filter_by(user_id=user_id).first()
    
    if partner:
        db.session.delete(partner)
    db.session.delete(user)
    db.session.commit()
    
    flash('Delivery Partner deleted successfully', 'danger')
    return redirect(url_for('admin.manage_delivery_partners'))

@admin_bp.route('/update_order_status/<int:order_id>/<status>')
@admin_required
def update_order_status(order_id, status):
    order = Order.query.get_or_404(order_id)
    order.status = status
    db.session.commit()
    flash(f'Order #{order.id} status updated to {status}', 'info')
    return redirect(url_for('admin.manage_orders'))

@admin_bp.route('/manage_prescriptions')
@admin_required
def manage_prescriptions():
    prescriptions = Prescription.query.order_by(Prescription.created_at.desc()).all()
    return render_template('admin/prescriptions.html', prescriptions=prescriptions)

@admin_bp.route('/review_prescription/<int:prescription_id>/<action>')
@admin_required
def review_prescription(prescription_id, action):
    prescription = Prescription.query.get_or_404(prescription_id)
    prescription.status = action
    db.session.commit()
    flash(f'Prescription {action}', 'success')
    return redirect(url_for('admin.manage_prescriptions'))

@admin_bp.route('/manage_categories')
@admin_required
def manage_categories():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/add_category', methods=['POST'])
@admin_required
def add_category():
    name = request.form.get('name')
    description = request.form.get('description')
    image_url = request.form.get('image_url')
    if name:
        new_cat = Category(name=name, description=description, image_url=image_url)
        db.session.add(new_cat)
        db.session.commit()
        flash('Category added successfully', 'success')
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/edit_category/<int:category_id>', methods=['POST'])
@admin_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    category.name = request.form.get('name')
    category.description = request.form.get('description')
    category.image_url = request.form.get('image_url')
    
    db.session.commit()
    flash('Category updated successfully', 'success')
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/delete_category/<int:category_id>')
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    # Check if category has products
    if category.products:
        flash('Cannot delete category with associated products.', 'warning')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully', 'danger')
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/manage_users')
@admin_required
def manage_users():
    users = User.query.filter_by(role='user').all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/reports')
@admin_required
def reports():
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    total_sales = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    total_orders = Order.query.count()
    
    # Calculate Daily Revenue for the last 8 days (8th day to calculate 7th day's growth)
    daily_stats = db.session.query(
        func.date(Order.created_at).label('day'),
        func.sum(Order.total_amount).label('revenue'),
        func.count(Order.id).label('orders')
    ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at).desc()).limit(8).all()
    
    # Process daily stats to calculate growth %
    reports_data = []
    for i in range(len(daily_stats)):
        current = daily_stats[i]
        growth = 0
        if i < len(daily_stats) - 1:
            prev = daily_stats[i+1]
            if prev.revenue > 0:
                growth = float((current.revenue - prev.revenue) / prev.revenue) * 100
        
        reports_data.append({
            'date': current.day.strftime('%d %b') if hasattr(current.day, 'strftime') else current.day,
            'revenue': float(current.revenue),
            'orders': current.orders,
            'growth': round(growth, 1)
        })
    
    # We take the first 7 days after calculating growth with the 8th day
    reports_data = reports_data[:7]
        
    return render_template('admin/reports.html', 
                          total_sales=total_sales, 
                          total_orders=total_orders,
                          reports_data=reports_data)

@admin_bp.route('/analytics')
@admin_required
def analytics():
    return render_template('admin/analytics.html')

@admin_bp.route('/api/analytics_data')
@admin_required
def api_analytics_data():
    from datetime import datetime, timedelta
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
    else:
        # Default to last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

    # 1. Summary Metrics
    total_users = User.query.filter_by(role='user').count()
    total_orders = Order.query.filter(Order.created_at.between(start_date, end_date)).count()
    total_products = Product.query.count()
    total_categories = Category.query.count()
    
    total_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        Order.created_at.between(start_date, end_date),
        Order.status != 'Cancelled'
    ).scalar() or 0
    
    total_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.date.between(start_date.date(), end_date.date())
    ).scalar() or 0
    
    # Simple profit calculation (Revenue - Expenses - Cost of Goods Sold)
    # COGS = Sum of (OrderItem.quantity * Product.cost_price)
    cogs = db.session.query(func.sum(OrderItem.quantity * Product.cost_price)).\
        join(Order, OrderItem.order_id == Order.id).\
        join(Product, OrderItem.product_id == Product.id).\
        filter(Order.created_at.between(start_date, end_date), Order.status != 'Cancelled').scalar() or 0
    
    total_profit = float(total_revenue) - float(total_expenses) - float(cogs)
    
    today = datetime.utcnow().date()
    this_month = today.replace(day=1)

    # Helper for profit calculation
    def get_profit(start, end):
        rev = db.session.query(func.sum(Order.total_amount)).filter(
            Order.created_at.between(start, end), Order.status != 'Cancelled'
        ).scalar() or 0
        exp = db.session.query(func.sum(Expense.amount)).filter(
            Expense.date.between(start.date() if hasattr(start, 'date') else start, 
                         end.date() if hasattr(end, 'date') else end)
        ).scalar() or 0
        cogs_val = db.session.query(func.sum(OrderItem.quantity * Product.cost_price)).\
            join(Order, OrderItem.order_id == Order.id).\
            join(Product, OrderItem.product_id == Product.id).\
            filter(Order.created_at.between(start, end), Order.status != 'Cancelled').scalar() or 0
        return float(rev) - float(exp) - float(cogs_val)

    daily_profit = get_profit(datetime.combine(today, datetime.min.time()), datetime.combine(today, datetime.max.time()))
    monthly_profit = get_profit(datetime.combine(this_month, datetime.min.time()), datetime.utcnow())

    # 2. Revenue vs Expense Chart Data
    revenue_trend = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(Order.total_amount).label('total'),
        func.count(Order.id).label('count')
    ).filter(Order.created_at.between(start_date, end_date), Order.status != 'Cancelled').\
    group_by(func.date(Order.created_at)).all()
    
    expense_trend = db.session.query(
        Expense.date.label('date'),
        func.sum(Expense.amount).label('total')
    ).filter(Expense.date.between(start_date.date(), end_date.date())).\
    group_by(Expense.date).all()
    
    # 3. Category Sales Distribution
    cat_sales = db.session.query(
        Category.name,
        func.sum(OrderItem.quantity * OrderItem.price_at_time).label('revenue')
    ).join(Product, Category.id == Product.category_id).\
    join(OrderItem, Product.id == OrderItem.product_id).\
    join(Order, OrderItem.order_id == Order.id).\
    filter(Order.created_at.between(start_date, end_date), Order.status != 'Cancelled').\
    group_by(Category.name).all()
    
    # 4. Top Selling Products
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('qty')
    ).join(OrderItem, Product.id == OrderItem.product_id).\
    join(Order, OrderItem.order_id == Order.id).\
    filter(Order.created_at.between(start_date, end_date), Order.status != 'Cancelled').\
    group_by(Product.name).order_by(func.sum(OrderItem.quantity).desc()).limit(10).all()
    
    # 5. Order Status Distribution
    status_dist = db.session.query(
        Order.status,
        func.count(Order.id)
    ).filter(Order.created_at.between(start_date, end_date)).\
    group_by(Order.status).all()

    # 6. User Growth
    user_growth = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id)
    ).filter(User.created_at.between(start_date, end_date), User.role == 'user').\
    group_by(func.date(User.created_at)).all()

    # 7. Low Stock Products
    low_stock = Product.query.filter(Product.stock < 10).all()

    # 8. Prescription Stats
    prescription_stats = db.session.query(
        Prescription.status,
        func.count(Prescription.id)
    ).group_by(Prescription.status).all()

    # 9. Detailed Sales Table (Last 20)
    detailed_sales = db.session.query(
        Order.id,
        Product.name.label('product_name'),
        Category.name.label('category'),
        OrderItem.quantity,
        Order.created_at,
        Order.payment_method,
        Order.total_amount
    ).join(OrderItem, Order.id == OrderItem.order_id).\
    join(Product, OrderItem.product_id == Product.id).\
    join(Category, Product.category_id == Category.id).\
    filter(Order.created_at.between(start_date, end_date)).\
    order_by(Order.created_at.desc()).limit(20).all()

    return {
        'summary': {
            'total_users': total_users,
            'total_orders': total_orders,
            'total_products': total_products,
            'total_categories': total_categories,
            'total_revenue': float(total_revenue),
            'total_expenses': float(total_expenses),
            'total_profit': float(total_profit),
            'daily_profit': daily_profit,
            'monthly_profit': monthly_profit,
            'pending_orders': Order.query.filter_by(status='Pending').count(),
            'delivered_orders': Order.query.filter_by(status='Delivered').count(),
            'active_partners': User.query.filter_by(role='delivery_partner').count()
        },
        'trends': {
            'revenue': [{'date': str(r.date), 'value': float(r.total)} for r in revenue_trend],
            'sales': [{'date': str(r.date), 'value': r.count} for r in revenue_trend],
            'expense': [{'date': str(e.date), 'value': float(e.total)} for e in expense_trend],
            'user_growth': [{'date': str(u.date), 'value': u[1]} for u in user_growth]
        },
        'categories': [{'name': c.name, 'value': float(c.revenue)} for c in cat_sales],
        'top_products': [{'name': p.name, 'value': int(p.qty)} for p in top_products],
        'status_dist': [{'name': s.status, 'value': s[1]} for s in status_dist],
        'low_stock': [{'name': p.name, 'stock': p.stock} for p in low_stock],
        'prescription_stats': [{'status': s.status, 'count': s[1]} for s in prescription_stats],
        'sales_table': [{
            'id': s.id,
            'product': s.product_name,
            'category': s.category,
            'qty': s.quantity,
            'date': s.created_at.strftime('%Y-%m-%d'),
            'method': s.payment_method,
            'amount': float(s.total_amount)
        } for s in detailed_sales]
    }

@admin_bp.route('/notifications')
@admin_required
def notifications():
    from app.models import Prescription, Order, Product
    
    # 1. Pending Prescriptions
    pending_prescriptions = Prescription.query.filter_by(status='Pending').order_by(Prescription.created_at.desc()).all()
    
    # 2. Recent Pending Orders
    pending_orders = Order.query.filter_by(status='Pending').order_by(Order.created_at.desc()).limit(10).all()
    
    # 3. Low Stock Alerts
    low_stock_products = Product.query.filter(Product.stock < 10, Product.stock > 0).all()
    out_of_stock = Product.query.filter_by(stock=0).all()
    
    return render_template('admin/notifications.html', 
                           prescriptions=pending_prescriptions,
                           orders=pending_orders,
                           low_stock=low_stock_products,
                           out_of_stock=out_of_stock)

@admin_bp.route('/export_analytics')
@admin_required
def export_analytics():
    from datetime import datetime, timedelta
    from io import StringIO
    import csv
    
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
    else:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

    detailed_sales = db.session.query(
        Order.id,
        Product.name.label('product_name'),
        Category.name.label('category'),
        OrderItem.quantity,
        Order.created_at,
        Order.payment_method,
        Order.total_amount
    ).join(OrderItem, Order.id == OrderItem.order_id).\
    join(Product, OrderItem.product_id == Product.id).\
    join(Category, Product.category_id == Category.id).\
    filter(Order.created_at.between(start_date, end_date)).\
    order_by(Order.created_at.desc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order ID', 'Product Name', 'Category', 'Quantity', 'Date', 'Payment Method', 'Total Amount'])
    
    for row in detailed_sales:
        writer.writerow([
            row.id, 
            row.product_name, 
            row.category, 
            row.quantity, 
            row.created_at.strftime('%Y-%m-%d %H:%M'), 
            row.payment_method, 
            float(row.total_amount)
        ])
    
    # Generate a nice filename using the actual dates
    fn_start = start_date.strftime('%Y-%m-%d')
    fn_end = end_date.strftime('%Y-%m-%d')
    filename = f"PharmaPlus_Sales_Report_{fn_start}_to_{fn_end}.csv"
    
    # Return as response with correct headers
    response = Response(
        output.getvalue(),
        mimetype="text/csv"
    )
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
