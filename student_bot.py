from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext, CallbackQueryHandler
from PIL import Image
import os

# Стані для збору замовлення
TYPE, ORDER = range(2)

# Налаштування
TOKEN = os.getenv("TOKEN")  # беремо токен з Environment Variables
ADMIN_USERNAME = "Yuliya26_01"
ADMIN_CHAT_ID = None  # визначимо за username після старту

# Вітання
WELCOME_TEXT = """Привіт 👋 Я твій помічник у світі студентських робіт!
Тут можна замовити все: від щоденника практики до диплома 😎.
Обери, з чого почнемо, і не переживай — я не ставлю п’ятірки, тільки допомагаю їх отримати 😜
"""

# Вид роботи і ціни
WORKS = {
    "Щоденник практики": "📘 Щоденник практики\n- Стандартний (10–20 днів) — 700–1000 грн, 1–2 дні\n- Розширений — 1200–1800 грн, 2–3 дні\n- Під ключ — 2000–3500 грн, 2–4 дні",
    "Звіт практики": "📊 Звіт практики — 1000–2500 грн, 2–3 дні",
    "Реферат": "📄 Реферат (5–10 сторінок) — 250–400 грн, 1 день",
    "Диплом": "🎓 Дипломна — 4000–8000 грн, 10–20 днів\nПід ключ — 9000–12000 грн, 10–25 днів",
    "Есе": "📄 Есе — 200–300 грн, 1 день\nЕсе англійською — 300–500 грн, 1–2 дні",
    "Курсова": "🎓 Курсова — 1500–3000 грн, 5–7 днів",
    "ДСТУ": "📊 Оформлення за ДСТУ — 100–300 грн",
    "Інше": "Введіть будь-яку роботу вручну"
}

# Функція для перевірки формату картинки (замінює imghdr)
def get_image_type(file_path):
    with Image.open(file_path) as img:
        return img.format.lower()  # 'jpeg', 'png' і т.д.

# Старт бота
def start(update: Update, context: CallbackContext):
    global ADMIN_CHAT_ID
    if ADMIN_CHAT_ID is None:
        ADMIN_CHAT_ID = update.effective_user.id
    keyboard = [[work] for work in WORKS.keys()]
    update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )

# Команда /prices
def prices(update: Update, context: CallbackContext):
    text = "\n\n".join([f"{work}:\n{info}" for work, info in WORKS.items()])
    update.message.reply_text(text)

# Обробка вибору виду роботи
def type_choice(update: Update, context: CallbackContext):
    work = update.message.text
    context.user_data['type'] = work
    info = WORKS.get(work, "Інформація про роботу відсутня")
    
    keyboard = [[InlineKeyboardButton("Замовити зараз", callback_data="order")]]
    update.message.reply_text(info, reply_markup=InlineKeyboardMarkup(keyboard))
    return TYPE

# Кнопка "Замовити зараз"
def order_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.message.reply_text("Вкажи бажаний термін виконання (наприклад: 3 дні):", reply_markup=ReplyKeyboardRemove())
    return ORDER

# Крок збору замовлення: термін і контакт
def order_details(update: Update, context: CallbackContext):
    text = update.message.text
    if 'deadline' not in context.user_data:
        context.user_data['deadline'] = text
        update.message.reply_text("Залиш контакт (ім'я + телефон або email):")
        return ORDER
    else:
        context.user_data['contact'] = text
        summary = (
            f"🔔 *Нове замовлення*\n\n"
            f"*Клієнт:* @{update.effective_user.username or update.effective_user.full_name}\n"
            f"*Тип роботи:* {context.user_data['type']}\n"
            f"*Термін:* {context.user_data['deadline']}\n"
            f"*Контакт:* {context.user_data['contact']}\n"
            f"*UserID:* {update.effective_user.id}"
        )
        context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=summary, parse_mode='Markdown')
        update.message.reply_text("Дякуємо! Ваше замовлення прийнято і передане менеджеру. Скоро з вами зв'яжуться.")
        
        if 'orders' not in context.bot_data:
            context.bot_data['orders'] = {}
        order_id = len(context.bot_data['orders']) + 1
        context.bot_data['orders'][order_id] = {
            'user_id': update.effective_user.id,
            'type': context.user_data['type'],
            'deadline': context.user_data['deadline'],
            'contact': context.user_data['contact']
        }
        context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"Щоб відповісти клієнту, надішліть в цей чат команду:\n/reply {order_id} Текст повідомлення"
        )
        return ConversationHandler.END

# Скасування
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Скасовано.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Команда для адміна /reply
def admin_reply(update: Update, context: CallbackContext):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        update.message.reply_text("Цю команду можна використовувати тільки адміну.")
        return
    args = context.args
    if len(args) < 2:
        update.message.reply_text("Використання: /reply <order_id> <повідомлення>")
        return
    try:
        order_id = int(args[0])
    except:
        update.message.reply_text("Невірний order_id.")
        return
    if order_id not in context.bot_data.get('orders', {}):
        update.message.reply_text("Order_id не знайдено.")
        return
    text = ' '.join(args[1:])
    user_id = context.bot_data['orders'][order_id]['user_id']
    context.bot.send_message(chat_id=user_id, text=f"Повідомлення від менеджера:\n\n{text}")
    update.message.reply_text("Повідомлення надіслано клієнту.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.text & ~Filters.command, type_choice)],
        states={
            TYPE: [CallbackQueryHandler(order_callback, pattern="order")],
            ORDER: [MessageHandler(Filters.text & ~Filters.command, order_details)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv)
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('prices', prices))
    dp.add_handler(CommandHandler('reply', admin_reply))
    dp.add_handler(CommandHandler('help', lambda u, c: u.message.reply_text("Використовуй меню або /start, /prices, /reply")))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

