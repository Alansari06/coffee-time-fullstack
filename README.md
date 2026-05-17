# ☕ Coffee Time — Full Stack Web App

> A modern, fully functional coffee shop ordering system built with Flask & PostgreSQL.

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?style=flat&logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=flat&logo=postgresql)
![Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=flat&logo=render)

**Live Demo →** [coffee-time-fullstack.onrender.com](https://coffee-time-fullstack.onrender.com)

---

## 📸 Screenshots

| Home | Menu | Cart |
|------|------|------|
| ![Home](home.png) | ![Menu](menu.png) | ![cart](cart.png) |

| Checkout | Account | Admin |
|----------|---------|-------|
| ![Checkout](checkout.png) | ![Account](account.png) | ![Admin](admin.png) |

---

## ✨ Features

### 👤 User Side
- 🔐 **Signup & Login** — secure authentication with hashed passwords
- 🔵 **Google OAuth Login** — one-click sign in with Google
- 🛒 **Add to Cart** — add multiple items, adjust quantity
- 📦 **Order Tracking** — view all past orders with status
- 💳 **Checkout Flow** — delivery address → payment
- 📍 **GPS Location** — auto-fill delivery address using current location
- 💸 **Discount Codes** — apply promo codes at checkout (COFFEE10, WELCOME20, SAVE50)
- 💵 **Multiple Payment Methods** — Card, UPI, Cash on Delivery

### 🔧 Admin Panel (`/admin`)
- 📊 **Dashboard** — total users, orders, revenue, pending orders
- 📦 **Orders Management** — view all orders with delivery details, update status
- 🍵 **Menu Management** — add, edit, delete menu items with images
- 👥 **Users List** — view all registered users
- ✉️ **Contact Messages** — read/unread, delete messages

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| Database | PostgreSQL (psycopg2) |
| Frontend | HTML, CSS, Jinja2 |
| Auth | Werkzeug (password hashing), Google OAuth |
| Hosting | Render |
| Version Control | Git & GitHub |

---

## 📁 Project Structure

```
coffee-time/
│
├── app.py              # All Flask routes
├── database.py         # DB connection, table creation, helpers
├── requirements.txt    # Python dependencies
│
└── templates/
    ├── index.html      # Home page
    ├── menu.html       # Menu page
    ├── cart.html       # Cart page
    ├── checkout.html   # Delivery address form
    ├── payment.html    # Payment page
    ├── account.html    # User account & orders
    ├── login.html      # Login page
    ├── signup.html     # Signup page
    ├── contact.html    # Contact form
    ├── about.html      # About us page
    ├── specials.html   # Special offers
    ├── thankyou.html   # Thank you page
    └── admin/
        ├── base.html       # Admin layout
        ├── dashboard.html  # Admin dashboard
        ├── orders.html     # Orders management
        ├── menu.html       # Menu management
        ├── users.html      # Users list
        ├── contacts.html   # Contact messages
        └── login.html      # Admin login
```

---

## 🚀 Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/Alansari06/coffee-time-fullstack.git
cd coffee-time-fullstack

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variable
set DATABASE_URL=your_postgresql_url    # Windows
export DATABASE_URL=your_postgresql_url # Mac/Linux

# 5. Run the app
python app.py
```

---

## 🔑 Admin Access

```
URL:      /admin/login
Username: admin
Password: coffee123
```

---

## 💰 Discount Codes

| Code | Discount |
|------|----------|
| COFFEE10 | 10% off |
| WELCOME20 | 20% off |
| SAVE50 | 50% off |

---

## 🗄️ Database Tables

| Table | Purpose |
|-------|---------|
| `users` | Registered users |
| `orders` | Customer orders with delivery info |
| `order_items` | Items inside each order |
| `contacts` | Contact form messages |

---

## 👨‍💻 Developer

**Anas Ansari** — Full Stack Developer

> Built with ☕ & passion in Cleveland style!
