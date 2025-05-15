import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from bot.conversation import (
    BECOME_NANNY_NAME, BECOME_NANNY_CITY, BECOME_NANNY_EXP,
    BECOME_NANNY_PETS, BECOME_NANNY_RATE, BECOME_NANNY_DESC,
    BECOME_NANNY_PASSWORD, registration_cancel
)

# Enhanced nanny registration
async def enhanced_nanny_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    from data.database import get_nanny, add_user

    if get_nanny(user_id):
        await update.message.reply_text("✅ Вы уже зарегистрированы как няня. Используйте /myinfo для просмотра профиля.")
        return ConversationHandler.END

    user_username = user.username or f"user_{user_id}"
    add_user(user_id, user_username)
    context.user_data["nanny_info"] = {"username": user_username}

    registration_text = (
        "🐾 РЕГИСТРАЦИЯ НЯНИ 🐾\n"
        "---------------------\n\n"
        "Добро пожаловать в наше сообщество нянь для питомцев!\n\n"
        "Шаг 1 из 7: Укажите ваши имя и фамилию, которые будут видны клиентам:"
    )

    keyboard = [[InlineKeyboardButton("❌ Отменить регистрацию", callback_data="cancel_registration")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(registration_text, reply_markup=reply_markup)
    return BECOME_NANNY_NAME


async def cancel_registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Регистрация отменена. Вы можете начать снова в любое время с помощью /become_nanny")
    return ConversationHandler.END

async def enhanced_nanny_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nanny_info"] = context.user_data.get("user_info", {})
    context.user_data["nanny_info"]["name"] = update.message.text.strip()

    await update.message.reply_text(
        "✅ Имя сохранено!\n\nШаг 2 из 7: В каком городе вы предоставляете услуги? 🏙️"
    )
    return BECOME_NANNY_CITY

async def enhanced_nanny_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nanny_info"]["city"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ Город сохранен!\n\nШаг 3 из 7: Укажите ваш опыт работы с питомцами (в годах) 📊\nВведите только число, например: 2"
    )
    return BECOME_NANNY_EXP

async def enhanced_nanny_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    experience = update.message.text.strip()
    if not experience.isdigit():
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите только число (опыт в годах).\nНапример: 2"
        )
        return BECOME_NANNY_EXP

    context.user_data["nanny_info"]["experience"] = int(experience)

    keyboard = [
        ["🐶 Собаки", "🐱 Кошки"],
        ["🐦 Птицы", "🐹 Грызуны"],
        ["🐠 Рыбки", "🦎 Рептилии"],
        ["🌟 Все типы питомцев"],
    ]
    await update.message.reply_text(
        "✅ Опыт сохранен!\n\nШаг 4 из 7: Выберите типы питомцев, с которыми вы работаете 🐾",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return BECOME_NANNY_PETS

async def enhanced_nanny_pets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pet_choice = update.message.text
    if "Все типы питомцев" in pet_choice:
        pet_types = ["Собаки", "Кошки", "Птицы", "Грызуны", "Рыбки", "Рептилии"]
    else:
        pet_types = [re.sub(r"[^\w\s]", "", pet_choice).strip()]

    context.user_data["nanny_info"]["pet_types"] = pet_types

    rate_keyboard = [
        ["1000 ₸", "1500 ₸", "2000 ₸"],
        ["2500 ₸", "3000 ₸", "4000 ₸"],
        ["5000 ₸", "Другая сумма"]
    ]
    await update.message.reply_text(
        "✅ Типы питомцев сохранены!\n\nШаг 5 из 7: Укажите вашу почасовую ставку в тенге 💰\nВыберите предложенную сумму или укажите свою:",
        reply_markup=ReplyKeyboardMarkup(rate_keyboard, one_time_keyboard=True)
    )
    return BECOME_NANNY_RATE

async def enhanced_nanny_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rate_text = update.message.text.strip()
    rate = rate_text.split(" ")[0] if "₸" in rate_text else rate_text

    if rate == "Другая сумма":
        await update.message.reply_text("Введите вашу почасовую ставку (только число):", reply_markup=ReplyKeyboardRemove())
        return BECOME_NANNY_RATE

    if not rate.isdigit():
        await update.message.reply_text("⚠️ Пожалуйста, введите только число без символов.\nНапример: 2000", reply_markup=ReplyKeyboardRemove())
        return BECOME_NANNY_RATE

    context.user_data["nanny_info"]["hourly_rate"] = int(rate)

    examples = [
        "Опытный кинолог, умею обращаться с собаками разных пород. Предоставляю услуги выгула и дрессировки.",
        "Люблю кошек всех пород, имею опыт работы в ветклинике. Могу давать лекарства и следить за питанием.",
        "Профессиональный зоолог с высшим образованием. Опыт работы с разными видами животных более 5 лет."
    ]
    await update.message.reply_text(
        "✅ Ставка сохранена!\n\nШаг 6 из 7: Опишите ваш опыт и услуги (до 200 символов) 📝\n\n"
        f"Примеры описаний:\n• {examples[0]}\n• {examples[1]}\n• {examples[2]}",
        reply_markup=ReplyKeyboardRemove()
    )
    return BECOME_NANNY_DESC

async def enhanced_nanny_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text.strip()
    if len(description) > 200:
        await update.message.reply_text("⚠️ Описание слишком длинное. Сократите до 200 символов.")
        return BECOME_NANNY_DESC

    context.user_data["nanny_info"]["description"] = description
    await update.message.reply_text(
        "✅ Описание сохранено!\n\nШаг 7 из 7: Последний шаг! Придумайте пароль для входа в систему 🔐\n(минимум 4 символа)"
    )
    return BECOME_NANNY_PASSWORD

async def enhanced_nanny_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    if len(password) < 4:
        await update.message.reply_text("⚠️ Пароль должен содержать минимум 4 символа. Попробуйте ещё раз:")
        return BECOME_NANNY_PASSWORD

    context.user_data["nanny_info"]["password"] = password
    user_id = update.effective_user.id

    from data.database import add_nanny, update_user_type
    add_nanny(user_id, context.user_data["nanny_info"])
    update_user_type(user_id, "nanny")

    success_message = (
        "🎊 РЕГИСТРАЦИЯ ЗАВЕРШЕНА! 🎊\n"
        "---------------------\n\n"
        "✅ Ваш профиль няни успешно создан!\n\n"
        "Что дальше:\n"
        "• /myinfo — просмотр вашего профиля\n"
        "• /login — вход в систему\n"
        "• /my_bookings — ваши заказы\n\n"
        "Желаем успешной работы! 🌟"
    )
    await update.message.reply_text(success_message)
    return ConversationHandler.END


enhanced_nanny_registration_conv = ConversationHandler(
    entry_points=[CommandHandler("become_nanny", enhanced_nanny_registration)],
    states={
        BECOME_NANNY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_nanny_name)],
        BECOME_NANNY_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_nanny_city)],
        BECOME_NANNY_EXP: [MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_nanny_exp)],
        BECOME_NANNY_PETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_nanny_pets)],
        BECOME_NANNY_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_nanny_rate)],
        BECOME_NANNY_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_nanny_desc)],
        BECOME_NANNY_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_nanny_password)],
    },
    fallbacks=[
        CommandHandler("cancel", registration_cancel),
        CallbackQueryHandler(cancel_registration_callback, pattern="^cancel_registration$")
    ],
    name="enhanced_nanny_registration_conv",
    persistent=False,
)
