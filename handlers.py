from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from zoneinfo import ZoneInfo
import datetime
import db
import shlex

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send simple welcome message"""
    help_text = (
        "💊 Pill Reminder Bot\n\n"
        "📋 Commands:\n\n"
        "/add_reminder [HH:MM...] [Timezone] \"Reminder Name\"\n"
        "Example: /add_reminder 08:00 20:00 America/New_York \"Daily Pills\"\n\n"
        "/show_reminders - List active reminders\n"
        "/remove_reminder - Delete a reminder\n\n"
        "Click buttons to mark reminders as done ✅"
    )
    await update.message.reply_text(help_text)

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reminder creation without formatting"""
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command works only in group chats!")
        return

    try:
        args = shlex.split(' '.join(context.args))
    except:
        await update.message.reply_text("❌ Invalid arguments! Use quotes for names.")
        return

    # Parse name
    name = "Medication Reminder"
    for i in reversed(range(len(args))):
        if ' ' in args[i]:
            name = args.pop(i).strip('"')
            break

    # Parse timezone
    timezone = db.DEFAULT_TZ
    if args:
        try:
            ZoneInfo(args[-1])
            timezone = args.pop()
        except:
            pass

    # Validate times
    valid_times = []
    for t in args:
        try:
            datetime.datetime.strptime(t, "%H:%M")
            valid_times.append(t)
        except:
            await update.message.reply_text(f"❌ Invalid time format: {t}")
            return

    if not valid_times:
        await update.message.reply_text("❗ Please specify at least one time!")
        return

    # Save to database
    chat_id = update.effective_chat.id
    db.add_reminder(chat_id, valid_times, timezone, name)
    
    # Schedule jobs
    reminder_id = db.get_last_reminder_id(chat_id)
    for time_str in valid_times:
        hour, minute = map(int, time_str.split(':'))
        time = datetime.time(hour, minute, tzinfo=ZoneInfo(timezone))
        context.job_queue.run_daily(
            send_reminder,
            time,
            data={'reminder_id': reminder_id},
            name=f"reminder_{reminder_id}_{time_str}"
        )

    # Plain text response
    response = (
        "✅ New reminder added:\n"
        f"🕒 Times: {', '.join(valid_times)}\n"
        f"🌍 Timezone: {timezone}\n"
        f"📝 Name: {name}"
    )
    await update.message.reply_text(response)

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send plain text reminder"""
    job = context.job
    reminder = db.get_reminder(job.data['reminder_id'])
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Mark Done", callback_data=f"mark_{reminder['id']}")
        ]
    ]
    
    await context.bot.send_message(
        chat_id=reminder['group_id'],
        text=f"⏰ Reminder: {reminder['name']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mark done button"""
    query = update.callback_query
    await query.answer()
    
    reminder_id = int(query.data.split('_')[1])
    user = query.from_user
    
    # Log action
    db.log_pill(reminder_id, user.id, user.username)
    
    # Update message with history button
    keyboard = [[InlineKeyboardButton("📖 Show History", callback_data=f"history_{reminder_id}")]]
    await query.edit_message_text(
        text=f"✅ Marked as done by @{user.username}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show history with local time"""
    query = update.callback_query
    await query.answer()
    
    reminder_id = int(query.data.split('_')[1])
    history = db.get_history(reminder_id)
    
    if not history:
        await query.edit_message_text("📭 No history found")
        return

    text = f"📖 Last 20 entries:\n\n"
    for entry in history:
        text += f"⏰ {entry['timestamp']}\n👤 @{entry['username']}\n\n"
    
    await query.edit_message_text(text.strip())

async def show_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active reminders"""
    chat_id = update.effective_chat.id
    reminders = db.get_reminders(chat_id)
    
    if not reminders:
        await update.message.reply_text("🔔 No active reminders")
        return
    
    text = "📋 *Active Reminders:*\n\n"
    for idx, rem in enumerate(reminders, 1):
        text += (
            f"{idx}. {rem['name']}\n"
            f"   🕒 {', '.join(rem['times'])}\n"
            f"   🌍 {rem['timezone']}\n\n"
        )
    
    await update.message.reply_text(text, parse_mode='Markdown')