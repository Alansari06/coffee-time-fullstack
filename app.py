# ============================================================
#   Coffee Time — app.py
#   Only routes — DB logic is in database.py
# ============================================================

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os

# import everything from our database file
from database import get_db, create_tables, login_required, get_current_user


# ── CREATE FLASK APP ─────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = "coffeetime_secret_2025_change_me"


# ── PUBLIC PAGES ─────────────────────────────────────────────────────────────

@app.route("/")
def home():
    user = get_current_user()
    return render_template("index.html", user=user)


@app.route("/about")
def aboutus():
    user = get_current_user()
    return render_template("about.html", user=user)


@app.route("/menu")
def menu():
    user = get_current_user()

    conn = get_db()
    cur = conn.cursor()

    # fetch unique menu items from database
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


@app.route("/special")
def special():
    user = get_current_user()
    return render_template("specials.html", user=user)


# ── SIGNUP ───────────────────────────────────────────────────────────────────

@app.route("/signup", methods=["GET", "POST"])
def signup():

    # already logged in — go to thankyou
    if "user_email" in session:
        return redirect(url_for("thankyou"))

    if request.method == "POST":

        first_name       = request.form.get("first_name", "").strip()
        last_name        = request.form.get("last_name",  "").strip()
        email            = request.form.get("email",      "").strip().lower()
        phone            = request.form.get("phone",      "").strip()
        password         = request.form.get("password",         "")
        confirm_password = request.form.get("confirm_password", "")

        # basic validation
        if not first_name or not email or not password:
            return render_template("signup.html", error="Please fill all required fields.")

        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match! Please try again.")

        if len(password) < 8:
            return render_template("signup.html", error="Password must be at least 8 characters long.")

        try:
            conn = get_db()
            cur  = conn.cursor()

            # check if email already exists
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template("signup.html", error="Email already registered. Please login instead.")

            # hash password before saving
            hashed_pw = generate_password_hash(password)

            cur.execute(
                """INSERT INTO users (first_name, last_name, email, phone, password)
                   VALUES (%s, %s, %s, %s, %s)""",
                (first_name, last_name, email, phone, hashed_pw)
            )
            conn.commit()
            cur.close()
            conn.close()

            print(f"✅ New signup: {first_name} {last_name} | {email}")

            session.clear()
            return redirect(url_for("thankyou"))

        except Exception as e:
            print(f"❌ Signup error: {e}")
            return render_template("signup.html", error="Something went wrong. Please try again.")

    return render_template("signup.html")


# ── LOGIN ────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_email" in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        email    = request.form.get("email",    "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="Please enter your email and password.")

        try:
            conn = get_db()
            cur  = conn.cursor()

            cur.execute(
                "SELECT id, first_name, password FROM users WHERE email = %s",
                (email,)
            )
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user and check_password_hash(user[2], password):
                session["user_email"] = email
                session["user_name"]  = user[1]
                print(f"✅ Login: {email}")
                return redirect(url_for("home"))
            else:
                return render_template("login.html",
                                       error="Invalid email or password. Please signup if you don't have an account.")

        except Exception as e:
            print(f"❌ Login error: {e}")
            return render_template("login.html", error="Something went wrong. Please try again.")

    return render_template("login.html")


# ── GOOGLE LOGIN ─────────────────────────────────────────────────────────────

