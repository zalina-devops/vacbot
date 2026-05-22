# run.py
import threading
import os
import time
import subprocess
import sys
from app import create_app

app = create_app()

# Путь к файлу бота
BOT_SCRIPT = os.path.join(os.path.dirname(__file__), "telegram_bot.py")


def run_bot_with_auto_restart():
    """Запуск бота с автоматическим перезапуском при падении"""
    while True:
        try:
            print("🤖 Запуск Telegram-бота...")
            # Запускаем бота в отдельном процессе
            process = subprocess.Popen([sys.executable, BOT_SCRIPT])
            process.wait()  # Ждём завершения процесса

            print("⚠️ Бот остановлен. Перезапуск через 10 секунд...")
            time.sleep(10)

        except Exception as e:
            print(f"❌ Ошибка при запуске бота: {e}")
            time.sleep(10)


if __name__ == "__main__":
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token and bot_token != "your_token_here":
        # Запускаем бота в отдельном потоке
        bot_thread = threading.Thread(target=run_bot_with_auto_restart, daemon=True)
        bot_thread.start()
        print("🤖 Telegram-бот запущен в фоновом режиме")
    else:
        print("⚠️ TELEGRAM_BOT_TOKEN не задан. Бот не запущен.")

    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)