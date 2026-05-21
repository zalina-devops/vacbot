# start_bot.py
import asyncio
from telegram_bot import main

if __name__ == "__main__":
    print("🚀 Запуск Telegram-бота...")
    asyncio.run(main())