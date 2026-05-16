# ============================================================
#   Coffee Time — app.py
#   Full Backend: Users + Orders + Contact Form
# ============================================================

# Flask imports — these are tools we need from the Flask library
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

# psycopg2 — this library lets Python talk to PostgreSQL database
import psycopg2

# werkzeug — this library helps us hash (scramble) passwords safely
from werkzeug.security import generate_password_hash, check_password_hash

# functools.wraps — needed to create our custom login_required decorator
from functools import wraps

import os  # For reading environment variables (like DATABASE_URL)

# ── 1. CREATE FLASK APP ──────────────────────────────────────────────────────

# Create the main Flask application object
app = Flask(__name__)

# Set the secret key for session management — this should be a long random string in production
app.secret_key = "coffee_time_secret" 

# Secret key — Flask uses this to encrypt session cookies
# Always change this to a long random string in production
app.secret_key = "coffeetime_secret_2025_change_me"

# ── 2. DATABASE CONNECTION ───────────────────────────────────────────────────
def get_db():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL)
    return conn


# ── 3. CREATE ALL TABLES ─────────────────────────────────────────────────────

def create_tables():
    """
    Creates all required tables in the database when the app starts.
    Uses IF NOT EXISTS so it won't crash if tables already exist.

    Tables created:
      1. users       — stores signup/login info
      2. orders      — stores each order a user places
      3. order_items — stores each item inside an order
      4. contacts    — stores contact form messages
    """

    # Open database connection
    conn = get_db()

    # Create a cursor object — we use this to run SQL commands
    cur = conn.cursor()

    # ── TABLE 1: users ──────────────────────────────────────────
    # Stores one row per registered user
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         SERIAL PRIMARY KEY,            -- Auto-incrementing unique user ID
            first_name VARCHAR(50)  NOT NULL,         -- User's first name (required)
            last_name  VARCHAR(50),                   -- User's last name (optional)
            email      VARCHAR(100) UNIQUE NOT NULL,  -- Email address, must be unique
            phone      VARCHAR(20),                   -- Phone number (optional)
            password   TEXT         NOT NULL,         -- Hashed password (never plain text)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- When they signed up
        )
    """)

    # ── TABLE 2: orders ─────────────────────────────────────────
    # Stores one row per order placed by a user
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id           SERIAL PRIMARY KEY,           -- Unique order ID
            user_id      INT REFERENCES users(id),     -- Which user placed this order
            user_email   VARCHAR(100),                 -- User's email (for quick lookup)
            total_amount NUMERIC(10, 2) DEFAULT 0,     -- Total price of the order (e.g. 450.00)
            status       VARCHAR(20) DEFAULT 'pending',-- Order status: pending/confirmed/delivered
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- When the order was placed
        )
    """)

    # ── TABLE 3: order_items ─────────────────────────────────────
    # Stores each individual item inside an order
    # One order can have many items (one-to-many relationship)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id         SERIAL PRIMARY KEY,             -- Unique item row ID
            order_id   INT REFERENCES orders(id),      -- Which order this item belongs to
            item_name  VARCHAR(100) NOT NULL,           -- Name of the coffee/food item
            item_price NUMERIC(10, 2) NOT NULL,         -- Price of one unit
            quantity   INT DEFAULT 1,                   -- How many of this item
            category   VARCHAR(50)                      -- Category: hot, cold, food, etc.
        )
    """)

    # ── TABLE 4: contacts ────────────────────────────────────────
    # Stores messages sent through the contact form
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id         SERIAL PRIMARY KEY,             -- Unique message ID
            name       VARCHAR(100) NOT NULL,          -- Sender's full name
            email      VARCHAR(100) NOT NULL,          -- Sender's email address
            subject    VARCHAR(200),                   -- Message subject/topic
            message    TEXT         NOT NULL,          -- The actual message content
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- When the message was sent
        )
    """)

    # Commit (save) all the table creations to the database
    conn.commit()

    # Close cursor and connection to free memory
    cur.close()
    conn.close()

    # Print success message in terminal
    print("✅ All database tables are ready.")
    print("   → users, orders, order_items, contacts")


