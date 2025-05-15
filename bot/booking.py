from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from data.database import get_nanny, add_booking, update_booking_status
import datetime

BOOKING_DATE, BOOKING_TIME, BOOKING_DURATION, BOOKING_PET_DETAILS, BOOKING_ADDRESS, BOOKING_CONFIRM = range(6)

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
 
    query = update.callback_query
    await query.answer()
    
    nanny_id = int(query.data.split('_')[1])
    nanny = get_nanny(nanny_id)
    
    if not nanny:
        await query.edit_message_text("Информация о няне не найдена.")
        return ConversationHandler.END
    
   
    context.user_data['booking_nanny_name'] = nanny['name']
    
 
    await query.edit_message_text(
        f"Вы бронируете {nanny['name']} из {nanny['city']}.\n\n"
        f"Введите дату в формате ДД.ММ.ГГГГ (например, 15.04.2025):"
    )
    return BOOKING_DATE

async def booking_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text
    try:
        booking_date = datetime.datetime.strptime(date_text, "%d.%m.%Y").date()
        
      
        if booking_date < datetime.datetime.now().date():
            await update.message.reply_text(
                "Выбранная дата уже прошла. Пожалуйста, выберите будущую дату:"
            )
            return BOOKING_DATE
        
       
        context.user_data['booking_date'] = booking_date
        
        await update.message.reply_text(
            "Введите время начала (в формате ЧЧ:ММ, например 14:30):"
        )
        return BOOKING_TIME
        
    except ValueError:
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ (например, 15.04.2025):"
        )
        return BOOKING_DATE

async def booking_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_text = update.message.text
    try:
        time_obj = datetime.datetime.strptime(time_text, "%H:%M").time()
        booking_date = context.user_data['booking_date']
        start_datetime = datetime.datetime.combine(booking_date, time_obj)
        if start_datetime < datetime.datetime.now():
            await update.message.reply_text(
                "Выбранное время уже прошло. Пожалуйста, выберите будущее время:"
            )
            return BOOKING_TIME
    
        context.user_data['booking_start_time'] = start_datetime
        
        keyboard = [
            ['1 час', '2 часа', '3 часа'],
            ['4 часа', '6 часов', '8 часов'],
            ['Другое']
        ]
       
        await update.message.reply_text(
            "Выберите продолжительность услуги:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return BOOKING_DURATION
      
    except ValueError:
        await update.message.reply_text(
            "Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ (например, 14:30):"
        )
        return BOOKING_TIME
        
async def booking_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    duration_text = update.message.text
    
 
    if duration_text == 'Другое':
        await update.message.reply_text(
            "Введите количество часов (например, 5):",
            reply_markup=ReplyKeyboardRemove()
        )
        return BOOKING_DURATION
    
    
    try:
        if 'час' in duration_text:
            hours = int(duration_text.split()[0])
        else:
            hours = int(duration_text)
        
        if hours <= 0 or hours > 24:
            await update.message.reply_text(
                "Продолжительность должна быть от 1 до 24 часов. Пожалуйста, выберите снова:"
            )
            return BOOKING_DURATION
        
        
        start_time = context.user_data['booking_start_time']
        end_time = start_time + datetime.timedelta(hours=hours)
        
      
        context.user_data['booking_end_time'] = end_time
        context.user_data['booking_duration'] = hours
        
       
        await update.message.reply_text(
            "Опишите вашего питомца (вид, порода, возраст, особенности):",
            reply_markup=ReplyKeyboardRemove()
        )
        return BOOKING_PET_DETAILS
        
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректное число часов."
        )
        return BOOKING_DURATION

async def booking_pet_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
   
    pet_details = update.message.text
    
   
    if len(pet_details) < 5:
        await update.message.reply_text(
            "Пожалуйста, предоставьте более подробное описание вашего питомца:"
        )
        return BOOKING_PET_DETAILS
    
 
    context.user_data['booking_pet_details'] = pet_details
    
   
    await update.message.reply_text(
        "Введите адрес, куда няня должна прибыть:"
    )
    return BOOKING_ADDRESS

async def booking_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка адреса"""
    address = update.message.text
    
  
    if len(address) < 5:
        await update.message.reply_text(
            "Пожалуйста, введите полный адрес:"
        )
        return BOOKING_ADDRESS
    
  
    context.user_data['booking_address'] = address
    
 
    nanny_name = context.user_data['booking_nanny_name']
    start_time = context.user_data['booking_start_time'].strftime("%d.%m.%Y %H:%M")
    end_time = context.user_data['booking_end_time'].strftime("%d.%m.%Y %H:%M")
    duration = context.user_data['booking_duration']
    pet_details = context.user_data['booking_pet_details']
    
    
    nanny_id = context.user_data['booking_nanny_id']
    nanny = get_nanny(nanny_id)
    hourly_rate = nanny['hourly_rate']
    total_cost = hourly_rate * duration
    
    summary = (
        f"📋 Сводка заказа:\n\n"
        f"👤 Няня: {nanny_name}\n"
        f"🕒 Начало: {start_time}\n"
        f"⏱️ Продолжительность: {duration} часов\n"
        f"🕒 Окончание: {end_time}\n"
        f"🐾 Питомец: {pet_details}\n"
        f"📍 Адрес: {address}\n"
        f"💰 Стоимость: {total_cost} ₸ ({hourly_rate} ₸/час × {duration} ч)\n\n"
        "Подтвердите заказ:"
    )
    
   
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="booking_confirm")],
        [InlineKeyboardButton("❌ Отменить", callback_data="booking_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(summary, reply_markup=reply_markup)
    return BOOKING_CONFIRM

async def booking_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "booking_confirm":
   
        owner_id = update.effective_user.id
        nanny_id = context.user_data['booking_nanny_id']
        start_time = context.user_data['booking_start_time']
        end_time = context.user_data['booking_end_time']
        pet_details = context.user_data['booking_pet_details']
        address = context.user_data['booking_address']
        
        booking_id = add_booking(owner_id, nanny_id, start_time, end_time, pet_details, address)
        
        await query.edit_message_text(
            f"🎉 Заказ #{booking_id} успешно создан!\n\n"
            "Няня получит уведомление о вашем заказе и свяжется с вами в ближайшее время.\n"
            "Вы можете просмотреть свои заказы через /my_bookings."
        )
    else:
        await query.edit_message_text(
            "Заказ отменен."
        )
    
   
    for key in list(context.user_data.keys()):
        if key.startswith('booking_'):
            del context.user_data[key]
    
    return ConversationHandler.END

async def booking_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена процесса бронирования"""
    await update.message.reply_text(
        "Бронирование отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
    
   
    for key in list(context.user_data.keys()):
        if key.startswith('booking_'):
            del context.user_data[key]
    
    return ConversationHandler.END


booking_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_booking, pattern=r'^book_\d+$')],
    states={
        BOOKING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_date)],
        BOOKING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_time)],
        BOOKING_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_duration)],
        BOOKING_PET_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_pet_details)],
        BOOKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, booking_address)],
        BOOKING_CONFIRM: [CallbackQueryHandler(booking_confirm, pattern=r'^booking_\w+$')]
    },
    fallbacks=[CommandHandler('cancel', booking_cancel)]
)