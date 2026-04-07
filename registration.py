from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from config import SUBJECTS

# Conversation states
CHOOSING_NAME         = 0
CHOOSING_SUBJECTS     = 1
CHOOSING_ROLE         = 2
CHOOSING_AVAILABILITY = 3


# Keyboards 

def _subjects_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    buttons = []
    for subj in SUBJECTS:
        tick = "✅ " if subj in selected else ""
        buttons.append([InlineKeyboardButton(f"{tick}{subj}", callback_data=f"subj_{subj}")])
    buttons.append([InlineKeyboardButton("➡️  Done", callback_data="subjects_done")])
    return InlineKeyboardMarkup(buttons)


ROLE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎓 Tutor",        callback_data="role_tutor")],
    [InlineKeyboardButton("📖 Learner",      callback_data="role_learner")],
    [InlineKeyboardButton("🔄 Both",         callback_data="role_both")],
])

AVAIL_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🌅 Mornings",  callback_data="avail_mornings"),
     InlineKeyboardButton("🌆 Evenings",  callback_data="avail_evenings")],
    [InlineKeyboardButton("📅 Weekends",  callback_data="avail_weekends"),
     InlineKeyboardButton("🕐 Flexible",  callback_data="avail_flexible")],
])


# Step 1 — name

async def save_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name or len(name) > 50:
        await update.message.reply_text("⚠️ Please enter a name between 1 and 50 characters.")
        return CHOOSING_NAME

    ctx.user_data["display_name"] = name
    ctx.user_data.setdefault("selected_subjects", set())

    await update.message.reply_text(
        f"Nice to meet you, *{name}*! 👋\n\nNow pick the subjects you study or teach.\n"
        "Tap a subject to select/deselect it, then press *Done*.",
        parse_mode="Markdown",
        reply_markup=_subjects_keyboard(ctx.user_data["selected_subjects"]),
    )
    return CHOOSING_SUBJECTS


# Step 2 — subjects 

async def toggle_subject(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    subj = query.data[len("subj_"):]
    selected: set[str] = ctx.user_data.setdefault("selected_subjects", set())

    if subj in selected:
        selected.discard(subj)
    else:
        selected.add(subj)

    await query.edit_message_reply_markup(reply_markup=_subjects_keyboard(selected))
    return CHOOSING_SUBJECTS


async def subjects_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    selected: set[str] = ctx.user_data.get("selected_subjects", set())
    if not selected:
        await query.answer("Please select at least one subject!", show_alert=True)
        return CHOOSING_SUBJECTS

    await query.edit_message_text(
        f"Great! You selected: *{', '.join(sorted(selected))}*\n\n"
        "What's your role?",
        parse_mode="Markdown",
        reply_markup=ROLE_KEYBOARD,
    )
    return CHOOSING_ROLE


# Step 3 — role

async def save_role(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    role = query.data[len("role_"):]
    ctx.user_data["role"] = role

    role_label = {"tutor": "🎓 Tutor", "learner": "📖 Learner", "both": "🔄 Both"}[role]

    await query.edit_message_text(
        f"Role set to *{role_label}*.\n\nWhen are you usually available?",
        parse_mode="Markdown",
        reply_markup=AVAIL_KEYBOARD,
    )
    return CHOOSING_AVAILABILITY


# Step 4 — availability

async def save_availability(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    availability = query.data[len("avail_"):]
    ctx.user_data["availability"] = availability

    tg_user = update.effective_user
    display_name = ctx.user_data["display_name"]
    subjects     = list(ctx.user_data["selected_subjects"])
    role         = ctx.user_data["role"]

    # Persist
    db.upsert_user(
        user_id=tg_user.id,
        username=tg_user.username,
        display_name=display_name,
        role=role,
        availability=availability,
    )
    db.set_subjects(tg_user.id, subjects)

    avail_label = {"mornings": "🌅 Mornings", "evenings": "🌆 Evenings",
                   "weekends": "📅 Weekends",  "flexible": "🕐 Flexible"}[availability]

    await query.edit_message_text(
        f"✅ *Profile saved!*\n\n"
        f"👤 Name: {display_name}\n"
        f"📚 Subjects: {', '.join(sorted(subjects))}\n"
        f"🎭 Role: {role.capitalize()}\n"
        f"🕐 Availability: {avail_label}\n\n"
        "Use /find to discover study buddies, or /help for all commands.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END
