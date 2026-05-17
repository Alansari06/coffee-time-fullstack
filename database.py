# ============================================================
#   Coffee Time — database.py
#   DB connection, table creation, and helper functions
# ============================================================

import os
import psycopg2
from functools import wraps
from flask import session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash


# ── 1. DATABASE CONNECTION ───────────────────────────────────────────────────

def get_db():
    # Read the database URL from environment variable
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL)
    return conn


# ── 2. CREATE ALL TABLES ─────────────────────────────────────────────────────

def create_tables():
    # Creates all required tables when the app starts
    # Uses IF NOT EXISTS so it won't crash if tables already exist

    conn = get_db()
    cur = conn.cursor()

    # TABLE 1: users — stores signup/login info
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         SERIAL PRIMARY KEY,
            first_name VARCHAR(50)  NOT NULL,
            last_name  VARCHAR(50),
            email      VARCHAR(100) UNIQUE NOT NULL,
            phone      VARCHAR(20),
            password   TEXT         NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # TABLE 2: orders — stores each order a user places
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id               SERIAL PRIMARY KEY,
            user_id          INT REFERENCES users(id),
            user_email       VARCHAR(100),
            total_amount     NUMERIC(10, 2) DEFAULT 0,
            status           VARCHAR(20) DEFAULT 'pending',
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delivery_name    TEXT,
            delivery_phone   TEXT,
            delivery_address TEXT
        )
    """)

    # TABLE 3: order_items — stores each item inside an order
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id         SERIAL PRIMARY KEY,
            order_id   INT REFERENCES orders(id),
            item_name  VARCHAR(100) NOT NULL,
            item_price NUMERIC(10, 2) NOT NULL,
            quantity   INT DEFAULT 1,
            category   VARCHAR(50),
            image_url  TEXT,
            description TEXT
        )
    """)

    # TABLE 4: contacts — stores contact form messages
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id         SERIAL PRIMARY KEY,
            name       VARCHAR(100) NOT NULL,
            email      VARCHAR(100) NOT NULL,
            subject    VARCHAR(200),
            message    TEXT         NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read    BOOLEAN DEFAULT FALSE
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ All database tables are ready.")
    print("   → users, orders, order_items, contacts")


# ── 3. LOGIN REQUIRED DECORATOR ──────────────────────────────────────────────

def login_required(f):
    # Protects routes — redirects to login if user is not logged in
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_email" not in session and "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ── 4. GET CURRENT LOGGED-IN USER ────────────────────────────────────────────

def get_current_user():
    # Returns user dict if logged in, None if not

    # Google login user
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

    # Normal login user
    if "user_email" not in session:
        return None

    try:
        conn = get_db()
        cur = conn.cursor()
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
