from flask import Blueprint, render_template
from app.models import Product, Category

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    categories = Category.query.all()
    # Fetch some featured products for the home page
    featured_products = Product.query.limit(8).all()
    return render_template('main/index.html', categories=categories, products=featured_products)

@main_bp.route('/about')
def about():
    return render_template('main/about.html')

@main_bp.route('/contact')
def contact():
    return render_template('main/contact.html')

@main_bp.route('/return_policy')
def return_policy():
    return render_template('main/return_policy.html')
