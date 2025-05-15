from __future__ import annotations

import math
from typing import Callable, List, Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackQueryHandler, CommandHandler, ContextTypes,
                          ConversationHandler)

from data.database import (add_user, delete_nanny, get_all_nannies, get_nanny,
                           get_nanny_bookings, get_owner_bookings)


NANNIES_PER_PAGE = 10


def _paginate(items: Sequence, page: int, per_page: int) -> Sequence:
    start = page * per_page
    return items[start : start + per_page]


def _nanny_card(nanny: dict, idx: int) -> str:
    stars = "⭐" * int(nanny["rating"]) if nanny["rating"] else "Нет отзывов"
    pet_types = ", ".join(nanny["pet_types"]) if nanny["pet_types"] else "Все"
    return (
        f"{idx}. {nanny['name']}, {nanny['city']}\n"
        f"   Опыт: {nanny['experience']} лет | Рейтинг: {stars}\n"
        f"   🐾 {pet_types}\n"
        f"   💰 {nanny['hourly_rate']} ₸/ч\n\n"
    )


def _build_nanny_buttons(nannies: Sequence[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"{n['name']} ({n['city']})", callback_data=f"nanny_{n['user_id']}")]
        for n in nannies
    ]
    return InlineKeyboardMarkup(buttons)

def require_nanny(func: Callable):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not get_nanny(user_id):
            await update.message.reply_text("⛔️ У вас нет профиля няни. Используйте /become_nanny.")
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username or user.first_name)

    text = (
        f"Привет, {user.first_name}! Я бот для поиска нянь для питомцев.\n\n"
        "Доступные команды:\n"
        " /view_nannies  — список нянь\n"
        " /become_nanny  — зарегистрироваться как няня\n"
        " /login         — войти как няня\n"
        " /logout        — выйти из системы\n"
        " /myinfo        — мой профиль\n"
        " /my_bookings   — мои заказы\n"
        " /search        — поиск нянь по параметрам\n"
        " /help          — помощь\n"
        " /delete_me     — удалить профиль няни\n"
    )
    await update.message.reply_text(text)

async def view_nannies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = int(context.args[0]) if context.args else 0
    nannies = get_all_nannies()
    if not nannies:
        await update.message.reply_text("К сожалению, пока нет доступных нянь.")
        return

    pages = math.ceil(len(nannies) / NANNIES_PER_PAGE)
    page = max(0, min(page, pages - 1))

    chunk = _paginate(nannies, page, NANNIES_PER_PAGE)
    text = "📋 Доступные няни (стр. {}/{}):\n\n".format(page + 1, pages)
    for i, nanny in enumerate(chunk, 1 + page * NANNIES_PER_PAGE):
        text += _nanny_card(nanny, i)

    reply_markup = _build_nanny_buttons(chunk)

    
    nav_buttons: List[InlineKeyboardButton] = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"nanny_page_{page-1}"))
    if page < pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"nanny_page_{page+1}"))
    if nav_buttons:
        reply_markup.inline_keyboard.append(nav_buttons)

    await update.message.reply_text(text, reply_markup=reply_markup)


async def nanny_page_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[-1])
    context.args = [str(page)]
    await view_nannies(query, context)  

async def nanny_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nanny_id = int(query.data.split("_")[1])
    nanny = get_nanny(nanny_id)
    if not nanny:
        await query.edit_message_text("Информация о няне не найдена.")
        return

    stars = "⭐" * int(nanny["rating"]) if nanny["rating"] else "Нет отзывов"
    pet_types = ", ".join(nanny["pet_types"]) if nanny["pet_types"] else "Все"

    text = (
        f"{nanny['name']} из {nanny['city']}\n\n"
        f"Опыт: {nanny['experience']} лет\n"
        f"Рейтинг: {stars}\n"
        f"Питомцы: {pet_types}\n"
        f"Цена: {nanny['hourly_rate']} ₸/час\n\n"
        f"{nanny['description']}\n"
    )

    buttons = [
        [InlineKeyboardButton("Забронировать", callback_data=f"book_{nanny_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="nanny_page_0")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))


@require_nanny
async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nanny = get_nanny(update.effective_user.id)
    stars = "⭐" * int(nanny["rating"]) if nanny["rating"] else "Нет отзывов"
    pet_types = ", ".join(nanny["pet_types"]) if nanny["pet_types"] else "Все"

    text = (
        "📄 Ваш профиль няни:\n\n"
        f"Имя: {nanny['name']}\n"
        f"Город: {nanny['city']}\n"
        f"Опыт: {nanny['experience']} лет\n"
        f"Рейтинг: {stars}\n"
        f"Питомцы: {pet_types}\n"
        f"Ставка: {nanny['hourly_rate']} ₸/ч\n"
        f"Статус: {'Доступен' if nanny['available'] else 'Недоступен'}\n\n"
        f"{nanny['description']}"
    )
    await update.message.reply_text(text)


async def my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_nanny = bool(get_nanny(user_id))

    if is_nanny:
        bookings = get_nanny_bookings(user_id)
        role_text = "няни"
    else:
        bookings = get_owner_bookings(user_id)
        role_text = "владельца питомца"

    if not bookings:
        await update.message.reply_text(f"У вас пока нет заказов ({role_text}).")
        return

    text = f"📑 Ваши заказы ({role_text}):\n\n"
    for b in bookings:
        start = b["start_time"].strftime("%d.%m.%Y %H:%M")
        end = b["end_time"].strftime("%d.%m.%Y %H:%M")
        text += (
            f"#{b['id']}  {start} — {end}\n"
            f"Статус: {b['status']}\n"
            f"Адрес: {b['address']}\n"
            f"Питомец: {b['pet_details']}\n\n"
        )
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐾 *Помощь*\n\n"
        "• /view_nannies — список нянь с фильтрами\n"
        "• /search      — расширенный поиск\n"
        "• /my_bookings — ваши заказы\n"
        "• /become_nanny — стать няней\n"
        "• /login /logout — авторизация няни\n",
        parse_mode="Markdown",
    )


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Вы вышли из системы.")


@require_nanny
async def delete_my_nanny_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_nanny(update.effective_user.id)
    await update.message.reply_text("Ваш профиль няни удалён. Вы всегда можете зарегистрироваться заново через /become_nanny.")



def get_command_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("view_nannies", view_nannies),
        CallbackQueryHandler(nanny_page_handler, pattern=r"^nanny_page_\\d+$"),
        CallbackQueryHandler(nanny_details, pattern=r"^nanny_\\d+$"),
        CommandHandler("myinfo", myinfo),
        CommandHandler("my_bookings", my_bookings),
        CommandHandler("help", help_command),
        CommandHandler("logout", logout),
        CommandHandler("delete_me", delete_my_nanny_profile),
    ]
