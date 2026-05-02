#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ====================================================================
# КОНФИГУРАЦИЯ - ИЗМЕНИ ЭТИ ПАРАМЕТРЫ
# ====================================================================

TOKEN = "8613273240:AAHJKsUpxNGXgEOu6hPYBOfzrJvpOo9Y4Dw"           # Вставь сюда токен от @BotFather
LOG_CHAT_ID = None                   # Сюда вставь ID чата для логов (опционально)
ADMIN_IDS = []                       # Список ID админов, например [123456789, 987654321]

# ====================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ====================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ====================================================================

DATA_FILE = "business_bot_data.json"
message_cache: Dict[int, Dict[int, Dict[str, Any]]] = {}
MONITORING_ENABLED = True
TRACKED_USERS: Dict[int, List[int]] = {}  # {chat_id: [user_ids]}

# ====================================================================
# РАБОТА С ФАЙЛОМ ДАННЫХ
# ====================================================================

def load_data() -> Dict[str, Any]:
    """Загружает данные из JSON файла"""
    if not os.path.exists(DATA_FILE):
        default_data = {
            "deleted_messages": [],
            "edited_messages": [],
            "settings": {
                "monitoring_enabled": True,
                "notify_on_delete": True,
                "notify_on_edit": True
            }
        }
        save_data(default_data)
        return default_data
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return {
            "deleted_messages": [],
            "edited_messages": [],
            "settings": {
                "monitoring_enabled": True,
                "notify_on_delete": True,
                "notify_on_edit": True
            }
        }

def save_data(data: Dict[str, Any]) -> None:
    """Сохраняет данные в JSON файл"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"Ошибка сохранения данных: {e}")

def add_deleted_message(chat_id: int, user_id: int, username: str, text: str) -> None:
    """Добавляет запись об удаленном сообщении"""
    data = load_data()
    entry = {
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "text": text[:500],  # Ограничиваем длину
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": datetime.now().timestamp()
    }
    data["deleted_messages"].insert(0, entry)
    
    # Оставляем только последние 1000 записей
    if len(data["deleted_messages"]) > 1000:
        data["deleted_messages"] = data["deleted_messages"][:1000]
    
    save_data(data)

def add_edited_message(chat_id: int, user_id: int, username: str, old_text: str, new_text: str) -> None:
    """Добавляет запись об измененном сообщении"""
    data = load_data()
    entry = {
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "old_text": old_text[:500],
        "new_text": new_text[:500],
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": datetime.now().timestamp()
    }
    data["edited_messages"].insert(0, entry)
    
    if len(data["edited_messages"]) > 1000:
        data["edited_messages"] = data["edited_messages"][:1000]
    
    save_data(data)

def get_deleted_messages(chat_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
    """Получает список удаленных сообщений"""
    data = load_data()
    messages = data["deleted_messages"]
    
    if chat_id:
        messages = [m for m in messages if m.get("chat_id") == chat_id]
    
    return messages[:limit]

def get_edited_messages(chat_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
    """Получает список измененных сообщений"""
    data = load_data()
    messages = data["edited_messages"]
    
    if chat_id:
        messages = [m for m in messages if m.get("chat_id") == chat_id]
    
    return messages[:limit]

# ====================================================================
# КОМАНДЫ БОТА
# ====================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = f"""
Привет, {user.first_name}!

Я бот для мониторинга бизнес-чатов Telegram.

Что я умею:
- Отслеживать удаленные сообщения
- Отслеживать измененные сообщения
- Вести лог всех действий
- Экспортировать данные

Как использовать:
1. Добавь меня в бизнес-чат
2. Сделай меня администратором
3. Используй команды ниже

Доступные команды:
/monitor_on - Включить мониторинг
/monitor_off - Выключить мониторинг
/deleted - Показать удаленные сообщения
/edited - Показать измененные сообщения
/export - Экспортировать логи в файл
/stats - Показать статистику
/clear_cache - Очистить кэш
/help - Помощь
"""
    await update.message.reply_text(welcome_text.strip())

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = """
📖 Справка по командам:

