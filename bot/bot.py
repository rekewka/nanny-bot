import logging
import sys
import asyncio
import signal
import platform
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from telegram.request import HTTPXRequest
from config import TELEGRAM_TOKEN
from data.database import init_db, pg_pool
from bot.commands import get_command_handlers
from bot.enhanced_start import enhanced_start, start_button_handler
from bot.enhanced_registration import (
    enhanced_nanny_registration, enhanced_nanny_registration_conv,
    cancel_registration_callback
)
from bot.conversation import registration_conv, registration_cancel
from bot.auth import login_conv, quick_nav_cb
from bot.booking import booking_conv
from bot.booking_conversation import book_nanny_conv
from bot.search import search_conv

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

async def _shutdown(app):
    logging.info("Shutting down application …")
    await app.shutdown()
    pg_pool.closeall()
    await app.stop()
    logging.info("Bye! 👋")

def main() -> None:
    init_db()
    request = HTTPXRequest(connect_timeout=30, read_timeout=30)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).request(request).build()
    
    # Replace the start command with our enhanced version
    app.add_handler(CommandHandler("start", enhanced_start))
    app.add_handler(CallbackQueryHandler(start_button_handler, pattern="^(find_nanny|become_nanny|about_service|help|back_to_start|cmd_view_nannies|cmd_search|cmd_become_nanny)$"))
    
    # Add the enhanced nanny registration handler
    app.add_handler(enhanced_nanny_registration_conv)
    
    # Add the registration conversation handler (but keep our enhanced start)
    app.add_handler(registration_conv)
    
    # Add the rest of the original handlers
    for h in get_command_handlers():
        # Skip the original start handler as we've replaced it
        if isinstance(h, CommandHandler) and h.callback.__name__ == "start":
            continue
        app.add_handler(h)
    
    # Add remaining original handlers
    app.add_handler(login_conv)
    app.add_handler(quick_nav_cb)
    app.add_handler(booking_conv)
    app.add_handler(search_conv)
    app.add_handler(book_nanny_conv)
    
    if platform.system() != "Windows":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(_shutdown(app)))
    else:
        pass

    print("🚀 Бот запущен! Нажмите Ctrl+C для остановки.")
    try:
        app.run_polling()
    except (KeyboardInterrupt, SystemExit):
        asyncio.run(_shutdown(app))
        sys.exit(0)


if __name__ == "__main__":
    main()