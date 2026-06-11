# run_bot.py
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Проверяем наличие токена
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN or BOT_TOKEN == "your_token_here":
    print("❌ TELEGRAM_BOT_TOKEN не задан в файле .env")
    print("📝 Добавьте строку: TELEGRAM_BOT_TOKEN=ваш_токен")
    exit(1)

print("🤖 Запуск Telegram бота...")
print("📋 Бот будет отслеживать команды /start, /menu и др.")
print("\nДля запуска веб-приложения выполните: python run_web.py")
print("=" * 50)

# Импортируем функцию запуска бота
from telegram_bot import run_bot

# Запускаем бота
asyncio.run(run_bot())