import sqlite3
from datetime import datetime
import telebot
from telebot import types

TOKEN = "8852094345:AAGbc2KQeR3paHno8QHiuIiy-1HoFqtx3O0"

bot = telebot.TeleBot(TOKEN)

DB_NAME = "expenses.db"

# Состояния пользователей
user_states = {}


# =========================
# Работа с базой данных
# =========================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_expense(user_id, category, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO expenses (user_id, date, category, amount)
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        category,
        amount
    ))

    conn.commit()
    conn.close()


def get_current_month_expenses(user_id):
    current_month = datetime.now().strftime("%Y-%m")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, category, amount
        FROM expenses
        WHERE user_id = ?
          AND date LIKE ?
        ORDER BY date DESC
    """, (user_id, f"{current_month}%"))

    expenses = cursor.fetchall()
    conn.close()

    return expenses


# =========================
# Клавиатуры
# =========================

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.add(
        types.KeyboardButton("Добавить трату")
    )

    keyboard.add(
        types.KeyboardButton("История за месяц")
    )

    return keyboard


def categories_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )

    keyboard.row(
        types.KeyboardButton("Еда"),
        types.KeyboardButton("Хобби")
    )

    keyboard.row(
        types.KeyboardButton("Транспорт"),
        types.KeyboardButton("Другое")
    )

    return keyboard


# =========================
# Команда /start
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    user_states.pop(message.from_user.id, None)

    bot.send_message(
        message.chat.id,
        "Привет! 👋\n\n"
        "Я помогу тебе вести учёт расходов.\n"
        "Выбери действие:",
        reply_markup=main_keyboard()
    )


# =========================
# Добавление траты
# =========================

@bot.message_handler(func=lambda message: message.text == "Добавить трату")
def add_expense_start(message):
    user_states[message.from_user.id] = {
        "state": "waiting_amount"
    }

    bot.send_message(
        message.chat.id,
        "Введите сумму траты в рублях.\n\n"
        "Например: 1250 или 499.50",
        reply_markup=types.ReplyKeyboardRemove()
    )


@bot.message_handler(
    func=lambda message: (
        message.from_user.id in user_states
        and user_states[message.from_user.id]["state"] == "waiting_amount"
    )
)
def process_amount(message):
    try:
        amount_text = message.text.replace(",", ".").strip()
        amount = float(amount_text)

        if amount <= 0:
            raise ValueError

    except ValueError:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введи корректную сумму.\n"
            "Например: 500 или 1250.50"
        )
        return

    user_states[message.from_user.id] = {
        "state": "waiting_category",
        "amount": amount
    }

    bot.send_message(
        message.chat.id,
        "Выбери категорию:",
        reply_markup=categories_keyboard()
    )


@bot.message_handler(
    func=lambda message: (
        message.from_user.id in user_states
        and user_states[message.from_user.id]["state"] == "waiting_category"
    )
)
def process_category(message):
    categories = ["Еда", "Хобби", "Транспорт", "Другое"]

    if message.text not in categories:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, выбери категорию с помощью кнопок.",
            reply_markup=categories_keyboard()
        )
        return

    user_id = message.from_user.id
    amount = user_states[user_id]["amount"]
    category = message.text

    add_expense(user_id, category, amount)

    user_states.pop(user_id, None)

    bot.send_message(
        message.chat.id,
        f"✅ Трата сохранена!\n\n"
        f"Категория: {category}\n"
        f"Сумма: {amount:.2f} ₽",
        reply_markup=main_keyboard()
    )


# =========================
# История за месяц
# =========================

@bot.message_handler(func=lambda message: message.text == "История за месяц")
def month_history(message):
    user_id = message.from_user.id
    expenses = get_current_month_expenses(user_id)

    if not expenses:
        bot.send_message(
            message.chat.id,
            "📊 За текущий месяц трат пока нет.",
            reply_markup=main_keyboard()
        )
        return

    total = sum(expense[2] for expense in expenses)

    text = "📊 <b>История расходов за текущий месяц</b>\n\n"

    for date, category, amount in expenses:
        formatted_date = datetime.strptime(
            date,
            "%Y-%m-%d %H:%M:%S"
        ).strftime("%d.%m %H:%M")

        text += (
            f"• {formatted_date} — "
            f"{category}: <b>{amount:.2f} ₽</b>\n"
        )

    text += f"\n💰 <b>Всего: {total:.2f} ₽</b>"

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


# =========================
# Запуск бота
# =========================

if __name__ == "__main__":
    init_db()

    print("Бот запущен...")

    bot.infinity_polling()
