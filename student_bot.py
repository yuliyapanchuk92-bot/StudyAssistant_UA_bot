import sys
print("Python version:", sys.version)

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler
)
from PIL import Image
import filetype
import os

# Стані для збору замовлення
TYPE, ORDER = range(2)

# Налаштування
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Environment variable TOKEN не встановлено!")

ADMIN_USERNAME = "Yuliya26_01"
ADMIN_CHAT_ID = None

# Вітання
WELCOME_TEXT = """Привіт 👋 Я твій помічник у світі студентських робіт!
Тут можна замовити все: від щоденника практики до диплома 😎.
Обери, з чого почнемо, і не переживай — я не ставлю п’ятірки, тільки допомагаю їх отримати 😜
"""

# Вид роботи і ціни
WORKS = {
    "Щоденник практики": "📘 Щоденник практики\n- Стандартний — 700–1000 грн\n- Розширений — 1200–1800 грн",
    "Звіт практики": "📊 Звіт практики — 1000–2500 грн",
    "Реферат": "📄 Реферат — 250–400 грн",
    "Диплом": "🎓 Дипломна — 4000–8000 грн",
    "Есе": "📄 Есе — 200–500 грн",
    "Курсова": "🎓 Курсова — 1500–3000 грн",
    "ДСТУ": "📊 Оформлення за ДСТУ — 100–300 грн",
    "Інше": "Введіть будь-яку роботу вручну"
}

# Функція для перевірки типу файлу через filetype
def get_file_type(file_path: str) -> str:
    kind = filetype.guess(file_path)
    if kind is None:
        return "unknown"
    return kind.extension  # 'jpg', 'png', 'gif' і т.д.

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
        return ConversationHandler.END

# Скасування
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Скасовано.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Основна функція
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
    dp.add_handler(CommandHandler('help', lambda u, c: u.message.reply_text("Використовуй меню або /start, /prices")))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