# ── 4. LOGIN REQUIRED DECORATOR ──────────────────────────────────────────────

def login_required(f):
    """
    A protective wrapper for routes that need login.
    If someone tries to visit a protected page without logging in,
    they get redirected to /login automatically.

    How to use: just put @login_required above a route function.
    Example:
        @app.route("/account")
        @login_required
        def account():
            ...
    """

    # @wraps keeps the original function name intact (needed by Flask internally)
    @wraps(f)
    def decorated_function(*args, **kwargs):

        # Check the session dictionary for 'user_email'
        # If it's missing, the user has not logged in
        if "user_email" not in session and "user" not in session:

            # Not logged in → send them to the login page
            return redirect(url_for("login"))

        # Logged in → let them proceed to the actual page
        return f(*args, **kwargs)

    # Return the wrapped version of the function
    return decorated_function


# ── 5. HELPER: GET CURRENT LOGGED-IN USER ────────────────────────────────────

def get_current_user():
    # Google Login User
    if "user" in session:
        email = session["user"]["email"]
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, first_name, last_name, email, phone, created_at FROM users WHERE email = %s",
                (email,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return {
                    "id":         row[0],
                    "first_name": row[1],
                    "last_name":  row[2],
                    "email":      row[3],
                    "phone":      row[4],
                    "joined":     row[5],
                    "photo":      session["user"].get("photo", "")
                }
        except Exception as e:
            print(f"❌ Google user fetch error: {e}")
        return session["user"]  # fallback

    if "user_email" not in session:
        return None

    try:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, first_name, last_name, email, phone, created_at FROM users WHERE email = %s",
            (session["user_email"],)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {
                "id":         row[0],
                "first_name": row[1],
                "last_name":  row[2],
                "email":      row[3],
                "phone":      row[4],
                "joined":     row[5],
            }
    except Exception as e:
        print(f"❌ get_current_user error: {e}")
        return None

# ── 6. PUBLIC PAGES ───────────────────────────────────────────────────────────

# Home page — everyone can see this
@app.route("/")
def home():
    print(session.get("user"))
    user = get_current_user()  # Get logged-in user info (None if not logged in)
    return render_template("index.html", user=user)  # Pass user to template


# About Us page — everyone can see this
@app.route("/about")
def aboutus():
    user = get_current_user()
    return render_template("about.html", user=user)


# Menu page — everyone can see this
@app.route("/menu")
def menu():
    user = get_current_user()

    conn = get_db()
    cur = conn.cursor()

    # unique items fetch karo database se
    cur.execute("""
        SELECT DISTINCT ON (item_name)
               id, item_name, item_price,
               category, image_url, description
        FROM order_items
        ORDER BY item_name, id
    """)

    rows = cur.fetchall()

    menu_items = []
    for row in rows:
        menu_items.append({
            "id":          row[0],
            "name":        row[1],
            "price":       row[2],
            "category":    row[3],
            "image_url":   row[4] if row[4] else "",
            "description": row[5] if row[5] else "",
        })

    cur.close()
    conn.close()

    return render_template("menu.html", user=user, menu_items=menu_items)


# Specials page — everyone can see this
@app.route("/special")
def special():
    user = get_current_user()
    return render_template("specials.html", user=user)


# ── 7. SIGNUP ─────────────────────────────────────────────────────────────────

# Handles both GET (show form) and POST (submit form)
@app.route("/signup", methods=["GET", "POST"])
def signup():

    # If already logged in, no need to sign up again — go home
    if "user_email" in session:
        # signup hone ke baad thankyou page pe bhejo
        return redirect(url_for("thankyou"))

    # Form was submitted (user clicked Sign Up button)
    if request.method == "POST":

        # Read form fields — .strip() removes leading/trailing spaces
        first_name       = request.form.get("first_name", "").strip()
        last_name        = request.form.get("last_name",  "").strip()
        email            = request.form.get("email",      "").strip().lower()  # lowercase email
        phone            = request.form.get("phone",      "").strip()
        password         = request.form.get("password",         "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation 1: required fields must not be empty
        if not first_name or not email or not password:
            return render_template("signup.html", error="Please fill all required fields.")

        # Validation 2: both password fields must match
        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match! Please try again.")

        # Validation 3: password must be at least 8 characters
        if len(password) < 8:
            return render_template("signup.html", error="Password must be at least 8 characters long.")

        try:
            # Open database connection
            conn = get_db()
            cur  = conn.cursor()

            # Check if someone already registered with this email
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))

            if cur.fetchone():
                # Email already exists in database — reject registration
                cur.close()
                conn.close()
                return render_template("signup.html", error="Email already registered. Please login instead.")

            # Hash the password before saving — NEVER save plain text passwords
            # Example: "mypass123" → "pbkdf2:sha256:260000$abc...xyz"
            hashed_pw = generate_password_hash(password)

            # Insert the new user row into the users table
            cur.execute(
                """INSERT INTO users (first_name, last_name, email, phone, password)
                   VALUES (%s, %s, %s, %s, %s)""",
                (first_name, last_name, email, phone, hashed_pw)
            )

            # Commit saves the INSERT permanently to the database
            conn.commit()

            # Close connection — we're done writing
            cur.close()
            conn.close()

            # Save user info in session — this logs them in automatically
            session["user_email"] = email       # Used to identify the user
            session["user_name"]  = first_name  # Used to show their name in navbar

            # Terminal log for debugging
            print(f"✅ New signup: {first_name} {last_name} | {email}")

            session.clear()  # Clear session to log out the user after signup

            # Redirect to home page after successful signup
            return redirect(url_for("thankyou"))

        except Exception as e:
            print(f"❌ Signup error: {e}")
            return render_template("signup.html", error="Something went wrong. Please try again.")

    # GET request — just show the blank signup form
    return render_template("signup.html")


