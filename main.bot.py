#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = "8613273240:AAHJKsUpxNGXgEOu6hPYBOfzrJvpOo9Y4Dw"  # ← ВСТАВЬ СВОЙ ТОКЕН
DATA_FILE = "deleted_edited.json"
LOG_FILE = "bot_main.log"
# ===================================

# Настройка логирования для main системы
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Глобальные переменные
MONITORING = True
message_cache: Dict[int, Dict[int, Dict[str, Any]]] = {}

def load_data() -> Dict:
    """Загрузка данных из файла"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"deleted": [], "edited": []}
    return {"deleted": [], "edited": []}

def save_data(data: Dict) -> None:
    """Сохранение данных в файл"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== КОМАНДЫ БОТА ==========

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Бот запущен и работает в main системе\n\n"
        "Доступные команды:\n"
        "/monitor on - включить слежку\n"
        "/monitor off - выключить слежку\n"
        "/deleted_log - показать удаленные\n"
        "/edited_log - показать измененные\n"
        "/export - выгрузить логи\n"
        "/stats - статистика работы\n"
        "/clear_cache - очистить кэш"
    )
    logger.info(f"Start command from {update.effective_user.id}")

async def cmd_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение/выключение мониторинга"""
    global MONITORING
    if not context.args:
        status = "включен" if MONITORING else "выключен"
        await update.message.reply_text(f"Мониторинг {status}")
        return
    
    action = context.args[0].lower()
    if action == "on":
        MONITORING = True
        await update.message.reply_text("Мониторинг ВКЛЮЧЕН")
        logger.info("Monitoring enabled")
    elif action == "off":
        MONITORING = False
        await update.message.reply_text("Мониторинг ВЫКЛЮЧЕН")
        logger.info("Monitoring disabled")
    else:
        await update.message.reply_text("Используй: /monitor on  или  /monitor off")

async def cmd_deleted_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать удаленные сообщения"""
    data = load_data()
    if not data["deleted"]:
        await update.message.reply_text("Нет записей об удалениях")
        return
    
    msg = "Последние 10 удаленных сообщений:\n\n"
    for i, entry in enumerate(data["deleted"][:10], 1):
        msg += f"{i}. @{entry['user']}: {entry['text'][:80]}\n   Удалено: {entry['time']}\n\n"
    
    await update.message.reply_text(msg[:4000])

async def cmd_edited_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать измененные сообщения"""
    data = load_data()
    if not data["edited"]:
        await update.message.reply_text("Нет записей об изменениях")
        return
    
    msg = "Последние 10 измененных сообщений:\n\n"
    for i, entry in enumerate(data["edited"][:10], 1):
        msg += f"{i}. @{entry['user']}:\n   Было: {entry['old'][:60]}\n   Стало: {entry['new'][:60]}\n   Время: {entry['time']}\n\n"
    
    await update.message.reply_text(msg[:4000])

async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт логов в файл"""
    data = load_data()
    if not data["deleted"] and not data["edited"]:
        await update.message.reply_text("Нет данных для экспорта")
        return
    
    filename = f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("=" * 50 + "\n")
        f.write("УДАЛЕННЫЕ СООБЩЕНИЯ\n")
        f.write("=" * 50 + "\n")
        for d in data["deleted"]:
            f.write(f"Пользователь: @{d['user']}\n")
            f.write(f"Текст: {d['text']}\n")
            f.write(f"Время: {d['time']}\n")
            f.write("-" * 30 + "\n")
        
        f.write("\n" + "=" * 50 + "\n")
        f.write("ИЗМЕНЕННЫЕ СООБЩЕНИЯ\n")
        f.write("=" * 50 + "\n")
        for e in data["edited"]:
            f.write(f"Пользователь: @{e['user']}\n")
            f.write(f"Было: {e['old']}\n")
            f.write(f"Стало: {e['new']}\n")
            f.write(f"Время: {e['time']}\n")
            f.write("-" * 30 + "\n")
    
    await update.message.reply_document(document=open(filename, "rb"), filename="logs.txt")
    os.remove(filename)
    logger.info(f"Export by {update.effective_user.id}")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика работы бота"""
    data = load_data()
    cache_size = sum(len(msgs) for msgs in message_cache.values())
    
    stats = (
        f"Статистика бота:\n\n"
        f"Удаленных сообщений: {len(data['deleted'])}\n"
        f"Измененных сообщений: {len(data['edited'])}\n"
        f"Сообщений в кэше: {cache_size}\n"
        f"Мониторинг: {'вкл' if MONITORING else 'выкл'}\n"
        f"Активных чатов: {len(message_cache)}"
    )
    await update.message.reply_text(stats)

async def cmd_clear_cache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистка кэша"""
    global message_cache
    message_cache.clear()
    await update.message.reply_text("Кэш очищен")
    logger.info("Cache cleared")

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========

async def handle_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кэширование новых сообщений"""
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
    
    # Ограничение кэша на чат (максимум 1000 сообщений)
    if len(message_cache[chat_id]) > 1000:
        oldest_key = min(message_cache[chat_id].keys())
        del message_cache[chat_id][oldest_key]

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка измененных сообщений"""
    if not MONITORING:
        return
    
    edited = update.edited_message
    if not edited or not edited.text:
        return
    
    chat_id = edited.chat_id
    msg_id = edited.message_id
    old_data = message_cache.get(chat_id, {}).get(msg_id)
    
    if not old_data:
        return
    
    username = edited.from_user.username or edited.from_user.first_name
    
    log_entry = {
        "chat_id": chat_id,
        "user": username,
        "user_id": edited.from_user.id,
        "old": old_data["text"],
        "new": edited.text,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    data = load_data()
    data["edited"].insert(0, log_entry)
    if len(data["edited"]) > 500:
        data["edited"] = data["edited"][:500]
    save_data(data)
    
    # Обновляем кэш
    message_cache[chat_id][msg_id] = {
        "text": edited.text,
        "user": username,
        "user_id": edited.from_user.id,
        "date": edited.date.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    logger.info(f"Message edited by {username} in chat {chat_id}")
    
    # Оповещение в чат
    try:
        await edited.reply_text(
            f"[ИЗМЕНЕНО] @{username}\n"
            f"Было: {old_data['text'][:100]}\n"
            f"Стало: {edited.text[:100]}"
        )
    except:
        pass

# ========== ЗАПУСК ==========

async def main():
    """Главная функция запуска"""
    logger.info("Запуск бота в main системе...")
    
    # Создание приложения
    app = Application.builder().token(TOKEN).build()
    
    # Регистрация команд
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("monitor", cmd_monitor))
    app.add_handler(CommandHandler("deleted_log", cmd_deleted_log))
    app.add_handler(CommandHandler("edited_log", cmd_edited_log))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("clear_cache", cmd_clear_cache))
    
    # Регистрация обработчиков сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_message))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))
    
    # Запуск бота
    logger.info("Бот успешно запущен!")
    print("\n" + "="*50)
    print("БОТ РАБОТАЕТ В MAIN СИСТЕМЕ")
    print("="*50 + "\n")
    
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
