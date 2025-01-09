# 🥖 Tom's Bakery - Order Management System

A modern, user-friendly web application for managing bread orders at Tom's Bakery. This system allows bakers to schedule baking days and customers to place orders for their favorite breads.

## ✨ Features

### For Bakers
- 📅 Schedule baking days with customizable bread types and quantities
- 📊 View order summaries and detailed customer orders
- 🔗 Generate unique sharing links for each baking day
- 📱 Easy WhatsApp sharing for order links
- 📈 Track available quantities and order status
- 🗑️ Manage bread types and baking days

### For Customers
- 🛒 Place orders for available breads (max 2 loaves per order)
- 📝 Save delivery information for future orders
- ⏰ Clear order deadlines (10 PM, two days before baking)
- ✅ Instant order confirmation
- 🔄 Double-booking prevention system

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/toms-bakery.git
cd toms-bakery
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Production Deployment

For production deployment, the application uses:
- Gunicorn as the WSGI server
- Docker for containerization
- Kamal for deployment management

To deploy:
```bash
kamal setup
kamal deploy
```

## 📁 Project Structure

```
toms-bakery/
├── app.py              # Main application file
├── data/               # JSON data storage
│   ├── bread_types.json
│   ├── baking_days.json
│   └── orders.json
├── templates/          # HTML templates
│   ├── base.html
│   ├── baker_home.html
│   ├── login.html
│   ├── manage_baking.html
│   ├── order_page.html
│   └── view_orders.html
├── Dockerfile         # Docker configuration
├── requirements.txt   # Python dependencies
└── gunicorn.conf.py  # Gunicorn configuration
```

## 💾 Data Storage

The application uses JSON files for data storage:
- `bread_types.json`: Available types of bread
- `baking_days.json`: Scheduled baking days and their details
- `orders.json`: Customer orders and their status

## 🔒 Security

- Password-protected baker interface
- Secure sharing links for orders
- Data validation and sanitization
- Protection against double-booking

## 🎨 UI Features

- Responsive design that works on all devices
- Bootstrap 5 for modern styling
- Interactive order form with real-time validation
- Clear success/error messages
- Progress bars for order tracking

## 📱 Mobile-First Approach

The application is designed with a mobile-first approach, ensuring a great user experience on:
- 📱 Smartphones
- 📱 Tablets
- 💻 Desktop computers

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Support

For support, please contact [your-email@example.com] 