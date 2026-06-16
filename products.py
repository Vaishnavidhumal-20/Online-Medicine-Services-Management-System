from flask import Blueprint, render_template, jsonify, request
from app.models import Product, Category, Cart, db
from flask_login import current_user

product_bp = Blueprint('product_bp', __name__)

@product_bp.route('/medicines')
def all_medicines():
    categories = Category.query.all()
    products = Product.query.all()
    return render_template('products/list.html', products=products, categories=categories)

@product_bp.route('/search')
def search():
    q = request.args.get('q', '')
    categories = Category.query.all()
    if q:
        products = Product.query.filter(Product.name.contains(q) | Product.description.contains(q)).all()
    else:
        products = []
    return render_template('products/list.html', products=products, categories=categories, search_query=q)

@product_bp.route('/category/<int:category_id>')
def category_products(category_id):
    categories = Category.query.all()
    category = Category.query.get_or_404(category_id)
    products = Product.query.filter_by(category_id=category_id).all()
    return render_template('products/list.html', products=products, categories=categories, current_category=category)

@product_bp.route('/details/<int:product_id>')
def product_details(product_id):
    from app.models import Review
    product = Product.query.get_or_404(product_id)
    reviews = Review.query.filter_by(product_id=product_id).order_by(Review.created_at.desc()).all()
    return render_template('products/details.html', product=product, reviews=reviews)

@product_bp.route('/submit_review/<int:product_id>', methods=['POST'])
def submit_review(product_id):
    from app.models import Review
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Login required'})
    
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    
    if not rating:
        return jsonify({'success': False, 'message': 'Rating is required'})
    
    review = Review(
        user_id=current_user.id,
        product_id=product_id,
        rating=int(rating),
        comment=comment
    )
    db.session.add(review)
    
    # Update product average rating
    product = Product.query.get(product_id)
    all_reviews = Review.query.filter_by(product_id=product_id).all()
    if all_reviews:
        total_rating = sum([r.rating for r in all_reviews])
        product.rating = total_rating / len(all_reviews)
    else:
        product.rating = int(rating)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Review submitted!'})

@product_bp.route('/add_to_cart/<int:product_id>/<int:quantity>', methods=['POST'])
def add_to_cart(product_id, quantity):
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    product = Product.query.get_or_404(product_id)
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    cart_count = Cart.query.filter_by(user_id=current_user.id).count()
    return jsonify({'success': True, 'cart_count': cart_count})