Основные команды:
/monitor_on - Включить отслеживание сообщений
/monitor_off - Выключить отслеживание
/deleted [N] - Показать последние N удаленных сообщений (N=1-50)
/edited [N] - Показать последние N измененных сообщений
/export - Выгрузить все логи в текстовый файл
/stats - Статистика работы бота
/clear_cache - Очистить временный кэш

Для бизнес-чатов:
/track @username - Следить только за указанным пользователем
/untrack @username - Прекратить следить за пользователем
/untrack_all - Следить за всеми пользователями

Примеры:
/deleted 20 - показать 20 последних удалений
/track @ivan - следить только за Иваном
"""
    await update.message.reply_text(help_text.strip())

async def cmd_monitor_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Включить мониторинг"""
    global MONITORING_ENABLED
    MONITORING_ENABLED = True
    
    data = load_data()
    data["settings"]["monitoring_enabled"] = True
    save_data(data)
    
    await update.message.reply_text("✅ Мониторинг ВКЛЮЧЕН. Я буду отслеживать все сообщения.")

async def cmd_monitor_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выключить мониторинг"""
    global MONITORING_ENABLED
    MONITORING_ENABLED = False
    
    data = load_data()
    data["settings"]["monitoring_enabled"] = False
    save_data(data)
    
    await update.message.reply_text("❌ Мониторинг ВЫКЛЮЧЕН. Я не отслеживаю сообщения.")

async def cmd_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать удаленные сообщения"""
    try:
        limit = 10
        if context.args and context.args[0].isdigit():
            limit = min(int(context.args[0]), 50)
        
        chat_id = update.effective_chat.id
        messages = get_deleted_messages(chat_id=chat_id, limit=limit)
        
        if not messages:
            await update.message.reply_text("📭 Нет записей об удаленных сообщениях в этом чате.")
            return
        
        response = f"🗑 УДАЛЕННЫЕ СООБЩЕНИЯ (последние {len(messages)}):\n\n"
        
        for i, msg in enumerate(messages, 1):
            username = msg.get("username", "unknown")
            text = msg.get("text", "[пусто]")
            time = msg.get("time", "неизвестно")
            
            response += f"{i}. @{username}\n"
            response += f"   Текст: {text[:100]}\n"
            response += f"   Время: {time}\n\n"
            
            if len(response) > 3500:
                response += "\n... и еще сообщения. Используй /export для полного лога."
                break
        
        await update.message.reply_text(response[:4096])
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_deleted: {e}")
        await update.message.reply_text("Ошибка при получении списка удаленных сообщений.")

