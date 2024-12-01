from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import json
import uuid
import os
import calendar

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

def save_order(baking_day_id, customer_name, customer_phone, bread_orders):
    """
    Save an order with multiple bread types
    bread_orders is a list of dicts with bread_type_id and quantity
    """
    orders = get_orders()
    order_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    for bread_order in bread_orders:
        order = {
            'id': str(uuid.uuid4()),
            'order_group_id': order_id,  # Group multiple bread types under one order
            'baking_day_id': baking_day_id,
            'customer_name': customer_name,
            'customer_phone': customer_phone,
            'bread_type_id': bread_order['bread_type_id'],
            'quantity': bread_order['quantity'],
            'created_at': created_at
        }
        orders.append(order)
    
    save_json_file(ORDERS_FILE, orders)
    return order_id

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

@app.route('/delete_baking_day/<baking_day_id>', methods=['POST'])
def delete_baking_day_route(baking_day_id):
    baking_day = get_baking_day_by_id(baking_day_id)
    if baking_day:
        delete_baking_day(baking_day_id)
        flash('Baking day deleted successfully!')
    return redirect(url_for('baker_home'))

# Routes
@app.route('/')
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
            # Add bread type names to options
            for option in day_copy['bread_options']:
                bread_type = get_bread_type_by_id(option['bread_type_id'])
                if bread_type:
                    option['bread_type_name'] = bread_type['name']
            upcoming_days.append(day_copy)
    
    upcoming_days.sort(key=lambda x: x['date'])
    return render_template('baker_home.html', 
                         bread_types=bread_types, 
                         upcoming_days=upcoming_days,
                         weekdays=WEEKDAYS)

@app.route('/add_bread_type', methods=['POST'])
def add_bread_type():
    name = request.form.get('name')
    if name and save_bread_type(name):
        flash('Bread type added successfully!')
    else:
        flash('This bread type already exists!')
    return redirect(url_for('baker_home'))

@app.route('/add_baking_day', methods=['POST'])
def add_baking_day():
    weekday = request.form.get('weekday')
    bread_types = request.form.getlist('bread_types[]')
    quantities = request.form.getlist('quantities[]')
    
    if weekday and bread_types and quantities:
        # Calculate the next occurrence of the selected weekday
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

@app.route('/orders/<share_link>')
def order_page(share_link):
    baking_day = get_baking_day_by_share_link(share_link)
    if not baking_day:
        return 'Baking day not found', 404
    
    # Check if ordering window is still open (>36 hours before baking)
    cutoff_time = datetime.combine(baking_day['date'], datetime.min.time()) - timedelta(hours=36)
    can_order = datetime.now() < cutoff_time
    
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
                         can_order=can_order)

@app.route('/submit_order/<share_link>', methods=['POST'])
def submit_order(share_link):
    baking_day = get_baking_day_by_share_link(share_link)
    if not baking_day:
        return 'Baking day not found', 404
    
    # Check if ordering window is still open
    cutoff_time = datetime.combine(baking_day['date'], datetime.min.time()) - timedelta(hours=36)
    if datetime.now() >= cutoff_time:
        flash('Sorry, the ordering window has closed for this baking day.')
        return redirect(url_for('order_page', share_link=share_link))
    
    name = request.form.get('name')
    phone = request.form.get('phone')
    
    # Get quantities for each bread type
    bread_orders = []
    total_quantity = 0
    
    # Parse the quantities from form data
    for key, value in request.form.items():
        if key.startswith('quantities[') and key.endswith(']'):
            bread_type_id = key[len('quantities['):-1]  # Extract bread_type_id from the field name
            quantity = int(value) if value.isdigit() else 0
            if quantity > 0:
                bread_orders.append({
                    'bread_type_id': bread_type_id,
                    'quantity': quantity
                })
                total_quantity += quantity
    
    if not name or not phone or not bread_orders:
        flash('Please fill in all required fields')
        return redirect(url_for('order_page', share_link=share_link))
    
    if total_quantity > 5:
        flash('Maximum 5 loaves total per order')
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
    save_order(baking_day['id'], name, phone, bread_orders)
    flash('Your order has been submitted successfully!')
    
    return redirect(url_for('order_page', share_link=share_link))

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

if __name__ == '__main__':
    # Create data files if they don't exist
    for filepath in [BREAD_TYPES_FILE, BAKING_DAYS_FILE, ORDERS_FILE]:
        if not os.path.exists(filepath):
            save_json_file(filepath, [])
    
    app.run(debug=True) 