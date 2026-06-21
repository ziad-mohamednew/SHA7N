import asyncio
import re
import requests
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events, Button

# ============================================
# الإعدادات
# ============================================

BOT_TOKEN = "8858529708:AAHmGQhODiDrJ-vhjgzGipgPpVAzXMNb7Lo"  # غير ده
SMM_API_KEY = "YOUR_SMM_API_KEY_HERE"  # غير ده
SMM_API_URL = "https://smmbasha.com/api/v2"

WALLET_NUMBERS = {
    "vodafone": "01012345678",
    "orange": "01012345678",
    "we": "01012345678",
    "etisalat": "01012345678"
}

# ============================================
# قاعدة البيانات
# ============================================

DB_NAME = 'bot_database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            created_at TEXT
        )
    ''')
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
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            type TEXT,
            reference TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO users (user_id, username, balance, created_at) VALUES (?, ?, ?, ?)",
        (user_id, username, 0, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def save_order(user_id, service_id, service_name, link, quantity, price, smm_order_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (user_id, service_id, service_name, link, quantity, price, smm_order_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, service_id, service_name, link, quantity, price, smm_order_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_user_orders(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 20", (user_id,))
    orders = c.fetchall()
    conn.close()
    return orders

def log_transaction(user_id, amount, type, reference):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO transactions (user_id, amount, type, reference, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, type, reference, 'completed', datetime.now().isoformat()))
    conn.commit()
    conn.close()

init_db()

# ============================================
# دوال API
# ============================================

def call_smm_api(action, extra_data=None):
    data = {'key': SMM_API_KEY, 'action': action}
    if extra_data:
        data.update(extra_data)
    try:
        response = requests.post(SMM_API_URL, data=data, timeout=30)
        return response.json()
    except:
        return {'error': 'فشل الاتصال بالـ API'}

def format_price(price):
    return f"{price:.2f} جنيه"

def format_order_status(status):
    status_map = {
        'Pending': '⏳ قيد الانتظار',
        'In progress': '🔄 قيد التنفيذ',
        'Completed': '✅ مكتمل',
        'Partial': '⚠️ جزئي',
        'Cancelled': '❌ ملغي'
    }
    return status_map.get(status, status)

# ============================================
# البوت
# ============================================

bot = TelegramClient('bot', api_id=0, api_hash='').start(bot_token=BOT_TOKEN)

# تخزين حالة المستخدمين
user_state = {}

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    user_id = event.sender_id
    username = event.sender.username or 'مستخدم'
    if not get_user(user_id):
        create_user(user_id, username)
    
    buttons = [
        [Button.text('📦 الخدمات', resize=True)],
        [Button.text('💰 رصيدي'), Button.text('🔄 طلب جديد')],
        [Button.text('📋 طلباتي'), Button.text('💳 شحن الرصيد')],
        [Button.text('🆘 مساعدة')]
    ]
    await event.respond(
        "🌟 أهلاً بك في خدمة الباشا!\n\n"
        "📦 الخدمات المتاحة:\n"
        "- متابعين\n- إعجابات\n- مشاهدات\n- تعليقات\n\n"
        "💰 اشحن رصيدك عبر محافظ الهاتف\n\n"
        "📌 استخدم الأزرار أدناه للتنقل",
        buttons=buttons
    )

@bot.on(events.NewMessage(pattern='/services|📦 الخدمات'))
async def services_handler(event):
    services = call_smm_api('services')
    if not services or 'error' in services:
        await event.respond('❌ حدث خطأ في جلب الخدمات')
        return
    message = "📦 **قائمة الخدمات:**\n\n"
    for service in services[:10]:
        message += f"🔹 {service['name']}\n"
        message += f"   🆔 {service['service']}\n"
        message += f"   💰 {format_price(service['rate'])} لكل 1000\n"
        message += f"   📊 الحد: {service['min']} - {service['max']}\n\n"
    await event.respond(message)

@bot.on(events.NewMessage(pattern='/balance|💰 رصيدي'))
async def balance_handler(event):
    user_id = event.sender_id
    balance = get_balance(user_id)
    await event.respond(f"💰 **رصيدك الحالي:**\n{format_price(balance)}")

@bot.on(events.NewMessage(pattern='/order|🔄 طلب جديد'))
async def order_start_handler(event):
    services = call_smm_api('services')
    if not services or 'error' in services:
        await event.respond('❌ حدث خطأ في جلب الخدمات')
        return
    buttons = []
    for service in services[:10]:
        buttons.append([Button.inline(
            f"{service['name']}",
            data=f"service_{service['service']}"
        )])
    await event.respond(
        "🔄 **اختر الخدمة:**",
        buttons=buttons
    )

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    
    if data.startswith('service_'):
        service_id = data.split('_')[1]
        user_state[user_id] = {'service_id': service_id, 'step': 'link'}
        await event.edit(
            f"✅ تم اختيار الخدمة\n\n"
            f"📌 **أدخل الرابط:**\n"
            f"مثال: https://tiktok.com/@username"
        )

@bot.on(events.NewMessage(pattern='/orders|📋 طلباتي'))
async def orders_handler(event):
    user_id = event.sender_id
    orders = get_user_orders(user_id)
    if not orders:
        await event.respond('📭 لا توجد طلبات')
        return
    message = "📋 **طلباتك:**\n\n"
    for order in orders[:10]:
        message += f"🔹 #{order[0]} - {order[3]}\n"
        message += f"   الكمية: {order[5]}\n"
        message += f"   السعر: {format_price(order[6])}\n"
        message += f"   الحالة: {format_order_status(order[8])}\n\n"
    await event.respond(message)

@bot.on(events.NewMessage(pattern='/recharge|💳 شحن الرصيد'))
async def recharge_handler(event):
    message = f"""
💳 **شحن الرصيد**

📱 قم بتحويل المبلغ على:

🏦 فودافون كاش: {WALLET_NUMBERS['vodafone']}
🏦 أورنج كاش: {WALLET_NUMBERS['orange']}
🏦 وي كاش: {WALLET_NUMBERS['we']}
🏦 اتصالات كاش: {WALLET_NUMBERS['etisalat']}

⚠️ بعد التحويل، ارسل:
"حولت 50 جنيه من 01012345678"
"""
    await event.respond(message)

@bot.on(events.NewMessage(pattern='/help|🆘 مساعدة'))
async def help_handler(event):
    await event.respond(
        "🆘 **طريقة الاستخدام:**\n\n"
        "1️⃣ /balance - عرض رصيدك\n"
        "2️⃣ /services - عرض الخدمات\n"
        "3️⃣ /order - طلب خدمة جديدة\n"
        "4️⃣ /recharge - شحن الرصيد\n"
        "5️⃣ /orders - عرض طلباتك"
    )

@bot.on(events.NewMessage)
async def text_handler(event):
    text = event.raw_text
    user_id = event.sender_id
    
    # معالجة خطوات الطلب
    if user_id in user_state:
        state = user_state[user_id]
        step = state.get('step')
        
        if step == 'link':
            user_state[user_id]['link'] = text
            user_state[user_id]['step'] = 'quantity'
            await event.respond("📌 **أدخل الكمية:**\nمثال: 1000")
            return
        
        elif step == 'quantity':
            try:
                quantity = int(text)
                if quantity <= 0:
                    await event.respond('❌ الكمية يجب أن تكون أكبر من 0')
                    return
                
                service_id = user_state[user_id]['service_id']
                link = user_state[user_id]['link']
                
                services = call_smm_api('services')
                selected = None
                for service in services:
                    if str(service['service']) == service_id:
                        selected = service
                        break
                
                if selected:
                    price = selected['rate'] * quantity
                    balance = get_balance(user_id)
                    
                    if balance < price:
                        await event.respond(
                            f"❌ رصيد غير كافي!\n"
                            f"المطلوب: {format_price(price)}\n"
                            f"رصيدك: {format_price(balance)}"
                        )
                        del user_state[user_id]
                        return
                    
                    update_balance(user_id, -price)
                    result = call_smm_api('add', {
                        'service': service_id,
                        'link': link,
                        'quantity': quantity
                    })
                    
                    if 'order' in result:
                        save_order(user_id, service_id, selected['name'],
                                 link, quantity, price, result['order'])
                        log_transaction(user_id, price, 'order', result['order'])
                        await event.respond(
                            f"✅ **تم الطلب بنجاح!**\n"
                            f"🆔 رقم الطلب: {result['order']}\n"
                            f"💰 السعر: {format_price(price)}"
                        )
                    else:
                        update_balance(user_id, price)
                        await event.respond('❌ فشل الطلب، تم استرجاع الرصيد')
                    
                    del user_state[user_id]
            except ValueError:
                await event.respond('❌ يرجى إدخال رقم صحيح')
            return
    
    # معالجة الشحن
    if 'حولت' in text or 'تحويل' in text:
        amount_match = re.search(r'(\d+)\s*جنيه', text)
        phone_match = re.search(r'(01[0-9]{9})', text)
        if amount_match and phone_match:
            amount = float(amount_match.group(1))
            phone = phone_match.group(1)
            update_balance(user_id, amount)
            log_transaction(user_id, amount, 'deposit', phone)
            await event.respond(
                f"✅ **تم الشحن بنجاح!**\n"
                f"💰 المبلغ: {format_price(amount)}\n"
                f"💰 رصيدك الجديد: {format_price(get_balance(user_id))}"
            )
        else:
            await event.respond(
                "⚠️ استخدم الصيغة:\n"
                "حولت 50 جنيه من 01012345678"
            )

# ============================================
# تشغيل البوت
# ============================================

async def main():
    print("🤖 البوت شغال...")
    await bot.start()
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
