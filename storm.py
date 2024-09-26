import telebot
import sqlite3
import time
import threading
import random

API_TOKEN = '7594782829:AAFM9zaEblSxSnMWrVLyjsmXBieU_pfEXxQ'
ADMIN_ID = 1971188182 # Замените на ID администратора
bot = telebot.TeleBot(API_TOKEN)


# Функция для получения соединения с базой данных

def expedition_timer_thread():
    time.sleep(3600)  # Ожидание 1 час (3600 секунд)
    bot.send_message(get_chat_id(), "@maksimka2016 @fewarti, экспа завершилась")

def get_database_connection():
    return sqlite3.connect('timers.db', check_same_thread=False)

def is_user_banned(user_id):
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM chat_ban WHERE user_id = ?", (user_id,))
    banned = cursor.fetchone() is not None
    conn.close()
    return banned

# Обработчик событий для новых участников чата
@bot.message_handler(content_types=['new_chat_members'])
def new_member_handler(message):
    for new_member in message.new_chat_members:
        if is_user_banned(new_member.id):
            # Удаляем пользователя из чата
            bot.kick_chat_member(message.chat.id, new_member.id)
            bot.send_message(message.chat.id, f"Пользователь @{new_member.username} был удален из чата, так как он находится в черном списке.")
            # Дополнительно можно отправить сообщение пользователю, если это нужно
            try:
                bot.send_message(new_member.id, "Вы были удалены из чата за нахождение в черном списке.")
            except:
                pass  # Игнорируем, если не удалось отправить сообщение


