import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from config import BOT_TOKEN
from database import init_db
from handlers import (
    start,
    help_command,
    profile_command,
    find_command,
    cancel_command,
    handle_callback,
    registration,
    CHOOSING_NAME,
    CHOOSING_SUBJECTS,
    CHOOSING_ROLE,
    CHOOSING_AVAILABILITY,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    init_db()
    logger.info("Database initialised.")

    app = Application.builder().token(BOT_TOKEN).build()

    # Registration conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_NAME:         [MessageHandler(filters.TEXT & ~filters.COMMAND, registration.save_name)],
            CHOOSING_SUBJECTS:     [CallbackQueryHandler(registration.toggle_subject, pattern=r"^subj_"),
                                    CallbackQueryHandler(registration.subjects_done,  pattern=r"^subjects_done$")],
            CHOOSING_ROLE:         [CallbackQueryHandler(registration.save_role,      pattern=r"^role_")],
            CHOOSING_AVAILABILITY: [CallbackQueryHandler(registration.save_availability, pattern=r"^avail_")],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help",    help_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("find",    find_command))
    app.add_handler(CommandHandler("cancel",  cancel_command))

    # Inline‑button callbacks outside the conversation (connect / skip)
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot is running…")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
