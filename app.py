from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, timedelta
import json
import uuid
import os
import calendar
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production

# Ensure data directory exists
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

BREAD_TYPES_FILE = os.path.join(DATA_DIR, 'bread_types.json')
BAKING_DAYS_FILE = os.path.join(DATA_DIR, 'baking_days.json')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')

# Day of week choices (0 = Monday, 6 = Sunday)
WEEKDAYS = list(calendar.day_name)

def load_json_file(filepath, default=None):
    if default is None:
        default = []
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json_file(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def get_bread_types():
    return load_json_file(BREAD_TYPES_FILE, [])

def get_baking_days():
    return load_json_file(BAKING_DAYS_FILE, [])

def get_orders():
    return load_json_file(ORDERS_FILE, [])

def save_bread_type(name):
    bread_types = get_bread_types()
    # Check if bread type already exists
    if any(bt['name'] == name for bt in bread_types):
        return False
    bread_type = {
        'id': str(uuid.uuid4()),
        'name': name
    }
    bread_types.append(bread_type)
    save_json_file(BREAD_TYPES_FILE, bread_types)
    return True

def save_baking_day(date, bread_options):
    baking_days = get_baking_days()
    baking_day = {
        'id': str(uuid.uuid4()),
        'date': date,
        'share_link': str(uuid.uuid4()),
        'bread_options': bread_options
    }
    baking_days.append(baking_day)
    save_json_file(BAKING_DAYS_FILE, baking_days)
    return baking_day

def save_order(baking_day_id, customer_name, customer_address, bread_orders):
    """
    Save an order with multiple bread types
    bread_orders is a list of dicts with bread_type_id and quantity
    """
    orders = get_orders()
    order_group_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    for bread_order in bread_orders:
        order = {
            'id': str(uuid.uuid4()),
            'order_group_id': order_group_id,
            'baking_day_id': baking_day_id,
            'customer_name': customer_name,
            'customer_address': customer_address,
            'bread_type_id': bread_order['bread_type_id'],
            'quantity': bread_order['quantity'],
            'created_at': created_at
        }
        orders.append(order)
    
    save_json_file(ORDERS_FILE, orders)
    return order_group_id

def get_baking_day_by_share_link(share_link):
    baking_days = get_baking_days()
    for day in baking_days:
        if day['share_link'] == share_link:
            # Convert date string to datetime.date object
            day['date'] = datetime.strptime(day['date'], '%Y-%m-%d').date()
            return day
    return None

def get_orders_for_baking_day(baking_day_id):
    orders = get_orders()
    return [order for order in orders if order['baking_day_id'] == baking_day_id]

def get_bread_type_by_id(bread_type_id):
    bread_types = get_bread_types()
    for bt in bread_types:
        if bt['id'] == bread_type_id:
            return bt
    return None

def get_next_weekday(weekday_name):
    """Get the date of the next occurrence of a weekday."""
    today = datetime.now().date()
    target_weekday = WEEKDAYS.index(weekday_name)
    days_ahead = target_weekday - today.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return today + timedelta(days=days_ahead)

def get_baking_day_by_id(baking_day_id):
    baking_days = get_baking_days()
    for day in baking_days:
        if day['id'] == baking_day_id:
            return day
    return None

def delete_baking_day(baking_day_id):
    baking_days = get_baking_days()
    orders = get_orders()
    
    # Remove the baking day
    baking_days = [day for day in baking_days if day['id'] != baking_day_id]
    
    # Remove associated orders
    orders = [order for order in orders if order['baking_day_id'] != baking_day_id]
    
    save_json_file(BAKING_DAYS_FILE, baking_days)
    save_json_file(ORDERS_FILE, orders)

def check_password(password):
    try:
        with open('password.json', 'r') as f:
            password_data = json.load(f)
            return password == password_data.get('password')
    except (FileNotFoundError, json.JSONDecodeError):
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if check_password(password):
            session['logged_in'] = True
            return redirect(url_for('baker_home'))
        else:
            flash('Incorrect password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Routes
@app.route('/')
@login_required
def baker_home():
    bread_types = get_bread_types()
    baking_days = get_baking_days()
    
    # Convert date strings to datetime objects for comparison
    today = datetime.now().date()
    upcoming_days = []
    for day in baking_days:
        day_date = datetime.strptime(day['date'], '%Y-%m-%d').date()
        if day_date >= today:
            day_copy = day.copy()
            day_copy['date'] = day_date
            
            # Get orders for this day
            orders = get_orders_for_baking_day(day_copy['id'])
            
            # Calculate order summaries
            day_copy['total_orders'] = len(orders)
            day_copy['total_loaves'] = sum(order['quantity'] for order in orders)
            day_copy['max_total_loaves'] = sum(option['max_quantity'] for option in day_copy['bread_options'])
            
            # Add bread type names and order quantities to options
            for option in day_copy['bread_options']:
                bread_type = get_bread_type_by_id(option['bread_type_id'])
                if bread_type:
                    option['bread_type_name'] = bread_type['name']
                # Calculate ordered quantity for this bread type
                option['ordered_quantity'] = sum(
                    order['quantity'] for order in orders 
                    if order['bread_type_id'] == option['bread_type_id']
                )
            
            upcoming_days.append(day_copy)
    
    upcoming_days.sort(key=lambda x: x['date'])
    return render_template('baker_home.html', 
                         bread_types=bread_types, 
                         upcoming_days=upcoming_days,
                         weekdays=WEEKDAYS)

@app.route('/manage')
@login_required
def manage_baking():
    bread_types = get_bread_types()
    return render_template('manage_baking.html', 
                         bread_types=bread_types,
                         weekdays=WEEKDAYS)

@app.route('/delete_bread_type/<bread_type_id>', methods=['POST'])
@login_required
def delete_bread_type(bread_type_id):
    bread_types = get_bread_types()
    bread_types = [bt for bt in bread_types if bt['id'] != bread_type_id]
    save_json_file(BREAD_TYPES_FILE, bread_types)
    flash('Bread type deleted successfully!')
    return redirect(url_for('manage_baking'))

@app.route('/add_bread_type', methods=['POST'])
@login_required
def add_bread_type():
    name = request.form.get('name')
    if name and save_bread_type(name):
        flash('Bread type added successfully!')
    else:
        flash('This bread type already exists!')
    return redirect(url_for('manage_baking'))

@app.route('/add_baking_day', methods=['POST'])
@login_required
def add_baking_day():
    weekday = request.form.get('weekday')
    bread_types = request.form.getlist('bread_types[]')
    quantities = request.form.getlist('quantities[]')
    
    if weekday and bread_types and quantities:
        next_date = get_next_weekday(weekday)
        bread_options = []
        for bread_type_id, quantity in zip(bread_types, quantities):
            bread_options.append({
                'bread_type_id': bread_type_id,
                'max_quantity': int(quantity)
            })
        
        baking_day = save_baking_day(next_date.strftime('%Y-%m-%d'), bread_options)
        flash(f'Baking day added for next {weekday}!')
    
    return redirect(url_for('baker_home'))

@app.route('/delete_baking_day/<baking_day_id>', methods=['POST'])
@login_required
def delete_baking_day_route(baking_day_id):
    baking_day = get_baking_day_by_id(baking_day_id)
    if baking_day:
        delete_baking_day(baking_day_id)
        flash('Baking day deleted successfully!')
    return redirect(url_for('baker_home'))

def get_order_deadline(baking_date):
    """Calculate the order deadline (10 PM two days before baking)"""
    # Convert to datetime to handle time
    baking_datetime = datetime.combine(baking_date, datetime.min.time())
    # Go back 2 days and set time to 22:00 (10 PM)
    deadline = baking_datetime - timedelta(days=2)
    deadline = deadline.replace(hour=22, minute=0, second=0, microsecond=0)
    return deadline

def has_existing_order(baking_day_id, customer_name):
    """Check if a customer has already ordered for this baking day"""
    orders = get_orders_for_baking_day(baking_day_id)
    return any(order['customer_name'].lower() == customer_name.lower() for order in orders)

@app.route('/orders/<share_link>')
def order_page(share_link):
    baking_day = get_baking_day_by_share_link(share_link)
    if not baking_day:
        return 'Baking day not found', 404
    
    # Calculate order deadline
    order_deadline = get_order_deadline(baking_day['date'])
    # Check if ordering window is still open
    can_order = datetime.now() < order_deadline
    
    # Check for existing order if name is in localStorage (passed via query param)
    customer_name = request.args.get('check_name', '')
    has_ordered = False
    if customer_name:
        has_ordered = has_existing_order(baking_day['id'], customer_name)
    
    # Get available quantities
    orders = get_orders_for_baking_day(baking_day['id'])
    for option in baking_day['bread_options']:
        ordered_quantity = sum(
            order['quantity'] for order in orders 
            if order['bread_type_id'] == option['bread_type_id']
        )
        option['available'] = option['max_quantity'] - ordered_quantity
        bread_type = get_bread_type_by_id(option['bread_type_id'])
        if bread_type:
            option['bread_type_name'] = bread_type['name']
    
    return render_template('order_page.html', 
                         baking_day=baking_day, 
                         can_order=can_order,
                         has_ordered=has_ordered,
                         customer_name=customer_name,
                         order_deadline=order_deadline)

@app.route('/submit_order/<share_link>', methods=['POST'])
def submit_order(share_link):
    baking_day = get_baking_day_by_share_link(share_link)
    if not baking_day:
        return 'Baking day not found', 404
    
    # Check if ordering window is still open
    order_deadline = get_order_deadline(baking_day['date'])
    if datetime.now() >= order_deadline:
        flash('Sorry, the ordering window has closed for this baking day.')
        return redirect(url_for('order_page', share_link=share_link))
    
    name = request.form.get('name')
    address = request.form.get('address')
    
    # Check for existing order
    if has_existing_order(baking_day['id'], name):
        flash('You have already placed an order for this baking day.')
        return redirect(url_for('order_page', share_link=share_link, check_name=name))
    
    # Get quantities for each bread type
    bread_orders = []
    total_quantity = 0
    
    # Parse the quantities from form data
    for key, value in request.form.items():
        if key.startswith('quantities[') and key.endswith(']'):
            bread_type_id = key[len('quantities['):-1]  # Extract bread_type_id from the field name
            quantity = int(value) if value.isdigit() else 0
            if quantity > 0:
                bread_type = get_bread_type_by_id(bread_type_id)
                bread_orders.append({
                    'bread_type_id': bread_type_id,
                    'bread_type_name': bread_type['name'] if bread_type else 'Unknown',
                    'quantity': quantity
                })
                total_quantity += quantity
    
    if not name or not address or not bread_orders:
        flash('Please fill in all required fields')
        return redirect(url_for('order_page', share_link=share_link))
    
    if total_quantity > 2:
        flash('Maximum 2 loaves total per order')
        return redirect(url_for('order_page', share_link=share_link))
    
    # Check if quantities are available
    orders = get_orders_for_baking_day(baking_day['id'])
    for bread_order in bread_orders:
        for option in baking_day['bread_options']:
            if option['bread_type_id'] == bread_order['bread_type_id']:
                ordered_quantity = sum(
                    order['quantity'] for order in orders 
                    if order['bread_type_id'] == bread_order['bread_type_id']
                )
                if ordered_quantity + bread_order['quantity'] > option['max_quantity']:
                    flash('Sorry, not enough quantity available for one or more bread types!')
                    return redirect(url_for('order_page', share_link=share_link))
    
    # Save the order
    order_id = save_order(baking_day['id'], name, address, bread_orders)
    flash('Your order has been submitted successfully!')
    
    return redirect(url_for('order_page', 
                          share_link=share_link,
                          order_success=True,
                          order_id=order_id,
                          customer_name=name,
                          customer_address=address))

@app.route('/view_orders/<share_link>')
def view_orders(share_link):
    baking_day = get_baking_day_by_share_link(share_link)
    if not baking_day:
        return 'Baking day not found', 404
    
    orders = get_orders_for_baking_day(baking_day['id'])
    
    # Add bread type names to orders
    for order in orders:
        bread_type = get_bread_type_by_id(order['bread_type_id'])
        if bread_type:
            order['bread_type_name'] = bread_type['name']
        # Convert ISO format to datetime
        order['created_at'] = datetime.fromisoformat(order['created_at'])
    
    # Add bread type names to options
    for option in baking_day['bread_options']:
        bread_type = get_bread_type_by_id(option['bread_type_id'])
        if bread_type:
            option['bread_type_name'] = bread_type['name']
        # Calculate ordered quantity
        option['ordered_quantity'] = sum(
            order['quantity'] for order in orders 
            if order['bread_type_id'] == option['bread_type_id']
        )
    
    return render_template('view_orders.html', 
                         baking_day=baking_day,
                         orders=orders)

@app.route('/health')
def health_check():
    try:
        # Try to read the data directory to ensure it's accessible
        if not os.path.exists(DATA_DIR):
            return 'Data directory not accessible', 500
            
        # Try to load the JSON files to ensure they're readable
        get_bread_types()
        get_baking_days()
        get_orders()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/check_existing_order/<share_link>')
def check_existing_order(share_link):
    baking_day = get_baking_day_by_share_link(share_link)
    if not baking_day:
        return jsonify({'error': 'Baking day not found'}), 404
    
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'has_ordered': False})
    
    has_ordered = has_existing_order(baking_day['id'], name)
    return jsonify({
        'has_ordered': has_ordered,
        'customer_name': name
    })

if __name__ == '__main__':
    # Create data files if they don't exist
    for filepath in [BREAD_TYPES_FILE, BAKING_DAYS_FILE, ORDERS_FILE]:
        if not os.path.exists(filepath):
            save_json_file(filepath, [])
    
    app.run(debug=True) 