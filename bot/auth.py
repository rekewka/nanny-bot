from __future__ import annotations
import datetime
from zoneinfo import ZoneInfo

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove,
                      Update)
from telegram.ext import (CallbackQueryHandler, CommandHandler, ConversationHandler,
                          ContextTypes, MessageHandler, filters)

from data.database import get_nanny, verify_login


LOGIN_USERNAME, LOGIN_PASSWORD = range(2)
MAX_ATTEMPTS = 5           
BLOCK_MINUTES = 5         


async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(tz=ZoneInfo("Asia/Almaty"))
    block_until: datetime.datetime | None = context.user_data.get("login_block_until")

    if block_until and now < block_until:
        minutes_left = int((block_until - now).total_seconds() // 60) + 1
        await update.message.reply_text(
            f" Слишком много попыток входа. Попробуйте снова через {minutes_left} мин.")
        return ConversationHandler.END

    await update.message.reply_text("Введите *username*, указанный при регистрации:",
                                    parse_mode="Markdown")
    return LOGIN_USERNAME


async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["login_username"] = update.message.text.strip()
    await update.message.reply_text("Введите пароль:")
    return LOGIN_PASSWORD


async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username: str = context.user_data.get("login_username", "")
    password: str = update.message.text
    attempts = context.user_data.get("login_attempts", 0) + 1
    context.user_data["login_attempts"] = attempts
    user_id = verify_login(username, password)
    if user_id:
        nanny = get_nanny(user_id)
        if nanny:
            for k in ("login_username", "login_attempts", "login_block_until"):
                context.user_data.pop(k, None)

            context.user_data.update({
                "logged_in": True,
                "nanny_id": user_id,
            })

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 Мой профиль", callback_data="goto_myinfo")],
                [InlineKeyboardButton("📑 Мои заказы", callback_data="goto_bookings")],
            ])
            await update.message.reply_text(
                f"Добро пожаловать, {nanny['name']}!",
                reply_markup=keyboard,
            )
            return ConversationHandler.END

        await update.message.reply_text("Не удалось получить профиль няни. Попробуйте позже.")
        return ConversationHandler.END


    if attempts >= MAX_ATTEMPTS:
        block_until = datetime.datetime.now(tz=ZoneInfo("Asia/Almaty")) + datetime.timedelta(minutes=BLOCK_MINUTES)
        context.user_data["login_block_until"] = block_until
        await update.message.reply_text(
            "Превышено количество попыток. Вход заблокирован на 5 минут.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Неверный логин или пароль. Попробуйте ещё раз или /cancel.")
    return LOGIN_USERNAME

async def login_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Вход отменён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def quick_nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "goto_myinfo":
        await query.message.chat.send_message("/myinfo")  
    elif data == "goto_bookings":
        await query.message.chat.send_message("/my_bookings")

login_conv = ConversationHandler(
    entry_points=[CommandHandler("login", login_start)],
    states={
        LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
        LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
    },
    fallbacks=[CommandHandler("cancel", login_cancel)],
    name="login_conv",
    persistent=False,
)
quick_nav_cb = CallbackQueryHandler(quick_nav_handler, pattern=r"^goto_")