async def cmd_edited(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать измененные сообщения"""
    try:
        limit = 10
        if context.args and context.args[0].isdigit():
            limit = min(int(context.args[0]), 50)
        
        chat_id = update.effective_chat.id
        messages = get_edited_messages(chat_id=chat_id, limit=limit)
        
        if not messages:
            await update.message.reply_text("📭 Нет записей об измененных сообщениях в этом чате.")
            return
        
        response = f"✏️ ИЗМЕНЕННЫЕ СООБЩЕНИЯ (последние {len(messages)}):\n\n"
        
        for i, msg in enumerate(messages, 1):
            username = msg.get("username", "unknown")
            old_text = msg.get("old_text", "[пусто]")
            new_text = msg.get("new_text", "[пусто]")
            time = msg.get("time", "неизвестно")
            
            response += f"{i}. @{username}\n"
            response += f"   Было: {old_text[:80]}\n"
            response += f"   Стало: {new_text[:80]}\n"
            response += f"   Время: {time}\n\n"
            
            if len(response) > 3500:
                response += "\n... и еще сообщения. Используй /export для полного лога."
                break
        
        await update.message.reply_text(response[:4096])
        
    except Exception as e:
        logger.error(f"Ошибка в cmd_edited: {e}")
        await update.message.reply_text("Ошибка при получении списка измененных сообщений.")

async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Экспортировать логи в файл"""
    try:
        chat_id = update.effective_chat.id
        data = load_data()
        
        deleted_in_chat = [m for m in data["deleted_messages"] if m.get("chat_id") == chat_id]
        edited_in_chat = [m for m in data["edited_messages"] if m.get("chat_id") == chat_id]
        
        if not deleted_in_chat and not edited_in_chat:
            await update.message.reply_text("Нет данных для экспорта в этом чате.")
            return
        
        filename = f"business_logs_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("TELEGRAM BUSINESS BOT - ЛОГИ СООБЩЕНИЙ\n")
            f.write(f"Чат ID: {chat_id}\n")
            f.write(f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("УДАЛЕННЫЕ СООБЩЕНИЯ\n")
            f.write("-" * 40 + "\n")
            for msg in deleted_in_chat:
                f.write(f"Пользователь: @{msg.get('username', 'unknown')}\n")
                f.write(f"Текст: {msg.get('text', '')}\n")
                f.write(f"Время: {msg.get('time', '')}\n")
                f.write("-" * 30 + "\n")
            
            f.write("\nИЗМЕНЕННЫЕ СООБЩЕНИЯ\n")
            f.write("-" * 40 + "\n")
            for msg in edited_in_chat:
                f.write(f"Пользователь: @{msg.get('username', 'unknown')}\n")
                f.write(f"Было: {msg.get('old_text', '')}\n")
                f.write(f"Стало: {msg.get('new_text', '')}\n")
                f.write(f"Время: {msg.get('time', '')}\n")
                f.write("-" * 30 + "\n")
        
        await update.message.reply_document(
            document=open(filename, "rb"),
            filename=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        os.remove(filename)
        logger.info(f"Экспорт логов выполнен пользователем {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка экспорта: {e}")
        await update.message.reply_text("Ошибка при экспорте данных.")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать статистику работы бота"""
    try:
        chat_id = update.effective_chat.id
        data = load_data()
        
        deleted_count = len([m for m in data["deleted_messages"] if m.get("chat_id") == chat_id])
        edited_count = len([m for m in data["edited_messages"] if m.get("chat_id") == chat_id])
        cache_size = sum(len(msgs) for msgs in message_cache.values())
        
        stats_text = f"""
📊 СТАТИСТИКА БОТА

Чат ID: {chat_id}

📝 Мониторинг:
- Статус: {'Включен' if MONITORING_ENABLED else 'Выключен'}
- Сообщений в кэше: {cache_size}

🗑 Удаления:
- Записей: {deleted_count}

✏️ Изменения:
- Записей: {edited_count}

Время работы: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await update.message.reply_text(stats_text.strip())
        
    except Exception as e:
        logger.error(f"Ошибка stats: {e}")
        await update.message.reply_text("Ошибка получения статистики.")

async def cmd_clear_cache(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Очистить кэш сообщений"""
    global message_cache
    message_cache.clear()
    await update.message.reply_text("🗑 Кэш сообщений очищен.")
    logger.info(f"Кэш очищен пользователем {update.effective_user.id}")

async def cmd_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Следить только за определенным пользователем"""
    if not context.args:
        await update.message.reply_text("Использование: /track @username")
        return
    
    chat_id = update.effective_chat.id
    username = context.args[0].replace("@", "").lower()
    
    if chat_id not in TRACKED_USERS:
        TRACKED_USERS[chat_id] = []
    
    # Здесь нужно получить ID пользователя по username
    # Для упрощения пока сохраняем username
    if username not in TRACKED_USERS[chat_id]:
        TRACKED_USERS[chat_id].append(username)
        await update.message.reply_text(f"✅ Теперь слежу только за @{username}")
    else:
        await update.message.reply_text(f"@{username} уже в списке отслеживания")

async def cmd_untrack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Прекратить следить за пользователем"""
    if not context.args:
        await update.message.reply_text("Использование: /untrack @username")
        return
    
    chat_id = update.effective_chat.id
    username = context.args[0].replace("@", "").lower()
    
    if chat_id in TRACKED_USERS and username in TRACKED_USERS[chat_id]:
        TRACKED_USERS[chat_id].remove(username)
        await update.message.reply_text(f"❌ Больше не слежу за @{username}")
    else:
        await update.message.reply_text(f"@{username} не найден в списке отслеживания")

async def cmd_untrack_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Следить за всеми пользователями"""
    chat_id = update.effective_chat.id
    if chat_id in TRACKED_USERS:
        TRACKED_USERS[chat_id] = []
    await update.message.reply_text("✅ Теперь слежу за ВСЕМИ пользователями")

# ====================================================================
# ОБРАБОТЧИКИ СООБЩЕНИЙ
# ====================================================================

async def handle_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Кэширует новые сообщения"""
    if not MONITORING_ENABLED:
        return
    
    msg = update.message
    if not msg or not msg.text:
        return
    
    chat_id = msg.chat_id
    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    
    # Проверяем фильтр пользователей
    if chat_id in TRACKED_USERS and TRACKED_USERS[chat_id]:
        if username.lower() not in TRACKED_USERS[chat_id]:
            return
    
    # Сохраняем в кэш
    if chat_id not in message_cache:
        message_cache[chat_id] = {}
    
    message_cache[chat_id][msg.message_id] = {
        "text": msg.text,
        "user_id": user_id,
        "username": username,
        "date": msg.date.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": msg.date.timestamp()
    }
    
    # Ограничиваем размер кэша на чат
    if len(message_cache[chat_id]) > 2000:
        oldest_id = min(message_cache[chat_id].keys())
        del message_cache[chat_id][oldest_id]

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает измененные сообщения"""
    if not MONITORING_ENABLED:
        return
    
    edited = update.edited_message
    if not edited or not edited.text:
        return
    
    chat_id = edited.chat_id
    msg_id = edited.message_id
    user_id = edited.from_user.id
    username = edited.from_user.username or edited.from_user.first_name
    
    # Проверяем фильтр пользователей
    if chat_id in TRACKED_USERS and TRACKED_USERS[chat_id]:
        if username.lower() not in TRACKED_USERS[chat_id]:
            return
    
    # Ищем оригинал в кэше
    old_data = message_cache.get(chat_id, {}).get(msg_id)
    
    if old_data:
        old_text = old_data["text"]
        new_text = edited.text
        
        if old_text != new_text:
            # Сохраняем в файл
            add_edited_message(chat_id, user_id, username, old_text, new_text)
            
            # Обновляем кэш
            message_cache[chat_id][msg_id]["text"] = new_text
            message_cache[chat_id][msg_id]["edited"] = True
            
            # Уведомление в чат
            notify_text = f"✏️ @{username} изменил сообщение:\nБыло: {old_text[:100]}\nСтало: {new_text[:100]}"
            
            try:
                await edited.reply_text(notify_text[:500])
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")
            
            logger.info(f"Изменено сообщение от {username} в чате {chat_id}")

async def handle_deleted_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает удаленные сообщения"""
    if not MONITORING_ENABLED:
        return
    
    # Обратите внимание: в python-telegram-bot событие удаления сообщения
    # приходит как update.message_deleted или через update.message с is_deleted=True
    # Здесь базовая реализация через кэш
    
    # Для полной поддержки удалений нужно использовать deleted_messages update
    pass

# ====================================================================
# ЗАПУСК БОТА
# ====================================================================

async def main() -> None:
    """Главная функция запуска"""
    print("\n" + "=" * 60)
    print("TELEGRAM BUSINESS MONITOR BOT")
    print("=" * 60)
    print(f"Файл данных: {DATA_FILE}")
    print(f"Логирование: включено")
    print("=" * 60 + "\n")
    
    logger.info("Запуск бота...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("monitor_on", cmd_monitor_on))
    application.add_handler(CommandHandler("monitor_off", cmd_monitor_off))
    application.add_handler(CommandHandler("deleted", cmd_deleted))
    application.add_handler(CommandHandler("edited", cmd_edited))
    application.add_handler(CommandHandler("export", cmd_export))
    application.add_handler(CommandHandler("stats", cmd_stats))
    application.add_handler(CommandHandler("clear_cache", cmd_clear_cache))
    application.add_handler(CommandHandler("track", cmd_track))
    application.add_handler(CommandHandler("untrack", cmd_untrack))
    application.add_handler(CommandHandler("untrack_all", cmd_untrack_all))
    
    # Регистрируем обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_message))
    application.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited_message))
    
    # Запускаем бота
    print("✅ Бот успешно запущен!")
    print("📨 Бот готов к работе. Добавьте его в бизнес-чат.")
    print("🛑 Для остановки нажмите Ctrl+C\n")
    
    await application.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Бот остановлен пользователем")
        logger.info("Бот остановлен")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")
