import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def enhanced_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    from data.database import add_user
    add_user(user.id, user.username or user.first_name)

    # Welcome messages with random greeting
    greetings = ["👋 Салем", "🌟 Привет", "✨ Здравствуйте", "🎉 Қош келдіңіз"]
    greeting = random.choice(greetings)
    
    welcome_text = (
    f"{greeting}, {user.first_name}!\n\n"
    "🐾 *NANNY BOT* 🐾\n"
    "---------------------\n"  # заменили линию
    "Ваш надежный помощник для ухода за питомцами!\n\n"
    "Мы поможем найти идеальную няню для вашего питомца или стать няней и зарабатывать, делая то, что вы любите!\n\n"
    "Выберите, как вы хотите продолжить:"
)

    
    # Create inline keyboard for the main options
    keyboard = [
    [InlineKeyboardButton("🔍 Найти няню", callback_data="find_nanny")],
    [InlineKeyboardButton("📅 Сделать заказ", callback_data="cmd_book")],
    [InlineKeyboardButton("📋 Мои заказы", callback_data="my_bookings")],
    [InlineKeyboardButton("👤 Стать няней", callback_data="become_nanny")],
    [InlineKeyboardButton("ℹ️ О сервисе", callback_data="about_service")],
    [InlineKeyboardButton("❓ Помощь", callback_data="help")]
]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = update.message or update.callback_query.message
    await message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# Handle button callbacks from the start menu
async def start_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "find_nanny":
        text = (
            "🔍 *Поиск няни для питомца*\n\n"
            "У нас есть несколько способов найти идеальную няню:\n\n"
            "• /view_nannies — просмотр всех доступных нянь\n"
            "• /search — расширенный поиск по параметрам\n\n"
            "Также вы можете воспользоваться нашими командами:"
        )
        
        commands_keyboard = [
            [InlineKeyboardButton("🐾 Все няни", callback_data="cmd_view_nannies")],
            [InlineKeyboardButton("🔍 Поиск", callback_data="cmd_search")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(commands_keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif query.data == "become_nanny":
        text = (
            "👤 *Станьте няней для питомцев*\n\n"
            "Любите животных и хотите зарабатывать?\n"
            "Зарегистрируйтесь как няня и начните принимать заказы!\n\n"
            "• Сами устанавливаете цены\n"
            "• Выбираете типы питомцев\n"
            "• Гибкий график работы\n\n"
            "Нажмите кнопку ниже, чтобы начать регистрацию:"
        )
        
        nanny_keyboard = [
            [InlineKeyboardButton("✅ Зарегистрироваться", callback_data="cmd_become_nanny")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(nanny_keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif query.data == "about_service":
        text = (
            "ℹ️ *О нашем сервисе*\n\n"
            "🐾 *NANNY BOT* — это платформа, которая соединяет:\n\n"
            "• Владельцев, которым нужен присмотр за питомцами\n"
            "• Профессиональных нянь с опытом работы\n\n"
            "Наши преимущества:\n"
            "✅ Проверенные няни\n"
            "✅ Удобный поиск\n"
            "✅ Прозрачная система отзывов\n"
            "✅ Безопасная оплата\n\n"
            "Присоединяйтесь к нам сегодня!"
        )
        
        about_keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(about_keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif query.data == "help":
        text = (
            "❓ *Помощь и команды*\n\n"
            "Основные команды:\n"
            "• /start — главное меню\n"
            "• /view_nannies — список нянь\n"
            "• /search — поиск нянь\n"
            "• /become_nanny — стать няней\n"
            "• /login — вход для нянь\n"
            "• /my_bookings — ваши заказы\n"
            "• /myinfo — ваш профиль\n"
            "• /delete_me — удалить профиль\n\n"
            "Нужна дополнительная помощь? Свяжитесь с нами через @beknur_10"
        )
        
        help_keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(help_keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    elif query.data == "back_to_start":
        # Return to main menu
        await enhanced_start(update, context)
    
    elif query.data == "cmd_view_nannies":
        # Execute the view_nannies command
        from bot.commands import view_nannies
        await view_nannies(query, context)
    
    elif query.data == "cmd_search":
        # Send message to start search conversation
        await query.edit_message_text(
            "🔍 *Поиск няни по параметрам*\n\n"
            "Для начала поиска введите команду /search",
            
        )
    
    elif query.data == "cmd_become_nanny":
        # Send message to start nanny registration
        await query.edit_message_text(
            "👤 *Регистрация няни*\n\n"
            "Для начала регистрации введите команду /become_nanny",
           
        )

    elif query.data == "cmd_book":
        await query.edit_message_text(
            "📅 *Создание заказа*\n\n"
            "Чтобы создать заказ, введите:\n"
            "`/book <ID няни>`\n\n"
            "Например: `/book 12345678`\n"
            "Где 12345678 — это ID няни (отображается при поиске).",
            parse_mode="Markdown"
        )

    elif query.data == "my_bookings":
        from bot.commands import my_bookings
        await my_bookings(query, context)