# Создание таблиц для хранения таймеров и чата
def initialize_database():
    conn = get_database_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS timers (
        user_id INTEGER,
        duration INTEGER,
        timer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS config (
        chat_id INTEGER PRIMARY KEY
    )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_ban (
            user_id INTEGER PRIMARY KEY,
            reason TEXT
        )
     ''')
    conn.commit()

    cursor.execute('SELECT chat_id FROM config')
    if cursor.fetchone() is None:
        # Вставляем ID чата (замените на нужный вам ID)
        cursor.execute('INSERT INTO config (chat_id) VALUES (?)', (123456789,))  # Замените 123456789 на ваш ID чата
        conn.commit()

    conn.close()


initialize_database()


# Функция для управления таймером
def timer_thread(user_id, duration, timer_id, text, username):
    time.sleep(duration)
    chat_id = get_chat_id()

    if user_id == ADMIN_ID:
        bot.send_message(user_id, f"⏰ Таймер {text} завершился!")
    else:
        bot.send_message(chat_id, f"@{username}, напоминание: {text}")

    # Удаляем таймер из базы данных
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM timers WHERE user_id = ? AND timer_id = ?", (user_id, timer_id))
    conn.commit()
    conn.close()


# Функция для получения ID чата
def get_chat_id():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM config')
    chat_id = cursor.fetchone()[0]
    conn.close()
    return chat_id


# Функция для проверки, забанен ли пользователь
def is_user_banned(user_id):
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM chat_ban WHERE user_id = ?", (user_id,))
    banned = cursor.fetchone() is not None
    conn.close()
    return banned


# Функция для парсинга команды таймера
def parse_timer_command(command):
    parts = command.split()
    time_str = parts[0]
    text = ' '.join(parts[1:]) if len(parts) > 1 else '⏰'

    return time_str, text


# Команда для установки таймера
@bot.message_handler(func=lambda message: message.text.lower().startswith('таймер '))
def set_timer(message):
    if is_user_banned(message.from_user.id):
        bot.reply_to(message, "Вы забанены и не можете использовать этого бота.")
        return

    chat_id = get_chat_id()
    if message.chat.id != chat_id and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Этот бот работает только в определенном чате.")
        return

    username = message.from_user.username
    if username is None:
        bot.reply_to(message, "У вас должен быть установлен юзернейм в Telegram, чтобы использовать таймер.")
        return

    try:
        time_str, text = parse_timer_command(message.text[7:])  # Пропускаем 'таймер'
        duration = 0

        if time_str[-1] == 'м':  # минуты
            minutes = int(time_str[:-1])
            duration = minutes * 60
        else:
            bot.reply_to(message, "Неправильный формат. Используйте 'м' для минут.")
            return

        user_id = message.from_user.id

        # Сохранение таймера в базе данных
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO timers (user_id, duration, text) VALUES (?, ?, ?)", (user_id, duration, text))
        conn.commit()
        timer_id = cursor.lastrowid
        conn.close()

        # Запуск таймера в отдельном потоке
        threading.Thread(target=timer_thread, args=(user_id, duration, timer_id, text, username)).start()

        bot.reply_to(message, f"Таймер установлен на {duration // 60} минут с напоминанием '{text}'.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Используйте правильный формат: 'таймер <время>' (например, 'таймер 1м текст').")

# Команда для просмотра таймеров
@bot.message_handler(func=lambda message: message.text.lower().startswith('таймеры'))
def show_timers(message):
    if is_user_banned(message.from_user.id):
        bot.reply_to(message, "Вы забанены и не можете использовать этого бота.")
        return

    chat_id = get_chat_id()
    if message.chat.id != chat_id and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Этот бот работает только в определенном чате.")
        return

    user_id = message.from_user.id
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT timer_id, duration, text FROM timers WHERE user_id = ?", (user_id,))
    user_timers = cursor.fetchall()
    conn.close()

    if user_timers:
        timer_list = "\n".join([f"Таймер {timer_id}: {duration // 60} минут, текст: {text}" for timer_id, duration, text in user_timers])
        bot.reply_to(message, f"Ваши таймеры:\n{timer_list}")
    else:
        bot.reply_to(message, "У вас нет активных таймеров.")

# Команда для удаления таймера
@bot.message_handler(func=lambda message: message.text.lower().startswith('удалить'))
def delete_timer(message):
    if is_user_banned(message.from_user.id):
        bot.reply_to(message, "Вы забанены и не можете использовать этого бота.")
        return

    chat_id = get_chat_id()
    if message.chat.id != chat_id and message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Этот бот работает только в определенном чате.")
        return

    user_id = message.from_user.id
    try:
        timer_id = int(message.text.split()[1])

        # Удаление таймера из базы данных
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM timers WHERE user_id = ? AND timer_id = ?", (user_id, timer_id))
        conn.commit()
        conn.close()

        if cursor.rowcount > 0:
            bot.reply_to(message, f"Таймер {timer_id} удален.")
        else:
            bot.reply_to(message, "Неправильный номер таймера или таймер не существует.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Используйте правильный формат: 'таймер удалить <номер>'.")


# Команда для администратора: статистика
@bot.message_handler(func=lambda message: message.text.lower() == 'статистика')
def show_statistics(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    conn = get_database_connection()
    cursor = conn.cursor()

    # Получаем три последних таймера
    cursor.execute("SELECT user_id, text FROM timers ORDER BY timer_id DESC LIMIT 3")
    last_timers = cursor.fetchall()

    # Получаем пользователя с наибольшим количеством таймеров
    cursor.execute("SELECT user_id, COUNT(*) as count FROM timers GROUP BY user_id ORDER BY count DESC LIMIT 1")
    most_timers = cursor.fetchone()

    conn.close()
    # Формируем сообщение
    response = "📊 Статистика:\n"
    response += "Последние три таймера:\n"
    for user_id, text in last_timers:
        response += f"@{user_id} - {text}\n"
    if most_timers:
        response += f"\nПользователь с наибольшим количеством таймеров: @{most_timers[0]} с {most_timers[1]} таймерами.\n"
    # Случайное сообщение "Кто сосал"
    response += f"\nКто сосал: @{random.choice(['maksimka2016', 'другой_пользователь'])}"
    bot.send_message(ADMIN_ID, response)


@bot.message_handler(func=lambda message: message.chat.id == get_chat_id() and
                                   message.text.startswith("Экспедиция началась! 🧳") and
                                   "🌏" in message.text)
def handle_expedition(message):
    threading.Thread(target=expedition_timer_thread).start()
    bot.reply_to(message, "Таймер на экспедицию запущен на 1 час")


@bot.message_handler(func=lambda message: message.text.lower().startswith('привязать'))
def bind_chat_id(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    try:
        new_chat_id = int(message.text.split()[1])

        # Обновление ID чата в базе данных
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE config SET chat_id = ?", (new_chat_id,))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"Чат привязан: {new_chat_id}.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Используйте правильный формат: 'привязать <ID чата>'.")

@bot.message_handler(func=lambda message: message.text.lower().startswith('чс '))
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    try:
        parts = message.text.split()
        user_id_to_ban = int(parts[1])
        reason = ' '.join(parts[2:]) if len(parts) > 2 else 'нарушитель'

        # Добавление пользователя в черный список
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO chat_ban (user_id, reason) VALUES (?, ?)", (user_id_to_ban, reason))
        conn.commit()
        conn.close()

        bot.reply_to(message, f"Пользователь с ID {user_id_to_ban} был добавлен в черный список. Причина: {reason}.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Используйте правильный формат: 'чс <user_id> <причина>'")


@bot.message_handler(func=lambda message: message.text.lower().startswith('-чс'))
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    try:
        user_id_to_unban = int(message.text.split()[1])

        # Удаление пользователя из черного списка
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_ban WHERE user_id = ?", (user_id_to_unban,))
        conn.commit()
        conn.close()

        bot.reply_to(message, f"Пользователь с ID {user_id_to_unban} был вынесен из чс.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Используйте правильный формат: '-чс <user_id>'.")


@bot.message_handler(func=lambda message: message.text.lower() == 'список чсов')
def list_banned_users(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return

    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, reason FROM chat_ban")
    banned_users = cursor.fetchall()
    conn.close()

    if banned_users:
        response = "Список забаненных пользователей:\n"
        for user_id, reason in banned_users:
            try:
                user_info = bot.get_chat(user_id)
                username = user_info.username if user_info.username else "Нет юзернейма"
                response += f"@{username} - {user_id} - Причина: {reason}\n"
            except Exception as e:
                response += f"Пользователь ID {user_id} - Причина: {reason} (не удалось получить информацию о пользователе)\n"

        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "Список забаненных пользователей пуст.")


@bot.message_handler(func=lambda message: message.text.lower() == 'адмк')
def show_rules(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У вас нет прав на выполнение этой команды.")
        return
    rules_text = (
        "чс [телеграм ид] [причина] - заносит в чс\n"
        "-чс [телеграм ид] - снимает чс\n"
        "список чсов - список пользователей с чсом империи\n"
    )
    bot.reply_to(message, rules_text)

@bot.message_handler(func=lambda message: message.text.lower() == 'правила')
def show_rules(message):
    rules_text = (
        "🎟Немного о требованиях\n"
        "От каждого участника империи: \n"
        "| Желателен актив 25 сообщений боту/час.\n"
        "| Необходимо ускорение производства завода/пополнение склада ресурсами.\n"
        "| Участие в как можно большем количестве экспедиций империи (будут упоминания).\n"
        "| Не жалеем и бьём босса, чтобы получить больше наград.\n"
        "| Нужны доброжелательность и уважение ко всем участникам группы.\n\n"

        "🏰Правила империи\n"
        "1. Участники группы не грабят друг друга.\n"
        "2. Любая информация о группе и/или империи должна остаться в группе - слив не запрещён нам похуй.\n"
        "3. Не забываем о взаимном уважении и адекватном поведении по отношению друг к другу.\n"
        "4. Чистка империи и группы производится каждую неделю. Самые неактивные будут исключены.\n"
        "5. Во время сборов на экспедицию не играем в бота, чтобы не мешать созыву.\n\n"

        "❔По всем вопросам » Михаил (@fewarti), Максим (@maksimka2016)"
    )
    bot.reply_to(message, rules_text)


if __name__ == '__main__':
    bot.polling(none_stop=True)