@app.route("/google-login", methods=["POST"])
def google_login():
    data = request.get_json()
    full_name  = data["name"].split(" ", 1)
    first_name = full_name[0]
    last_name  = full_name[1] if len(full_name) > 1 else ""
    email      = data["email"]
    photo      = data.get("photo", "")

    conn = get_db()
    cur  = conn.cursor()

    # insert user if not already exists
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (first_name, last_name, email, password)
            VALUES (%s, %s, %s, %s)
        """, (first_name, last_name, email, "google_oauth"))
        conn.commit()

    cur.close()
    conn.close()

    session["user"] = {
        "first_name": first_name,
        "last_name":  last_name,
        "email":      email,
        "photo":      photo
    }

    return jsonify({"message": "success"})


# ── ACCOUNT PAGE ─────────────────────────────────────────────────────────────

@app.route("/account")
@login_required
def account():
    user = get_current_user()

    if not user:
        session.clear()
        return redirect(url_for("login"))

    try:
        conn = get_db()
        cur  = conn.cursor()

        cur.execute("""
            SELECT o.id, o.total_amount, o.status, o.created_at
            FROM orders o
            WHERE o.user_email = %s
            ORDER BY o.created_at ASC
        """, (user["email"],))

        orders = []
        for row in cur.fetchall():
            orders.append({
                "id":         row[0],
                "total":      row[1],
                "status":     row[2],
                "created_at": row[3],
            })

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Account orders error: {e}")
        orders = []

    return render_template("account.html", user=user, orders=orders)


# ── ADD TO CART ───────────────────────────────────────────────────────────────

@app.route("/add-to-cart", methods=["POST"])
@login_required
def add_to_cart():
    user = get_current_user()

    item_name  = request.form.get("item_name",  "")
    item_price = request.form.get("item_price", 0)
    category   = request.form.get("category",  "")
    quantity   = request.form.get("quantity",   1)

    try:
        conn = get_db()
        cur  = conn.cursor()

        # check if user already has a pending order
        cur.execute("""
            SELECT id FROM orders
            WHERE user_email = %s AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        """, (user["email"],))

        existing_order = cur.fetchone()

        if existing_order:
            order_id = existing_order[0]
        else:
            # create a new order
            cur.execute("""
                INSERT INTO orders (user_id, user_email, total_amount, status)
                VALUES (NULL, %s, 0, 'pending')
                RETURNING id
            """, (user["email"],))
            order_id = cur.fetchone()[0]

        # add item to order
        cur.execute("""
            INSERT INTO order_items (order_id, item_name, item_price, quantity, category)
            VALUES (%s, %s, %s, %s, %s)
        """, (order_id, item_name, float(item_price), int(quantity), category))

        # update order total
        cur.execute("""
            UPDATE orders
            SET total_amount = total_amount + %s
            WHERE id = %s
        """, (float(item_price) * int(quantity), order_id))

        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ Item added: {item_name} x{quantity} for {user['email']}")
        return jsonify({"success": True, "message": f"{item_name} added to your order!"})

    except Exception as e:
        print(f"❌ Add to cart error: {e}")
        return jsonify({"success": False, "message": "Could not add item. Please try again."})


# ── VIEW CART ────────────────────────────────────────────────────────────────

@app.route("/cart")
@login_required
def cart():
    user = get_current_user()

    try:
        conn = get_db()
        cur  = conn.cursor()

        cur.execute("""
            SELECT id, total_amount, created_at FROM orders
            WHERE user_email = %s AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        """, (user["email"],))

        order_row   = cur.fetchone()
        cart_items  = []
        order_total = 0
        order_id    = None

        if order_row:
            order_id    = order_row[0]
            order_total = order_row[1]

            cur.execute("""
                SELECT id, item_name, item_price, quantity, category
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))

            for row in cur.fetchall():
                cart_items.append({
                    "id":       row[0],
                    "name":     row[1],
                    "price":    row[2],
                    "quantity": row[3],
                    "category": row[4],
                    "subtotal": float(row[2]) * int(row[3])
                })

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Cart error: {e}")
        cart_items  = []
        order_total = 0

    return render_template("cart.html",
                           user=user,
                           cart_items=cart_items,
                           order_total=order_total,
                           order_id=order_id)


# ── UPDATE CART ───────────────────────────────────────────────────────────────

