import sqlite3
import json
from datetime import datetime

DB_NAME = 'bot_database.db'

def init_db():
    """إنشاء قاعدة البيانات والجداول"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # جدول المستخدمين
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            phone TEXT,
            balance REAL DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    # جدول الطلبات
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_id INTEGER,
            service_name TEXT,
            link TEXT,
            quantity INTEGER,
            price REAL,
            smm_order_id INTEGER,
            status TEXT DEFAULT 'Pending',
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # جدول المعاملات
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            type TEXT,
            reference TEXT,
            status TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id):
    """جلب بيانات المستخدم"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username):
    """إنشاء مستخدم جديد"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (user_id, username, balance, created_at) VALUES (?, ?, ?, ?)",
        (user_id, username, 0, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_balance(user_id):
    """جلب رصيد المستخدم"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_balance(user_id, amount):
    """تحديث رصيد المستخدم (إضافة أو خصم)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    return True

def save_order(user_id, service_id, service_name, link, quantity, price, smm_order_id):
    """حفظ طلب جديد"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (user_id, service_id, service_name, link, quantity, price, smm_order_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, service_id, service_name, link, quantity, price, smm_order_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_orders(user_id):
    """جلب طلبات المستخدم"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,)
    )
    orders = c.fetchall()
    conn.close()
    return orders

def log_transaction(user_id, amount, type, reference):
    """تسجيل معاملة مالية"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO transactions (user_id, amount, type, reference, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, type, reference, 'completed', datetime.now().isoformat()))
    conn.commit()
    conn.close()