# ── 8. LOGIN ──────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():

    # Already logged in — no need to log in again
    if "user_email" in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        # Read submitted email and password
        email    = request.form.get("email",    "").strip().lower()
        password = request.form.get("password", "")

        # Both fields must be filled
        if not email or not password:
            return render_template("login.html", error="Please enter your email and password.")

        try:
            conn = get_db()
            cur  = conn.cursor()

            # Find the user with this email in the database
            cur.execute(
                "SELECT id, first_name, password FROM users WHERE email = %s",
                (email,)  # Parameterized query prevents SQL injection attacks
            )

            # Get the user row — returns None if email not found
            user = cur.fetchone()

            cur.close()
            conn.close()

            # check_password_hash compares the typed password with the stored hash
            if user and check_password_hash(user[2], password):

                # Correct credentials — create session to mark them as logged in
                session["user_email"] = email    # Store email
                session["user_name"]  = user[1]  # Store first name

                print(f"✅ Login: {email}")

                # Send to home page
                return redirect(url_for("home"))

            else:
                # Wrong email or password — don't reveal which one (security)
                return render_template("login.html",
                                       error="Invalid email or password. Please signup if you don't have an account.")

        except Exception as e:
            print(f"❌ Login error: {e}")
            return render_template("login.html", error="Something went wrong. Please try again.")

    # GET — show empty login form
    return render_template("login.html")

@app.route("/google-login", methods=["POST"])
def google_login():
    data = request.get_json()
    full_name = data["name"].split(" ", 1)
    first_name = full_name[0]
    last_name = full_name[1] if len(full_name) > 1 else ""
    email = data["email"]
    photo = data.get("photo", "")

    conn = get_db()
    cur = conn.cursor()

    # 1. Check if email exists
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    existing = cur.fetchone()

    # 2. Insert if not exists
    if not existing:
        cur.execute("""
            INSERT INTO users (first_name, last_name, email, password)
            VALUES (%s, %s, %s, %s)
        """, (first_name, last_name, email, "google_oauth"))
        conn.commit()

    cur.close()
    conn.close()

    # 3. Create session
    session["user"] = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "photo": photo
    }

    return jsonify({"message": "success"})


# ── 9. ACCOUNT PAGE (login required) ─────────────────────────────────────────

