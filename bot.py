import telebot
from telebot import types
from strava_api import get_user, save_user, delete_user, exchange_code_for_tokens, get_activities
from training_logic import parse_strava_activities, build_week_plan

BOT_TOKEN = "8200480147:AAGWgAapLI_9zyiIaZuolzFAuyi_QuBJWmA"
bot = telebot.TeleBot(BOT_TOKEN)

# --- /start ---
@bot.message_handler(commands=["start"])
def cmd_start(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if user:
        text = (
            "👋 Привет! Я бот StravaCCU, помогаю строить персональный план тренировок на основе ваших данных Strava.\n\n"
            "✅ Ваши данные уже есть.\n"
            "Чтобы узнать все доступные команды, используйте /help."
        )
        # Кнопка удаления данных
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🏃 Получить план тренировок", "🗑️ Удалить данные")
        bot.send_message(chat_id, text, reply_markup=markup)
    else:
        text = (
            "👋 Привет! Я бот StravaCCU, помогаю строить персональный план тренировок на основе ваших данных Strava.\n\n"
            "❌ Данных о вас пока нет. перед регистрацией можете ознакомиться с инструкцией используйте команду /helpregister.\n"
            "🔗 А чтобы зарегистрироваться, используйте команду /registrate.\n"
            "ℹ️ Чтобы узнать все доступные команды, используйте /help."
        )
        bot.send_message(chat_id, text)

# --- /delacc ---
@bot.message_handler(commands=["delacc"])
def cmd_delacc(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if not user:
        bot.send_message(chat_id, "⚠️ Данных о вас нет.")
        return
    delete_user(chat_id)
    bot.send_message(chat_id, "🗑️ Ваши данные успешно удалены. Теперь вы можете зарегистрироваться заново через /registrate.")

# --- Обработка Client ID ---
@bot.message_handler(func=lambda m: m.text and m.text.isdigit())
def handle_client_id(message):
    chat_id = message.chat.id
    client_id = message.text
    user = get_user(chat_id)
    if user:
        bot.send_message(chat_id, "ℹ️ Вы уже зарегистрированы.")
        return

    link = f"https://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all"
    bot.send_message(chat_id, f"🔗 Перейдите по этой ссылке, авторизуйтесь и пришлите сюда ссылку с code:\n{link}")
    bot.register_next_step_handler(message, handle_auth_link, client_id)

# --- Обработка ссылки с code ---
def handle_auth_link(message, client_id):
    chat_id = message.chat.id
    url = message.text.strip()
    if "code=" not in url:
        bot.send_message(chat_id, "❌ Ссылка некорректна, попробуйте ещё раз.")
        return
    code = url.split("code=")[1].split("&")[0]

    msg = bot.send_message(chat_id, "🔑 Теперь пришлите ваш Client Secret:")
    bot.register_next_step_handler(msg, lambda m: handle_client_secret(m, client_id, code))

# --- Обработка Client Secret ---
def handle_client_secret(message, client_id, code):
    chat_id = message.chat.id
    client_secret = message.text.strip()
    try:
        access_token, refresh_token, expires_at = exchange_code_for_tokens(client_id, client_secret, code)
        save_user(chat_id, client_id, client_secret, access_token, refresh_token, expires_at)
        bot.send_message(chat_id, "✅ Регистрация успешна! Теперь вы можете получить план тренировок командой /plan")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка получения токена: {e}")

# --- /plan ---
@bot.message_handler(commands=["plan"])
def cmd_plan(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if not user:
        bot.send_message(chat_id, "⚠️ Сначала зарегистрируйтесь через /start")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⚡ Увеличить темп", "📏 Увеличить дистанцию")
    bot.send_message(chat_id, "🎯 Выберите цель:", reply_markup=markup)

# --- Обработка кнопки "🏃 Получить план тренировок" ---
@bot.message_handler(func=lambda m: m.text == "🏃 Получить план тренировок")
def handle_plan_button(message):
    cmd_plan(message)

# --- Обработка целей ---
@bot.message_handler(func=lambda m: m.text in ["⚡ Увеличить темп", "📏 Увеличить дистанцию"])
def handle_goal_buttons(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if not user:
        bot.send_message(chat_id, "❌ Ошибка. Зарегистрируйтесь заново.")
        return

    goal = "pace" if message.text == "⚡ Увеличить темп" else "distance"

    try:
        raw = get_activities(user)
        workouts = parse_strava_activities(raw)
        plan = build_week_plan(workouts, goal=goal)
        bot.send_message(chat_id, f"🏃‍♂️ Ваш план тренировок:\n\n{plan}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {e}")

# --- /registrate ---
@bot.message_handler(commands=["registrate"])
def cmd_registrate(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if user:
        bot.send_message(chat_id, "ℹ️ Вы уже зарегистрированы. Если хотите удалить старые данные и зарегистрироваться заново, используйте /delacc.")
        return
    bot.send_message(chat_id, "👋 Отлично! Пришлите ваш Client ID из Strava API для регистрации.\n"
                     "Для помощи команда /help ✅\n")

# --- Удаление данных ---
@bot.message_handler(func=lambda m: m.text and "удалить данные" in m.text.lower())
def cmd_delete(message):
    delete_user(message.chat.id)
    bot.send_message(message.chat.id, "🗑️ Данные удалены. Пришлите новый Client ID для регистрации.")

# --- /help ---
@bot.message_handler(commands=["help"])
def cmd_help(message):
    text = (
        "📌<b> Доступные команды:</b>\n"
        "/start - регистрация через Strava\n"
        "/registrate - зарегестрироваться\n"
        "/help - показать эту справку\n"
        "/helpregister - помощь в регистрации\n"
        "/delacc - удалить свои данные\n"
        "/plan - получить план тренировок\n"
        "/about - информация о боте\n\n"
        "<b>После регистрации используйте кнопки:</b>\n"
        "🏃 Получить план тренировок\n"
        "⚡ Увеличить темп\n"
        "📏 Увеличить дистанцию\n"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=["helpregister"])
def cmd_help(message):
    text = (
        "📌<b> Для регистрации вам нужно будет выполнить ряд простых действий:</b>\n"
        "1️⃣ Регистрация в Strava\n"
        "2️⃣ Перейдите по ссылке: https://www.strava.com/settings/api 🔗\n"
        "3️⃣ Дайте любое название приложения, категорию, клуб.\n"
        "4️⃣ В веб-сайт укажите: http://localhost\n"
        "5️⃣ В домен поставьте: localhost\n"
        "6️⃣ Сохранить ✅\n"
        "7️⃣ Далее загрузите любое фото, во вкладке <b>Мое настройки API</b> и готово!\n"
        "<b>Поздравляю!</b> У вас теперь есть доступ к своим токенам. Можете переходить к /registrate"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML")

# --- /about ---
@bot.message_handler(commands=["about"])
def cmd_about(message):
    text = (
        "🤖 Бот StravaCCU\n"
        "Создан для построения персонального плана тренировок на основе ваших данных Strava.\n"
        "План учитывает реальную дистанцию и темп ваших тренировок."
    )
    bot.send_message(message.chat.id, text)

print("Бот запущен... 🚀")
bot.polling(none_stop=True)
