import asyncio
import json
import requests
from telethon import TelegramClient, events, Button
from datetime import datetime
import config
import database

# تهيئة قاعدة البيانات
database.init_db()

# تهيئة البوت
bot = TelegramClient('bot', api_id=0, api_hash='').start(bot_token=config.BOT_TOKEN)

# ============================================
# دوال مساعدة
# ============================================

def call_smm_api(action, extra_data=None):
    """الاتصال بـ SMMBasha API"""
    data = {
        'key': config.SMM_API_KEY,
        'action': action
    }
    if extra_data:
        data.update(extra_data)
    
    try:
        response = requests.post(config.SMM_API_URL, data=data, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ خطأ في API: {e}")
        return {'error': str(e)}

def format_price(price):
    """تنسيق السعر"""
    return f"{price:.2f} جنيه"

def format_order_status(status):
    """تنسيق حالة الطلب"""
    status_map = {
        'Pending': '⏳ قيد الانتظار',
        'In progress': '🔄 قيد التنفيذ',
        'Completed': '✅ مكتمل',
        'Partial': '⚠️ جزئي',
        'Cancelled': '❌ ملغي'
    }
    return status_map.get(status, status)

# ============================================
# أوامر البوت
# ============================================

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """بدء البوت"""
    user_id = event.sender_id
    username = event.sender.username or 'مستخدم'
    
    # التحقق من وجود المستخدم
    if not database.get_user(user_id):
        database.create_user(user_id, username)
    
    # زر البدء
    buttons = [
        [Button.text('📦 الخدمات', resize=True)],
        [Button.text('💰 رصيدي'), Button.text('🔄 طلب جديد')],
        [Button.text('📋 طلباتي'), Button.text('💳 شحن الرصيد')],
        [Button.text('🆘 مساعدة')]
    ]
    
    await event.respond(
        config.WELCOME_MESSAGE,
        buttons=buttons
    )

@bot.on(events.NewMessage(pattern='/services|📦 الخدمات'))
async def services_handler(event):
    """عرض الخدمات"""
    user_id = event.sender_id
    
    # جلب الخدمات من SMMBasha
    services = call_smm_api('services')
    
    if not services or 'error' in services:
        await event.respond('❌ حدث خطأ في جلب الخدمات')
        return
    
    # عرض أول 10 خدمات
    message = "📦 **قائمة الخدمات:**\n\n"
    for service in services[:10]:
        message += f"🔹 **{service['name']}**\n"
        message += f"   🆔 {service['service']}\n"
        message += f"   💰 {format_price(service['rate'])} لكل 1000\n"
        message += f"   📊 الحد الأدنى: {service['min']} - الحد الأقصى: {service['max']}\n\n"
    
    message += "\n📌 لطلب خدمة استخدم /order"
    
    await event.respond(message)

@bot.on(events.NewMessage(pattern='/balance|💰 رصيدي'))
async def balance_handler(event):
    """عرض الرصيد"""
    user_id = event.sender_id
    balance = database.get_balance(user_id)
    
    await event.respond(
        f"💰 **رصيدك الحالي:**\n"
        f"{format_price(balance)}\n\n"
        f"📌 لشحن الرصيد استخدم /recharge"
    )

@bot.on(events.NewMessage(pattern='/order|🔄 طلب جديد'))
async def order_start_handler(event):
    """بدء طلب جديد"""
    user_id = event.sender_id
    
    # جلب الخدمات
    services = call_smm_api('services')
    
    if not services or 'error' in services:
        await event.respond('❌ حدث خطأ في جلب الخدمات')
        return
    
    # إنشاء أزرار للخدمات
    buttons = []
    for service in services[:10]:
        buttons.append([Button.inline(
            f"{service['name']} - {format_price(service['rate'])}",
            data=f"service_{service['service']}"
        )])
    
    await event.respond(
        "🔄 **اختر الخدمة المطلوبة:**\n"
        "اضغط على الزر المناسب",
        buttons=buttons
    )

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    """معالجة الأزرار"""
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    
    if data.startswith('service_'):
        # اختيار الخدمة
        service_id = data.split('_')[1]
        
        # حفظ الخدمة في الجلسة
        event.session_data = {'service_id': service_id}
        
        await event.edit(
            "🔄 **أدخل الرابط المطلوب:**\n"
            "مثال: https://tiktok.com/@username"
        )
        # انتظار إدخال الرابط
        # (سيتم التعامل معه في handler منفصل)

@bot.on(events.NewMessage(pattern='/orders|📋 طلباتي'))
async def orders_handler(event):
    """عرض الطلبات"""
    user_id = event.sender_id
    orders = database.get_user_orders(user_id)
    
    if not orders:
        await event.respond('📭 **لا توجد طلبات بعد**\nاستخدم /order لطلب خدمة')
        return
    
    message = "📋 **طلباتك الأخيرة:**\n\n"
    for order in orders[:10]:
        message += f"🔹 **#{order[0]}** - {order[3]}\n"
        message += f"   الكمية: {order[5]}\n"
        message += f"   السعر: {format_price(order[6])}\n"
        message += f"   الحالة: {format_order_status(order[8])}\n"
        message += f"   📅 {order[9][:10]}\n\n"
    
    await event.respond(message)

@bot.on(events.NewMessage(pattern='/recharge|💳 شحن الرصيد'))
async def recharge_handler(event):
    """شحن الرصيد"""
    user_id = event.sender_id
    
    message = f"""
💳 **شحن الرصيد**

📱 قم بتحويل المبلغ على أحد الأرقام التالية:

🏦 **فودافون كاش:** {config.WALLET_NUMBERS['vodafone']}
🏦 **أورنج كاش:** {config.WALLET_NUMBERS['orange']}
🏦 **وي كاش:** {config.WALLET_NUMBERS['we']}
🏦 **اتصالات كاش:** {config.WALLET_NUMBERS['etisalat']}

⚠️ **تعليمات مهمة:**
1️⃣ أرسل المبلغ على أي رقم من الأرقام أعلاه
2️⃣ بعد التحويل، ارسل رسالة تحتوي على:
   - المبلغ المحول
   - رقم هاتفك المسجل في البوت
  
📌 مثال: "حولت 50 جنيه من 01012345678"

✅ سيتم إضافة الرصيد تلقائياً خلال دقائق
"""
    
    await event.respond(message)

@bot.on(events.NewMessage(pattern='/help|🆘 مساعدة'))
async def help_handler(event):
    """رسالة المساعدة"""
    await event.respond(config.HELP_MESSAGE)

@bot.on(events.NewMessage)
async def text_handler(event):
    """معالجة النصوص العامة"""
    text = event.raw_text
    user_id = event.sender_id
    
    # معالجة رسائل الشحن
    if 'حولت' in text or 'تحويل' in text:
        # استخراج المبلغ ورقم الهاتف من النص
        import re
        amount_match = re.search(r'(\d+)\s*جنيه', text)
        phone_match = re.search(r'(01[0-9]{9})', text)
        
        if amount_match and phone_match:
            amount = float(amount_match.group(1))
            phone = phone_match.group(1)
            
            # إضافة الرصيد
            database.update_balance(user_id, amount)
            database.log_transaction(user_id, amount, 'deposit', phone)
            
            await event.respond(
                f"✅ **تم إضافة الرصيد بنجاح!**\n"
                f"💰 المبلغ: {format_price(amount)}\n"
                f"📱 من رقم: {phone}\n"
                f"💰 رصيدك الجديد: {format_price(database.get_balance(user_id))}"
            )
        else:
            await event.respond(
                "⚠️ **لم نتمكن من قراءة رسالتك**\n"
                "يرجى استخدام الصيغة التالية:\n"
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