@app.route("/update-cart", methods=["POST"])
def update_cart():

    if "user" not in session and "user_email" not in session:
        return redirect("/login")

    item_id = request.form.get("item_id")
    action  = request.form.get("action")

    if not item_id:
        return jsonify({'error': 'item_id missing'}), 400

    item_id = int(item_id)
    conn = get_db()
    cur  = conn.cursor()

    if action == "increase":
        cur.execute("UPDATE order_items SET quantity = quantity + 1 WHERE id = %s", (item_id,))

    elif action == "decrease":
        cur.execute("UPDATE order_items SET quantity = quantity - 1 WHERE id = %s", (item_id,))
        cur.execute("DELETE FROM order_items WHERE id = %s AND quantity <= 0", (item_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/cart")


# ── PLACE ORDER ───────────────────────────────────────────────────────────────

@app.route("/place-order/<int:order_id>", methods=["POST"])
@login_required
def place_order(order_id):
    user = get_current_user()

    try:
        conn = get_db()
        cur  = conn.cursor()

        # change status from pending to confirmed
        cur.execute("""
            UPDATE orders
            SET status = 'confirmed'
            WHERE id = %s AND user_email = %s AND status = 'pending'
        """, (order_id, user["email"]))

        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ Order #{order_id} confirmed for {user['email']}")
        return redirect(url_for("account"))

    except Exception as e:
        print(f"❌ Place order error: {e}")
        return redirect(url_for("cart"))


# ── CHECKOUT (address form) ───────────────────────────────────────────────────

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user = get_current_user()

    conn = get_db()
    cur  = conn.cursor()

    # get latest pending order
    cur.execute("""
        SELECT id, total_amount FROM orders
        WHERE user_email = %s AND status = 'pending'
        ORDER BY created_at DESC LIMIT 1
    """, (user["email"],))

    order = cur.fetchone()

    if not order:
        cur.close()
        conn.close()
        return redirect(url_for("cart"))

    order_id = order[0]
    total    = order[1]

    if request.method == "POST":

        name     = request.form.get("name",     "").strip()
        phone    = request.form.get("phone",    "").strip()
        address  = request.form.get("address",  "").strip()
        landmark = request.form.get("landmark", "").strip()
        city     = request.form.get("city",     "").strip()
        pincode  = request.form.get("pincode",  "").strip()

        full_address = f"{address}, {landmark}, {city}, {pincode}"

        # use a new connection for POST to avoid conflicts
        conn2 = get_db()
        cur2  = conn2.cursor()

        cur2.execute("""
            UPDATE orders
            SET delivery_name    = %s,
                delivery_phone   = %s,
                delivery_address = %s
            WHERE id = %s
        """, (name, phone, full_address, order_id))

        conn2.commit()
        cur2.close()
        conn2.close()

        cur.close()
        conn.close()

        return redirect(url_for("payment", order_id=order_id))

    cur.close()
    conn.close()

    return render_template("checkout.html", user=user, order_id=order_id, total=total)


# ── PAYMENT PAGE ─────────────────────────────────────────────────────────────

@app.route("/payment", methods=["GET", "POST"])
@login_required
def payment():
    user = get_current_user()

    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, total_amount FROM orders
        WHERE user_email = %s AND status = 'pending'
        ORDER BY created_at DESC LIMIT 1
    """, (user["email"],))

    order = cur.fetchone()

    if not order:
        cur.close()
        conn.close()
        return redirect(url_for("cart"))

    order_id = order[0]
    total    = order[1]

    cur.close()
    conn.close()

    return render_template("payment.html", user=user, order_id=order_id, total=total)


# ── APPLY DISCOUNT ────────────────────────────────────────────────────────────

@app.route("/apply-discount", methods=["POST"])
@login_required
def apply_discount():
    code = request.form.get("code", "").strip().upper()

    # available discount codes
    discounts = {
        "COFFEE10":  10,
        "WELCOME20": 20,
        "SAVE50":    50,
    }

    if code in discounts:
        return jsonify({
            "success":  True,
            "discount": discounts[code],
            "message":  f"Code applied! {discounts[code]}% off"
        })
    else:
        return jsonify({"success": False, "message": "Invalid discount code"})


# ── CONTACT FORM ──────────────────────────────────────────────────────────────

@app.route("/contact", methods=["GET", "POST"])
def contact():
    user = get_current_user()

    if request.method == "POST":

        name    = request.form.get("name",    "").strip()
        email   = request.form.get("email",   "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            return render_template("contact.html", user=user, error="Please fill in all required fields.")

        try:
            conn = get_db()
            cur  = conn.cursor()

            cur.execute("""
                INSERT INTO contacts (name, email, subject, message)
                VALUES (%s, %s, %s, %s)
            """, (name, email, subject, message))

            conn.commit()
            cur.close()
            conn.close()

            print(f"✅ Contact message from: {name} | {email}")
            return render_template("contact.html", user=user,
                                   success="Thank you! Your message has been sent. We'll get back to you soon.")

        except Exception as e:
            print(f"❌ Contact form error: {e}")
            return render_template("contact.html", user=user, error="Something went wrong. Please try again.")

    return render_template("contact.html", user=user)


# ── LOGOUT ────────────────────────────────────────────────────────────────────

@app.route("/logout")
def logout():
    session.clear()
    print("👋 User logged out.")
    return redirect(url_for("home"))


# ── UPDATE PHONE ──────────────────────────────────────────────────────────────

@app.route("/update-phone", methods=["POST"])
@login_required
def update_phone():
    phone = request.form.get("phone", "").strip()
    user  = get_current_user()

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("UPDATE users SET phone = %s WHERE email = %s", (phone, user["email"]))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/account")


# ── THANK YOU PAGE ────────────────────────────────────────────────────────────

@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")


# ── ADMIN LOGOUT ──────────────────────────────────────────────────────────────

@app.route('/admin/logout')
def admin_logout():
    session.pop("admin", None)
    return redirect('/admin/login')


# ── ADMIN LOGIN ───────────────────────────────────────────────────────────────

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
            return render_template("admin/login.html", error="Wrong username or password!")

    return render_template("admin/login.html")


# ── ADMIN DASHBOARD ───────────────────────────────────────────────────────────

@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'confirmed'")
    total_revenue = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template("admin/dashboard.html",
                           total_users=total_users,
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           pending_orders=pending_orders)


# ── ADMIN ORDERS ──────────────────────────────────────────────────────────────

@app.route("/admin/orders")
def admin_orders():
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, user_email, total_amount, status, created_at,
               delivery_name, delivery_phone, delivery_address
        FROM orders
        ORDER BY created_at DESC
    """)

    orders = []
    for row in cur.fetchall():
        orders.append({
            "id":          row[0],
            "email":       row[1],
            "total":       row[2],
            "status":      row[3],
            "created_at":  row[4],
            "del_name":    row[5] or "—",
            "del_phone":   row[6] or "—",
            "del_address": row[7] or "—",
        })

    cur.close()
    conn.close()

    return render_template("admin/orders.html", orders=orders)


# ── ADMIN ORDER STATUS UPDATE ─────────────────────────────────────────────────

@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
def admin_order_status(order_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    new_status = request.form.get("status")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/orders")


# ── ADMIN MENU ────────────────────────────────────────────────────────────────

@app.route("/admin/menu")
def admin_menu():
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, item_name, item_price, category, image_url
        FROM order_items
        GROUP BY id, item_name, item_price, category, image_url
        ORDER BY category
    """)

    items = []
    for row in cur.fetchall():
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


# ── ADMIN MENU ADD ────────────────────────────────────────────────────────────

@app.route("/admin/menu/add", methods=["POST"])
def admin_menu_add():
    if not session.get("admin"):
        return redirect("/admin/login")

    item_name  = request.form.get("item_name",  "").strip()
    item_price = request.form.get("item_price")
    category   = request.form.get("category")
    image_url  = request.form.get("image_url",  "").strip()

    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        INSERT INTO order_items (order_id, item_name, item_price, category, quantity, image_url)
        VALUES (NULL, %s, %s, %s, 1, %s)
    """, (item_name, float(item_price), category, image_url))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/menu")


# ── ADMIN MENU DELETE ─────────────────────────────────────────────────────────

@app.route("/admin/menu/delete/<int:item_id>")
def admin_menu_delete(item_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM order_items WHERE id = %s", (item_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/menu")


# ── ADMIN MENU EDIT ───────────────────────────────────────────────────────────

@app.route("/admin/menu/edit/<int:item_id>", methods=["POST"])
def admin_menu_edit(item_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    item_name  = request.form.get("item_name",  "").strip()
    item_price = request.form.get("item_price")
    image_url  = request.form.get("image_url",  "").strip()

    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        UPDATE order_items
        SET item_name = %s, item_price = %s, image_url = %s
        WHERE id = %s
    """, (item_name, float(item_price), image_url, item_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/menu")


# ── ADMIN CONTACTS ────────────────────────────────────────────────────────────

@app.route("/admin/contacts")
def admin_contacts():
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, name, email, subject, message, created_at, is_read
        FROM contacts
        ORDER BY created_at ASC
    """)

    messages = []
    for row in cur.fetchall():
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


# ── ADMIN CONTACTS DELETE ─────────────────────────────────────────────────────

@app.route("/admin/contacts/delete/<int:msg_id>")
def admin_contacts_delete(msg_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM contacts WHERE id = %s", (msg_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/contacts")


# ── ADMIN CONTACTS READ/UNREAD ────────────────────────────────────────────────

@app.route("/admin/contacts/read/<int:msg_id>")
def admin_contacts_read(msg_id):
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur  = conn.cursor()

    # toggle read/unread
    cur.execute("SELECT is_read FROM contacts WHERE id = %s", (msg_id,))
    current = cur.fetchone()[0]

    cur.execute("UPDATE contacts SET is_read = %s WHERE id = %s", (not current, msg_id))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/admin/contacts")


# ── ADMIN USERS ───────────────────────────────────────────────────────────────

@app.route("/admin/users")
def admin_users():
    if not session.get("admin"):
        return redirect("/admin/login")

    conn = get_db()
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, first_name, last_name, email, phone, created_at
        FROM users
        ORDER BY created_at ASC
    """)

    users = []
    for row in cur.fetchall():
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


# ── RUN THE APP ───────────────────────────────────────────────────────────────

with app.app_context():
    create_tables()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))