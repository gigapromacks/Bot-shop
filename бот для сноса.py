import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import sqlite3
from datetime import datetime
import logging

# ========== ТОКЕН ==========
TOKEN = "8548987445:AAEsIrwwm4uDKowextu7Q7atJ3oKmjOw7XQ"
bot = AsyncTeleBot(TOKEN)

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect('krovstars.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY,
              username TEXT,
              balance INTEGER DEFAULT 0,
              registered DATE)''')

c.execute('''CREATE TABLE IF NOT EXISTS stars
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              amount INTEGER,
              price_rub INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS nft
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT,
              price_rub INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS orders
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              item_type TEXT,
              item_name TEXT,
              total_price INTEGER,
              status TEXT DEFAULT 'pending',
              date DATE)''')

c.execute('''CREATE TABLE IF NOT EXISTS nft_requests
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              description TEXT,
              status TEXT DEFAULT 'new',
              date DATE)''')

conn.commit()

# ========== ЗАПОЛНЯЕМ ЗВЁЗДЫ ==========
c.execute("SELECT COUNT(*) FROM stars")
if c.fetchone()[0] == 0:
    stars_data = [
        (50, 75), (75, 110), (100, 150), (150, 225),
        (250, 350), (500, 720), (750, 1050), (1000, 1479)
    ]
    for amount, price in stars_data:
        c.execute("INSERT INTO stars (amount, price_rub) VALUES (?, ?)", (amount, price))
    conn.commit()

# ========== АДМИНЫ ==========
ADMIN_IDS = [5284075920, 7738500002]

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ========== КОМАНДЫ ==========

@bot.message_handler(commands=['start'])
async def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "no_username"
    
    c.execute("INSERT OR IGNORE INTO users (user_id, username, registered) VALUES (?, ?, ?)",
              (user_id, username, datetime.now().date()))
    conn.commit()
    
    text = (
        "👋 Добро пожаловать в KrovStars!\n\n"
        "💫 Покупай звёзды и заказывай NFT\n"
        "👑 Админ: @krovenov\n\n"
        "📌 Основные команды:\n"
        "/help - инструкция\n"
        "/stars - купить звёзды\n"
        "/nft - готовые NFT\n"
        "/order_nft - заказать свой NFT\n"
        "/profile - мой профиль\n"
        "/orders - мои заказы\n"
        "/support - поддержка"
    )
    
    await bot.reply_to(message, text)

@bot.message_handler(commands=['help'])
async def cmd_help(message):
    text = (
        "ИНСТРУКЦИЯ ПО БОТУ KrovStars\n\n"
        
        "1. Как купить звёзды\n"
        "1. Напиши /stars\n"
        "2. Выбери количество звёзд\n"
        "3. Нажми 'Купить'\n"
        "4. Бот покажет реквизиты\n"
        "5. Оплати и напиши @krovenov\n\n"
        
        "2. Как купить готовый NFT\n"
        "1. Напиши /nft\n"
        "2. Выбери NFT из списка\n"
        "3. Нажми 'Купить'\n"
        "4. Оплати и забери свой NFT\n\n"
        
        "3. Как заказать свой NFT\n"
        "1. Напиши /order_nft\n"
        "2. Опиши, что хочешь:\n"
        "   - стиль\n"
        "   - тема\n"
        "   - цвета\n"
        "   - референсы\n"
        "3. Бот отправит заявку админу\n"
        "4. @krovenov свяжется с тобой\n\n"
        
        "Все команды:\n"
        "/start - запустить бота\n"
        "/help - эта инструкция\n"
        "/profile - мой профиль\n"
        "/stars - каталог звёзд\n"
        "/nft - готовые NFT\n"
        "/order_nft - заказать NFT\n"
        "/orders - история заказов\n"
        "/support - связь с поддержкой"
    )
    
    await bot.reply_to(message, text)

@bot.message_handler(commands=['profile'])
async def cmd_profile(message):
    user_id = message.from_user.id
    c.execute("SELECT balance, registered FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        balance, registered = result
        text = f"ТВОЙ ПРОФИЛЬ\n\nID: {user_id}\nБаланс: {balance} монет\nЗарегистрирован: {registered}"
    else:
        text = "Профиль не найден. Напиши /start"
    
    await bot.reply_to(message, text)

@bot.message_handler(commands=['stars'])
async def cmd_stars(message):
    c.execute("SELECT id, amount, price_rub FROM stars ORDER BY amount")
    stars = c.fetchall()
    
    text = "ЗВЁЗДЫ TELEGRAM\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for star_id, amount, price in stars:
        text += f"• {amount} ⭐ — {price}₽\n"
        markup.add(types.InlineKeyboardButton(
            f"Купить {amount} ⭐ за {price}₽",
            callback_data=f"buy_star_{star_id}"
        ))
    
    await bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(commands=['nft'])
async def cmd_nft(message):
    c.execute("SELECT id, name, price_rub FROM nft")
    nft_list = c.fetchall()
    
    if not nft_list:
        text = "NFT временно нет в наличии"
        markup = None
    else:
        text = "ГОТОВЫЕ NFT\n\n"
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for nft_id, name, price in nft_list:
            text += f"• {name} — {price}₽\n"
            markup.add(types.InlineKeyboardButton(
                f"Купить {name} за {price}₽",
                callback_data=f"buy_nft_{nft_id}"
            ))
    
    await bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(commands=['order_nft'])
async def cmd_order_nft(message):
    msg = await bot.reply_to(
        message,
        "ЗАКАЗ СВОЕГО NFT\n\n"
        "Опиши, какой NFT ты хочешь:\n"
        "- стиль\n"
        "- тема\n"
        "- цвета\n"
        "- референсы (если есть)\n\n"
        "Напиши описание в одном сообщении:"
    )
    bot.register_next_step_handler(msg, process_nft_request)

async def process_nft_request(message):
    user_id = message.from_user.id
    description = message.text
    
    c.execute("INSERT INTO nft_requests (user_id, description, date) VALUES (?, ?, ?)",
              (user_id, description, datetime.now().date()))
    conn.commit()
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"НОВЫЙ ЗАПРОС NFT\n\nОт: {user_id}\nОписание: {description}"
            )
        except:
            pass
    
    await bot.reply_to(
        message,
        "✅ Запрос отправлен! Скоро @krovenov свяжется с тобой."
    )

@bot.message_handler(commands=['orders'])
async def cmd_orders(message):
    user_id = message.from_user.id
    c.execute(
        "SELECT item_name, total_price, status, date FROM orders "
        "WHERE user_id = ? ORDER BY date DESC LIMIT 10",
        (user_id,)
    )
    orders = c.fetchall()
    
    if not orders:
        text = "ЗАКАЗЫ\n\nУ тебя пока нет заказов"
    else:
        text = "ТВОИ ПОСЛЕДНИЕ ЗАКАЗЫ\n\n"
        for name, price, status, date in orders:
            status_text = "Выполнен" if status == "completed" else "В обработке"
            text += f"• {date}: {name} — {price}₽ ({status_text})\n"
    
    await bot.reply_to(message, text)

@bot.message_handler(commands=['support'])
async def cmd_support(message):
    text = (
        "ПОДДЕРЖКА\n\n"
        "По всем вопросам: @krovenov\n"
        "Время ответа: до 1 часа\n\n"
        "Или напиши сюда свой вопрос, и я передам админу."
    )
    await bot.reply_to(message, text)

# ========== АДМИН-КОМАНДЫ ==========

@bot.message_handler(commands=['admin'])
async def cmd_admin(message):
    if not is_admin(message.from_user.id):
        await bot.reply_to(message, "⛔ Нет доступа")
        return
    
    text = (
        "АДМИН-ПАНЕЛЬ\n\n"
        "/add_nft - добавить новый NFT\n"
        "/requests - заявки на NFT\n"
        "/stats - статистика\n"
        "/broadcast - рассылка"
    )
    await bot.reply_to(message, text)

@bot.message_handler(commands=['add_nft'])
async def cmd_add_nft(message):
    if not is_admin(message.from_user.id):
        return
    
    msg = await bot.reply_to(
        message,
        "Введи данные NFT в формате:\n"
        "Название | Цена\n\n"
        "Пример: CyberPunk #001 | 500"
    )
    bot.register_next_step_handler(msg, process_add_nft)

async def process_add_nft(message):
    try:
        name, price = message.text.split('|')
        name = name.strip()
        price = int(price.strip())
        
        c.execute("INSERT INTO nft (name, price_rub) VALUES (?, ?)", (name, price))
        conn.commit()
        
        await bot.reply_to(message, f"✅ NFT {name} добавлен за {price} руб.")
    except:
        await bot.reply_to(message, "❌ Ошибка формата. Используй: Название | Цена")

@bot.message_handler(commands=['requests'])
async def cmd_requests(message):
    if not is_admin(message.from_user.id):
        return
    
    c.execute("SELECT id, user_id, description, date FROM nft_requests WHERE status = 'new'")
    requests = c.fetchall()
    
    if not requests:
        await bot.reply_to(message, "Новых заявок нет")
        return
    
    for req_id, user_id, desc, date in requests:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Обработано", callback_data=f"req_done_{req_id}"),
            types.InlineKeyboardButton("💬 Написать", url=f"tg://user?id={user_id}")
        )
        
        await bot.send_message(
            message.chat.id,
            f"ЗАЯВКА #{req_id}\n\nОт: {user_id}\nДата: {date}\nОписание: {desc}",
            reply_markup=markup
        )

@bot.message_handler(commands=['stats'])
async def cmd_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM nft_requests")
    total_requests = c.fetchone()[0]
    
    c.execute("SELECT SUM(total_price) FROM orders WHERE status = 'completed'")
    total_earned = c.fetchone()[0] or 0
    
    text = (
        f"СТАТИСТИКА\n\n"
        f"Пользователей: {total_users}\n"
        f"Заказов: {total_orders}\n"
        f"Заявок на NFT: {total_requests}\n"
        f"Заработано: {total_earned} руб"
    )
    
    await bot.reply_to(message, text)

@bot.message_handler(commands=['broadcast'])
async def cmd_broadcast(message):
    if not is_admin(message.from_user.id):
        return
    
    msg = await bot.reply_to(
        message,
        "Введи текст для рассылки всем пользователям:"
    )
    bot.register_next_step_handler(msg, process_broadcast)

async def process_broadcast(message):
    if not is_admin(message.from_user.id):
        return
    
    text = message.text
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    
    sent = 0
    await bot.reply_to(message, f"⏳ Рассылка началась... ({len(users)} пользователей)")
    
    for (uid,) in users:
        try:
            await bot.send_message(uid, f"РАССЫЛКА\n\n{text}")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            continue
    
    await bot.send_message(
        message.chat.id,
        f"✅ Рассылка завершена\nОтправлено: {sent} пользователям"
    )

# ========== КНОПКИ ==========

@bot.callback_query_handler(func=lambda call: True)
async def callback_handler(call):
    data = call.data
    
    if data.startswith("buy_star_"):
        star_id = int(data.replace("buy_star_", ""))
        await buy_star(call, star_id)
    
    elif data.startswith("buy_nft_"):
        nft_id = int(data.replace("buy_nft_", ""))
        await buy_nft(call, nft_id)
    
    elif data.startswith("req_done_"):
        if not is_admin(call.from_user.id):
            return
        req_id = int(data.replace("req_done_", ""))
        c.execute("UPDATE nft_requests SET status = 'done' WHERE id = ?", (req_id,))
        conn.commit()
        await bot.edit_message_text(
            "✅ Заявка обработана",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

async def buy_star(call, star_id):
    c.execute("SELECT amount, price_rub FROM stars WHERE id = ?", (star_id,))
    amount, price = c.fetchone()
    
    c.execute(
        "INSERT INTO orders (user_id, item_type, item_name, total_price, date) VALUES (?, ?, ?, ?, ?)",
        (call.from_user.id, "star", f"{amount} ⭐", price, datetime.now().date())
    )
    conn.commit()
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"НОВЫЙ ЗАКАЗ\n\nПользователь: {call.from_user.id}\nТовар: {amount} ⭐\nЦена: {price}₽"
            )
        except:
            pass
    
    await bot.edit_message_text(
        f"ЗАКАЗ ОФОРМЛЕН!\n\n"
        f"Товар: {amount} ⭐\n"
        f"Сумма: {price}₽\n\n"
        f"Реквизиты:\n"
        f"Т-банк: 2200701239444877\n\n"
        f"После оплаты:\n"
        f"1. Сделай скриншот\n"
        f"2. Напиши @krovenov\n"
        f"3. Отправь скрин и этот заказ",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

async def buy_nft(call, nft_id):
    c.execute("SELECT name, price_rub FROM nft WHERE id = ?", (nft_id,))
    name, price = c.fetchone()
    
    c.execute(
        "INSERT INTO orders (user_id, item_type, item_name, total_price, date) VALUES (?, ?, ?, ?, ?)",
        (call.from_user.id, "nft", name, price, datetime.now().date())
    )
    conn.commit()
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"НОВЫЙ ЗАКАЗ NFT\n\nПользователь: {call.from_user.id}\nТовар: {name}\nЦена: {price}₽"
            )
        except:
            pass
    
    await bot.edit_message_text(
        f"ЗАКАЗ ОФОРМЛЕН!\n\n"
        f"Товар: {name}\n"
        f"Сумма: {price}₽\n\n"
        f"Реквизиты:\n"
        f"Т-банк: 2200701239444877\n\n"
        f"После оплаты:\n"
        f"1. Сделай скриншот\n"
        f"2. Напиши @krovenov\n"
        f"3. Отправь скрин и этот заказ",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("Бот KrovStars запущен!")
    print("Админы:", ADMIN_IDS)
    asyncio.run(bot.polling())