@app.route("/account")
@login_required  # Only logged-in users can visit this page
def account():

    # Get the full user profile from database
    user = get_current_user()

    # Safety check — if user not found, clear session and redirect
    if not user:
        session.clear()
        return redirect(url_for("login"))

    try:
        conn = get_db()
        cur  = conn.cursor()

        # Fetch all orders this user has placed
        # ORDER BY created_at DESC shows newest orders first
        cur.execute("""
            SELECT o.id, o.total_amount, o.status, o.created_at
            FROM orders o
            WHERE o.user_email = %s
            ORDER BY o.created_at ASC
        """, (user["email"],))

        # fetchall() returns a list of all matching rows
        order_rows = cur.fetchall()

        # Convert each row into a readable dictionary
        orders = []
        for row in order_rows:
            orders.append({
                "id":         row[0],  # Order ID
                "total":      row[1],  # Total price
                "status":     row[2],  # pending/confirmed/delivered
                "created_at": row[3],  # Order date
            })

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Account orders error: {e}")
        orders = []  # If error, show empty orders list

    # Render account page with user info and their orders
    return render_template("account.html", user=user, orders=orders)


# ── 10. ADD TO CART / PLACE ORDER ─────────────────────────────────────────────

@app.route("/add-to-cart", methods=["POST"])
@login_required  # Must be logged in to place order
def add_to_cart():
    """
    Called when user clicks 'Add +' button on the menu.
    Receives item details and saves them as an order in the database.
    """

    # Get the current logged-in user
    user = get_current_user()

    # Read the item data sent from the HTML button (as JSON)
    item_name  = request.form.get("item_name",  "")   # e.g. "Classic Espresso"
    item_price = request.form.get("item_price", 0)    # e.g. 180
    category   = request.form.get("category",  "")   # e.g. "hot"
    quantity   = request.form.get("quantity",   1)    # e.g. 1

    try:
        conn = get_db()
        cur  = conn.cursor()

        # Check if the user already has an open (pending) order
        cur.execute("""
            SELECT id FROM orders
            WHERE user_email = %s AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        """, (user["email"],))

        existing_order = cur.fetchone()  # Returns the order row, or None

        if existing_order:
            # User has an open order — add this item to it
            order_id = existing_order[0]  # Get the existing order's ID
        else:
            # No open order — create a brand new one
            cur.execute("""
                INSERT INTO orders (user_id, user_email, total_amount, status)
                VALUES (NULL, %s, 0, 'pending')
                RETURNING id
            """, (user["email"],))

            # RETURNING id gives us back the new order's ID
            order_id = cur.fetchone()[0]

        # Insert the item into order_items table linked to this order
        cur.execute("""
            INSERT INTO order_items (order_id, item_name, item_price, quantity, category)
            VALUES (%s, %s, %s, %s, %s)
        """, (order_id, item_name, float(item_price), int(quantity), category))

        # Update the total_amount in the orders table
        # This adds the item price to the running total
        cur.execute("""
            UPDATE orders
            SET total_amount = total_amount + %s
            WHERE id = %s
        """, (float(item_price) * int(quantity), order_id))

        # Save all changes to the database
        conn.commit()

        cur.close()
        conn.close()

        print(f"✅ Item added: {item_name} x{quantity} for {user['email']}")

        # Return success response to the browser (JavaScript reads this)
        return jsonify({"success": True, "message": f"{item_name} added to your order!"})

    except Exception as e:
        print(f"❌ Add to cart error: {e}")
        # Return error response to the browser
        return jsonify({"success": False, "message": "Could not add item. Please try again."})


# ── 11. VIEW CART / ORDER SUMMARY ─────────────────────────────────────────────

