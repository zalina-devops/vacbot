# run.py
import threading
import os
import time
from app import create_app

app = create_app()


def run_bot():
    """Запуск Telegram-бота в отдельном потоке"""
    try:
        time.sleep(2)
        import asyncio
        from telegram_bot import main as bot_main
        print("🤖 Telegram-бот запускается...")
        asyncio.run(bot_main())
    except Exception as e:
        print(f"⚠️ Ошибка запуска бота: {e}")


if __name__ == "__main__":
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token and bot_token != "your_token_here":
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        print("🤖 Telegram-бот запущен в фоновом режиме")
    else:
        print("⚠️ TELEGRAM_BOT_TOKEN не задан. Бот не запущен.")

    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)