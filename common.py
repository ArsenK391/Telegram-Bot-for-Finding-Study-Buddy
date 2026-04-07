from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from config import MAX_MATCHES
from .registration import CHOOSING_NAME


# /start 

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user = db.get_user(update.effective_user.id)
    if user:
        await update.message.reply_text(
            f"Welcome back, *{user['display_name']}*! 👋\n\n"
            "Your profile is already set up.\n"
            "• /find — discover study buddies\n"
            "• /profile — view your profile\n"
            "• /start — re-run setup to update your preferences",
            parse_mode="Markdown",
        )
        # Allow re-registration to update preferences
    else:
        await update.message.reply_text(
            "👋 *Welcome to Study Buddy Bot!*\n\n"
            "I connect students who share the same subjects so you can learn together.\n\n"
            "Let's set up your profile. What's your name?",
            parse_mode="Markdown",
        )
    return CHOOSING_NAME


# /help

async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "*📖 Study Buddy Bot — Help*\n\n"
        "/start — create or update your profile\n"
        "/find — find students with matching subjects\n"
        "/profile — view your current profile\n"
        "/cancel — cancel the current action\n"
        "/help — show this message\n\n"
        "_Tip: use /find after setting up your profile to get matched!_",
        parse_mode="Markdown",
    )


# /profile 

async def profile_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    user = db.get_user(uid)

    if not user:
        await update.message.reply_text(
            "You don't have a profile yet. Use /start to create one!"
        )
        return

    subjects = db.get_subjects(uid)
    connections = db.get_connections(uid)

    avail_label = {"mornings": "🌅 Mornings", "evenings": "🌆 Evenings",
                   "weekends": "📅 Weekends",  "flexible": "🕐 Flexible"}.get(
        user["availability"], user["availability"].capitalize()
    )

    text = (
        f"👤 *{user['display_name']}*"
        + (f" (@{user['username']})" if user["username"] else "") + "\n\n"
        f"📚 *Subjects:* {', '.join(subjects) if subjects else 'None'}\n"
        f"🎭 *Role:* {user['role'].capitalize()}\n"
        f"🕐 *Availability:* {avail_label}\n"
        f"🤝 *Connections:* {len(connections)}\n\n"
        "_Use /start to update your profile._"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# /find

async def find_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id

    if not db.get_user(uid):
        await update.message.reply_text(
            "Please set up your profile first with /start."
        )
        return

    matches = db.find_matches(uid, limit=MAX_MATCHES)

    if not matches:
        await update.message.reply_text(
            "😔 No new matches found right now.\n\n"
            "Try adding more subjects via /start, or check back later as more students join!"
        )
        return

    await update.message.reply_text(
        f"🔍 Found *{len(matches)}* potential study buddy{'s' if len(matches) > 1 else ''}!\n\n"
        "Here they are 👇",
        parse_mode="Markdown",
    )

    for match in matches:
        await _send_match_card(update, match)


async def _send_match_card(update: Update, match) -> None:
    avail_label = {"mornings": "🌅 Mornings", "evenings": "🌆 Evenings",
                   "weekends": "📅 Weekends",  "flexible": "🕐 Flexible"}.get(
        match["availability"], match["availability"].capitalize()
    )
    shared = match["shared_subjects"]

    handle = f"@{match['username']}" if match["username"] else "_no username set_"

    text = (
        f"👤 *{match['display_name']}* ({handle})\n"
        f"🎭 Role: {match['role'].capitalize()}\n"
        f"🕐 Available: {avail_label}\n"
        f"📚 Shared subjects ({match['shared_count']}): {shared}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤝 Connect", callback_data=f"connect_{match['user_id']}"),
            InlineKeyboardButton("⏭ Skip",    callback_data=f"skip_{match['user_id']}"),
        ]
    ])

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


# /cancel

async def cancel_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❌ Action cancelled. Use /help to see available commands."
    )
    return ConversationHandler.END


# Global callback router 

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    uid  = update.effective_user.id

    if data.startswith("connect_"):
        target_id = int(data[len("connect_"):])
        db.record_connection(uid, target_id, "connected")

        target = db.get_user(target_id)
        name   = target["display_name"] if target else "that user"
        handle = f"@{target['username']}" if target and target["username"] else name

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"✅ *Connected with {name}!*\n\n"
            f"Reach out directly: {handle}\n\n"
            "_Good luck studying together! 📚_",
            parse_mode="Markdown",
        )

    elif data.startswith("skip_"):
        target_id = int(data[len("skip_"):])
        db.record_connection(uid, target_id, "skipped")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("⏭ Skipped. Use /find to see more matches.")