@app.route("/cart")
@login_required  # Must be logged in to view cart
def cart():
    """
    Shows the user their current pending order (cart) with all items.
    """

    # Get logged-in user info
    user = get_current_user()

    try:
        conn = get_db()
        cur  = conn.cursor()

        # Get the user's most recent pending order
        cur.execute("""
            SELECT id, total_amount, created_at FROM orders
            WHERE user_email = %s AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        """, (user["email"],))

        order_row = cur.fetchone()  # The pending order row

        cart_items = []    # List of items in the cart
        order_total = 0    # Running total price
        order_id = None    # ID of the pending order

        if order_row:
            order_id    = order_row[0]   # Order ID
            order_total = order_row[1]   # Total amount

            # Fetch all items inside this order
            cur.execute("""
                SELECT id, item_name, item_price, quantity, category
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))

            # Convert each row to a dictionary
            for row in cur.fetchall():
                cart_items.append({
                    "id":       row[0],                     # item id
                    "name":     row[1],                     # Item name
                    "price":    row[2],                     # Unit price
                    "quantity": row[3],                     # Quantity
                    "category": row[4],                     # Category
                    "subtotal": float(row[2]) * int(row[3]) # price × quantity
                })

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Cart error: {e}")
        cart_items  = []
        order_total = 0

    # Render the cart page with all items and total
    return render_template("cart.html",
                           user=user,
                           cart_items=cart_items,
                           order_total=order_total,
                           order_id=order_id)


@app.route("/update-cart", methods=["POST"])
def update_cart():

    if "user" not in session and "user_email" not in session:
        return redirect("/login")

    item_id = request.form.get("item_id")
    action = request.form.get("action")

    if not item_id:
        return jsonify({'error': 'item_id missing'}), 400
    item_id = int(item_id)

    conn = get_db()
    cur = conn.cursor()

    if action == "increase":

        cur.execute("""
            UPDATE order_items
            SET quantity = quantity + 1
            WHERE id = %s
        """, (item_id,))

    elif action == "decrease":

        cur.execute("""
            UPDATE order_items
            SET quantity = quantity - 1
            WHERE id = %s
        """, (item_id,))

        cur.execute("""
            DELETE FROM order_items
            WHERE id = %s AND quantity <= 0
        """, (item_id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/cart")


# ── 12. CONFIRM / PLACE ORDER ─────────────────────────────────────────────────

@app.route("/place-order/<int:order_id>", methods=["POST"])
@login_required  # Must be logged in
def place_order(order_id):
    """
    Confirms a pending order — changes its status from 'pending' to 'confirmed'.
    Called when user clicks 'Place Order' button on the cart page.
    """

    user = get_current_user()

    try:
        conn = get_db()
        cur  = conn.cursor()

        # Update the order status from 'pending' to 'confirmed'
        # Also check it belongs to this user (security)
        cur.execute("""
            UPDATE orders
            SET status = 'confirmed'
            WHERE id = %s AND user_email = %s AND status = 'pending'
        """, (order_id, user["email"]))

        # Commit the status change
        conn.commit()

        cur.close()
        conn.close()

        print(f"✅ Order #{order_id} confirmed for {user['email']}")

        # Redirect to account page to see order history
        return redirect(url_for("account"))

    except Exception as e:
        print(f"❌ Place order error: {e}")
        return redirect(url_for("cart"))
    
# Note: In a real app, you'd also want to handle payment processing here before confirming the order.
# checkout page
@app.route("/checkout")
@login_required
def checkout():
    user = get_current_user()

    conn = get_db()
    cur = conn.cursor()

    # pending order fetch karo
    cur.execute("""
        SELECT id, total_amount FROM orders
        WHERE user_email = %s AND status = 'pending'
        ORDER BY created_at DESC LIMIT 1
    """, (user["email"],))

    order = cur.fetchone()
    cur.close()
    conn.close()

    if not order:
        return redirect(url_for("cart"))

    return render_template("checkout.html",
                           user=user,
                           order_id=order[0],
                           total=order[1])


# apply discount code
@app.route("/apply-discount", methods=["POST"])
@login_required
def apply_discount():
    code = request.form.get("code", "").strip().upper()

    # simple discount codes
    discounts = {
        "COFFEE10": 10,   # 10% off
        "WELCOME20": 20,  # 20% off
        "SAVE50": 50,     # 50 rupees off flat
    }

    if code in discounts:
        return jsonify({
            "success": True,
            "discount": discounts[code],
            "message": f"Code applied! {discounts[code]}% off"
        })
    else:
        return jsonify({
            "success": False,
            "message": "Invalid discount code"
        })


# ── 13. CONTACT FORM ──────────────────────────────────────────────────────────

@app.route("/contact", methods=["GET", "POST"])
def contact():
    """
    Shows the contact form (GET) and saves the message to database (POST).
    Anyone can send a message — login not required.
    """

    # Get current user (None if not logged in — that's okay for contact)
    user = get_current_user()

    if request.method == "POST":

        # Read all fields from the submitted contact form
        name    = request.form.get("name",    "").strip()   # Sender's name
        email   = request.form.get("email",   "").strip()   # Sender's email
        subject = request.form.get("subject", "").strip()   # Message subject
        message = request.form.get("message", "").strip()   # Message body

        # Validate — name, email, and message are required
        if not name or not email or not message:
            return render_template("contact.html",
                                   user=user,
                                   error="Please fill in all required fields.")

        try:
            conn = get_db()
            cur  = conn.cursor()

            # Insert the contact message into the contacts table
            cur.execute("""
                INSERT INTO contacts (name, email, subject, message)
                VALUES (%s, %s, %s, %s)
            """, (name, email, subject, message))

            # Commit saves the message permanently
            conn.commit()

            cur.close()
            conn.close()

            print(f"✅ Contact message from: {name} | {email}")

            # Show contact page with a success message
            return render_template("contact.html",
                                   user=user,
                                   success="Thank you! Your message has been sent. We'll get back to you soon.")

        except Exception as e:
            print(f"❌ Contact form error: {e}")
            return render_template("contact.html",
                                   user=user,
                                   error="Something went wrong. Please try again.")

    # GET — show blank contact form
    return render_template("contact.html", user=user)


# ── 14. LOGOUT ────────────────────────────────────────────────────────────────

@app.route("/logout")
def logout():

    # session.clear() removes ALL keys from the session
    # This logs the user out — their cookie becomes empty
    session.clear()

    print("👋 User logged out.")

    # Send to home page after logout
    return redirect(url_for("home"))

@app.route("/update-phone", methods=["POST"])
@login_required
def update_phone():
    phone = request.form.get("phone", "").strip()
    user = get_current_user()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE users SET phone = %s WHERE email = %s", (phone, user["email"]))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/account")

@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")

#logout route from admin panel
@app.route('/admin/logout')
def admin_logout():
    session.pop("admin", None)
    return redirect('/admin/login')

# ✅ YAHAN LIKHO — admin logout ke neeche
# admin login
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin"):
        return redirect("/admin")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == "admin" and password == "coffee123":
            session["admin"] = True
            print("✅ Admin logged in!")
            return redirect("/admin")
        else:
            return render_template("admin/login.html",
                                   error="Wrong username or password!")
    return render_template("admin/login.html")

# Admin dashboard route
@app.route("/admin")
def admin_dashboard():

    # Check if admin is Logged in
    if not session.get("admin"):
        return redirect("/admin/login")
    
    conn = get_db()
    cur  = conn.cursor()

    # total users
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    # total orders
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]

    # total revenue
    cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'confirmed'")
    total_revenue = cur.fetchone()[0]

    #pending orders
    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = cur.fetchone()[0]

    cur.close()
    conn.close()

    #Send data to admin dashboard
    return render_template("admin/dashboard.html",
                           total_users=total_users,
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           pending_orders=pending_orders)

# admin orders page
@app.route("/admin/orders")
def admin_orders():

    # check karo admin logged in hai
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur = conn.cursor()

    # saare orders fetch karo — newest pehle
    cur.execute("""
        SELECT id, user_email, total_amount, status, created_at 
        FROM orders 
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    # har row ko dictionary mein convert karo
    orders = []
    for row in rows:
        orders.append({
            "id":         row[0],
            "email":      row[1],
            "total":      row[2],
            "status":     row[3],
            "created_at": row[4],
        })

    cur.close()
    conn.close()

    return render_template("admin/orders.html", orders=orders)

# show all menu items
# admin menu — admin ke liye
@app.route("/admin/menu")
def admin_menu():        # ← naya function
    if not session.get("admin"):
        return redirect("/admin/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, item_name, item_price, category, image_url
        FROM order_items
        GROUP BY id, item_name, item_price, category, image_url
        ORDER BY category
    """)
    rows = cur.fetchall()
    items = []
    for row in rows:
        items.append({
            "id":        row[0],
            "name":      row[1],
            "price":     row[2],
            "category":  row[3],
            "image_url": row[4] if row[4] else "",
        })
    cur.close()
    conn.close()
    return render_template("admin/menu.html", items=items)

# add new item to menu
@app.route("/admin/menu/add", methods=["POST"])
def admin_menu_add():

    if not session.get("admin"):
        return redirect("/admin/login")

    # get data from form
    item_name  = request.form.get("item_name", "").strip()
    item_price = request.form.get("item_price")
    category   = request.form.get("category")
    Image_url   = request.form.get("image_url", "").strip()  # New field for image URL

    conn = get_db()
    cur = conn.cursor()

    # insert new item into database
    cur.execute("""
        INSERT INTO order_items (order_id, item_name, item_price, category, quantity, image_url)
        VALUES (NULL, %s, %s, %s, 1, %s)
    """, (item_name, float(item_price), category, Image_url))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/menu")

# delete item from menu
@app.route("/admin/menu/delete/<int:item_id>")
def admin_menu_delete(item_id):

    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur = conn.cursor()

    # delete item by id
    cur.execute("DELETE FROM order_items WHERE id = %s", (item_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/menu")


# edit item price and name
@app.route("/admin/menu/edit/<int:item_id>", methods=["POST"])
def admin_menu_edit(item_id):

    if not session.get("admin"):
        return redirect("/admin/login")

    # get updated data from form
    item_name  = request.form.get("item_name", "").strip()
    item_price = request.form.get("item_price")
    image_url = request.form.get("image_url", "").strip()
    conn = get_db()
    cur = conn.cursor()

    # update item in database
    cur.execute("""
        UPDATE order_items
        SET item_name = %s, item_price = %s, image_url = %s
        WHERE id = %s
    """, (item_name, float(item_price), image_url, item_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/menu")

@app.route("/admin/contacts")
def admin_contacts():

    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur = conn.cursor()

    # id aur is_read bhi fetch karo
    cur.execute("""
        SELECT id, name, email, subject, message, created_at, is_read
        FROM contacts
        ORDER BY created_at ASC
    """)

    rows = cur.fetchall()

    messages = []
    for row in rows:
        messages.append({
            "id":         row[0],
            "name":       row[1],
            "email":      row[2],
            "subject":    row[3],
            "message":    row[4],
            "created_at": row[5],
            "is_read":    row[6],
        })

    cur.close()
    conn.close()

    return render_template("admin/contacts.html", messages=messages)


@app.route("/admin/contacts/delete/<int:msg_id>")
def admin_contacts_delete(msg_id):
    if not session.get("admin"):
        return redirect("/admin/login")
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM contacts WHERE id = %s",
        (msg_id,)
    )
    conn.commit()    # changes save karo
    cur.close()
    conn.close()

    return redirect("/admin/contacts")  # wapas contacts pe

@app.route("/admin/contacts/read/<int:msg_id>")
def admin_contacts_read(msg_id):
    if not session.get("admin"):
        return redirect("/admin/login")
    conn = get_db()
    cur = conn.cursor()

    # pehle dekho message read hai ya unread
    cur.execute(
        "SELECT is_read FROM contacts WHERE id = %s",
        (msg_id,)
    )
    current = cur.fetchone()[0]  # True ya False

    # agar read hai toh unread karo — agar unread hai toh read karo
    cur.execute(
        "UPDATE contacts SET is_read = %s WHERE id = %s",
        (not current, msg_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/contacts")  # wapas contacts pe


@app.route("/admin/users")
def admin_users():
    if not session.get("admin"):
        return redirect("/admin/login")
    
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, first_name, last_name, email, phone, created_at 
        FROM users 
        ORDER BY created_at ASC
    """)
    rows = cur.fetchall()
    users = []
    for row in rows:
        users.append({
            "id":         row[0],
            "first_name": row[1],
            "last_name":  row[2],
            "email":      row[3],
            "phone":      row[4],
            "joined":     row[5],
        })
    cur.close()
    conn.close()

    return render_template("admin/users.html", users=users)

# ── 15. RUN THE APP ───────────────────────────────────────────────────────────

# Ye Render pe bhi chalega
with app.app_context():
    create_tables()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))