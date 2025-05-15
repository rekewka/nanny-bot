from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (CommandHandler, ContextTypes, ConversationHandler,
                          MessageHandler, filters)
from datetime import datetime
from data.database import add_booking

ASK_START_DATE, ASK_END_DATE, ASK_ADDRESS, ASK_PET_DETAILS = range(4)

async def book_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Пожалуйста, укажите ID няни. Пример: /book 123")
        return ConversationHandler.END

    context.user_data['booking'] = {
        'nanny_id': int(args[0]),
        'owner_id': update.effective_user.id
    }
    await update.message.reply_text("Введите дату начала (в формате ГГГГ-ММ-ДД):")
    return ASK_START_DATE

async def ask_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        start = datetime.strptime(update.message.text.strip(), "%Y-%m-%d")
        context.user_data['booking']['start_time'] = start
        await update.message.reply_text("Введите дату окончания (в формате ГГГГ-ММ-ДД):")
        return ASK_END_DATE
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату как ГГГГ-ММ-ДД")
        return ASK_START_DATE

async def ask_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        end = datetime.strptime(update.message.text.strip(), "%Y-%m-%d")
        context.user_data['booking']['end_time'] = end
        await update.message.reply_text("Введите адрес, где будет проходить уход за питомцем:")
        return ASK_ADDRESS
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату как ГГГГ-ММ-ДД")
        return ASK_END_DATE

async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['booking']['address'] = update.message.text.strip()
    await update.message.reply_text("Опишите питомца (порода, особенности, кормление и т.д.):")
    return ASK_PET_DETAILS

async def ask_pet_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['booking']['pet_details'] = update.message.text.strip()
    context.user_data['booking']['status'] = 'pending'
    context.user_data['booking']['created_at'] = datetime.now()

    # сохранить в БД
    add_booking(context.user_data['booking'])

    await update.message.reply_text(
        "✅ Заявка создана и отправлена няне. Ожидайте подтверждения!",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Заявка отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

book_nanny_conv = ConversationHandler(
    entry_points=[CommandHandler("book", book_command)],
    states={
        ASK_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_start_date)],
        ASK_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_end_date)],
        ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_address)],
        ASK_PET_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pet_details)],
    },
    fallbacks=[CommandHandler("cancel", cancel_booking)],
    name="book_nanny_conv",
    persistent=False
)
