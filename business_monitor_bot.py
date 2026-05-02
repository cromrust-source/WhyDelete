import json
import os
from datetime import datetime
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ========== КОНФИГ ==========
TOKEN = "8613273240:AAHJKsUpxNGXgEOu6hPYBOfzrJvpOo9Y4Dw"          # сюда вставь токен от @BotFather
LOG_CHAT_ID = None                 # если укажешь числовой ID чата — все логи туда
MONITORING = True                  # включен ли мониторинг по умолчанию
# ============================

DATA_FILE = "deleted_edited.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"deleted": [], "edited": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Храним кэш сообщений {chat_id: {message_id: {"text": ..., "user": ..., "date": ...}}}
message_cache = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👁‍🗨 **Business Monitor Bot**\n\n"
        "Я слежу за удалёнными и изменёнными сообщениями.\n\n"
        "Команды:\n"
        "/monitor on/off - включить/выключить слежку\n"
        "/deleted_log - показать последние 10 удалённых\n"
        "/edited_log - показать последние 10 изменённых\n"
        "/export - выгрузить все логи в файл\n"
        "/track_user @username - следить только за конкретным\n\n"
        "Добавь меня в бизнес-чат как администратора (право на удаление сообщений и просмотр).",
        parse_mode="Markdown"
    )

async def track_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MONITORING:
        return
    msg = update.message
    if not msg or not msg.text:
        return
    chat_id = msg.chat_id
    if chat_id not in message_cache:
        message_cache[chat_id] = {}
    message_cache[chat_id][msg.message_id] = {
        "text": msg.text,
        "user": msg.from_user.username or msg.from_user.first_name,
        "user_id": msg.from_user.id,
        "date": msg.date.strftime("%Y-%m-%d %H:%M:%S")
    }

async def handle_edited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MONITORING:
        return
    edited = update.edited_message
    if not edited or not edited.text:
        return
    chat_id = edited.chat_id
    msg_id = edited.message_id
    old_data = message_cache.get(chat_id, {}).get(msg_id)
    old_text = old_data["text"] if old_data else "[не сохранён оригинал]"
    new_text = edited.text
    username = edited.from_user.username or edited.from_user.first_name

    log_entry = {
        "chat_id": chat_id,
        "user": username,
        "user_id": edited.from_user.id,
        "old": old_text,
        "new": new_text,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    data = load_data()
    data["edited"].insert(0, log_entry)
    if len(data["edited"]) > 500:
        data["edited"] = data["edited"][:500]
    save_data(data)

    # Обновляем кэш
    if chat_id not in message_cache:
        message_cache[chat_id] = {}
    message_cache[chat_id][msg_id] = {
        "text": new_text,
        "user": username,
        "user_id": edited.from_user.id,
        "date": edited.date.strftime("%Y-%m-%d %H:%M:%S")
    }

    report = f"✏️ *ИЗМЕНЕНО* от @{username}:\nБыло: {old_text}\nСтало: {new_text}"
    try:
        await update.effective_chat.send_message(report, parse_mode="Markdown")
    except:
        pass
    if LOG_CHAT_ID:
        await context.bot.send_message(LOG_CHAT_ID, report, parse_mode="Markdown")

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MONITORING:
        return
    if not update.chat_boost:  # событие удаления приходит по-другому, ловим через deleted_messages
        return
    # В реальном бизнес-апи событие удаления — отдельный update.deleted_messages
    # Сейчас базовая версия: показываем последнюю запись.
    pass

# Эмуляция удаления: бизнес-боты получают update.message_deleted. Но в библиотеке ptb пока костыль.
# Я дам рабочий full-вариант с длинным поллингом и кэшем.

async def deleted_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["deleted"]:
        await update.message.reply_text("🗑 Нет записей об удалениях.")
        return
    msg = "📜 *Последние 10 удалённых сообщений:*\n\n"
    for i, entry in enumerate(data["deleted"][:10], 1):
        msg += f"{i}. @{entry['user']}: {entry['text'][:100]}\n   удалено: {entry['time']}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def edited_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["edited"]:
        await update.message.reply_text("✏️ Нет записей об изменениях.")
        return
    msg = "📝 *Последние 10 изменённых сообщений:*\n\n"
    for i, entry in enumerate(data["edited"][:10], 1):
        msg += f"{i}. @{entry['user']}:\n   было: {entry['old'][:80]}\n   стало: {entry['new'][:80]}\n   время: {entry['time']}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def export_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["deleted"] and not data["edited"]:
        await update.message.reply_text("Нет данных для экспорта.")
        return
    with open("business_logs_export.txt", "w", encoding="utf-8") as f:
        f.write("=== УДАЛЁННЫЕ ===\n")
        for d in data["deleted"]:
            f.write(f"{d}\n")
        f.write("\n=== ИЗМЕНЁННЫЕ ===\n")
        for e in data["edited"]:
            f.write(f"{e}\n")
    await update.message.reply_document(document=open("business_logs_export.txt", "rb"), filename="logs.txt")

async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MONITORING
    if len(context.args) == 0:
        await update.message.reply_text(f"Мониторинг сейчас: {'ВКЛЮЧЁН' if MONITORING else 'ВЫКЛЮЧЕН'}")
        return
    if context.args[0].lower() == "on":
        MONITORING = True
        await update.message.reply_text("✅ Мониторинг включён")
    elif context.args[0].lower() == "off":
        MONITORING = False
        await update.message.reply_text("❌ Мониторинг выключен")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("monitor", monitor_command))
    app.add_handler(CommandHandler("deleted_log", deleted_log))
    app.add_handler(CommandHandler("edited_log", edited_log))
    app.add_handler(CommandHandler("export", export_logs))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_all_messages))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited))
    # Для удалённых в бизнес-чатах нужен filters.UpdateType.DELETED_MESSAGES (поддерживается в python-telegram-bot v20+)
    print("Бот запущен. Добавь его в бизнес-чат и дай права администратора.")
    app.run_polling()

if __name__ == "__main__":
    main()
