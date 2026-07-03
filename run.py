# run.py
import sys
import os
import argparse


def main():
    parser = argparse.ArgumentParser(description='VacBot - система поиска вакансий')
    parser.add_argument('--mode', choices=['web', 'bot', 'both'], default='both',
                        help='Режим запуска: web (только сайт), bot (только телеграм), both (оба)')
    parser.add_argument('--port', type=int, default=None,
                        help='Порт для веб-приложения (по умолчанию из переменной PORT или 5000)')

    args = parser.parse_args()
    
    port = int(os.environ.get("PORT", args.port or 5000))

    if args.mode == 'bot':
        # Запуск только бота
        print("🤖 Запуск только Telegram бота")
        from telegram_bot import run_bot
        import asyncio
        asyncio.run(run_bot())

    elif args.mode == 'web':
        # Запуск только веб-приложения
        print("🌐 Запуск только веб-приложения")
        from app import create_app
        app = create_app()
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    else: 
        print("🚀 Запуск VacBot в полном режиме...")

        from app import create_app
        import threading
        import asyncio
        from telegram_bot import run_bot

        # Запускаем бота в отдельном потоке
        def run_bot_thread():
            asyncio.run(run_bot())

        bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
        bot_thread.start()
        print("✅ Telegram бот запущен в фоновом режиме")

        # Запускаем Flask
        app = create_app()
        print(f"🌐 Веб-приложение запущено на порту {port}")
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()