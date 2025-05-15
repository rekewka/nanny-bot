from __future__ import annotations

import math
from typing import Sequence

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.ext import (CallbackQueryHandler, CommandHandler, ContextTypes,
                          ConversationHandler, MessageHandler, filters)

from data.database import get_all_nannies

# ────────────────────────────────────────────────────────────────────────────────
#  Conversation states
# ────────────────────────────────────────────────────────────────────────────────
SEARCH_CITY, SEARCH_PET_TYPE, SEARCH_MIN_RATING, SHOW_RESULTS = range(4)
PAGE_SIZE = 10

# ────────────────────────────────────────────────────────────────────────────────
#  Utils
# ────────────────────────────────────────────────────────────────────────────────

def _build_inline_list(nannies: Sequence[dict], page: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"{n['name']} ({n['city']})", callback_data=f"nanny_{n['user_id']}")]
        for n in nannies
    ]
    pages = math.ceil(len(nannies) / PAGE_SIZE)
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"srch_page_{page-1}"))
    if page < pages - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"srch_page_{page+1}"))
    if nav_row:
        buttons.append(nav_row)
    return InlineKeyboardMarkup(buttons)

# ────────────────────────────────────────────────────────────────────────────────
#  Handlers
# ────────────────────────────────────────────────────────────────────────────────
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["search_params"] = {}
    keyboard = [
        ["Алматы", "Астана"],
        ["Шымкент", "Караганда", "Оскемен"],
        ["Любой город"],
    ]
    await update.message.reply_text(
        "🔍 *Поиск нянь*\n\nВыберите город или введите свой:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown",
    )
    return SEARCH_CITY

async def search_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    if city != "Любой город":
        context.user_data["search_params"]["city"] = city

    keyboard = [
        ["🐶 Собаки", "🐱 Кошки"],
        ["🐦 Птицы", "🐹 Грызуны"],
        ["🐠 Рыбки", "🦎 Рептилии"],
        ["Любой питомец"],
    ]
    await update.message.reply_text(
        "Выберите тип питомца:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return SEARCH_PET_TYPE

async def search_pet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice != "Любой питомец":
        pet_type = choice.split()[-1].strip("🐶🐱🐦🐹🐠🦎")
        context.user_data["search_params"]["pet_type"] = pet_type

    keyboard = [
        ["⭐⭐⭐⭐⭐ (5)", "⭐⭐⭐⭐ (4+)"],
        ["⭐⭐⭐ (3+)", "⭐⭐ (2+)"],
        ["Любой рейтинг"],
    ]
    await update.message.reply_text(
        "Минимальный рейтинг няни:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return SEARCH_MIN_RATING

async def search_min_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if "Любой" not in choice:
        import re
        match = re.search(r"\d+", choice)
        if match:
            context.user_data["search_params"]["min_rating"] = float(match.group())

    params = context.user_data["search_params"]
    nannies = get_all_nannies(
        params.get("city"), params.get("pet_type"), params.get("min_rating")
    )

    if not nannies:
        await update.message.reply_text(
            "😔 Нянь не найдено. Попробуйте изменить параметры /search.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    context.user_data["search_results"] = nannies
    context.user_data["search_page"] = 0
    await _show_results(update, context, first=True)
    return SHOW_RESULTS


async def _show_results(update: Update, context: ContextTypes.DEFAULT_TYPE, *, first=False):
    nannies: list = context.user_data["search_results"]
    page: int = context.user_data["search_page"]

    chunk = nannies[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    text = f"🔍 Результаты (стр. {page + 1}/{math.ceil(len(nannies)/PAGE_SIZE)}):\n\n"
    for idx, n in enumerate(chunk, 1 + page * PAGE_SIZE):
        stars = "⭐" * int(n["rating"]) if n["rating"] else "Нет отзывов"
        text += (
            f"{idx}. {n['name']}, {n['city']}\n"
            f"   {stars} | {n['hourly_rate']} ₸/ч\n\n"
        )
    markup = _build_inline_list(chunk, page)

    if first:
        await update.message.reply_text(text, reply_markup=markup)
    else:
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=markup)

async def paginate_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split("_")[-1])
    context.user_data["search_page"] = page
    await _show_results(update, context)

async def search_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Поиск отменён.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


search_conv = ConversationHandler(
    entry_points=[CommandHandler("search", search_start)],
    states={
        SEARCH_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_city)],
        SEARCH_PET_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_pet_type)],
        SEARCH_MIN_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_min_rating)],
        SHOW_RESULTS: [CallbackQueryHandler(paginate_results, pattern=r"^srch_page_\\d+$")],
    },
    fallbacks=[CommandHandler("cancel", search_cancel)],
    name="search_conv",
    persistent=False,
)
