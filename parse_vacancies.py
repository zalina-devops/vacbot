# parse_vacancies.py (в корне проекта)
"""Скрипт для управления парсингом вакансий."""

import sys
import argparse
from app import create_app
from app.parser_service import run_parser_and_save, get_parser_stats
from app.scheduler import start_scheduler, stop_scheduler, is_scheduler_running


def main():
    parser = argparse.ArgumentParser(description='Управление парсингом вакансий')
    parser.add_argument('command',
                        choices=['run', 'scheduler-start', 'scheduler-stop', 'stats'],
                        help='Команда для выполнения')
    parser.add_argument('--interval', type=int, default=24,
                        help='Интервал парсинга в часах (для scheduler-start)')

    args = parser.parse_args()

    app = create_app()

    if args.command == 'run':
        # Разовый запуск
        with app.app_context():
            print("🚀 Разовый запуск парсинга...")
            run_parser_and_save()

    elif args.command == 'scheduler-start':
        # Запуск планировщика
        with app.app_context():
            print(f"🕐 Запуск планировщика с интервалом {args.interval} часов...")
            start_scheduler(interval_hours=args.interval, run_immediately=True)
            print("✅ Планировщик запущен в фоновом режиме")
            print("   Нажмите Ctrl+C для остановки")
            try:
                # Держим скрипт запущенным
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n⏹️ Остановка планировщика...")
                stop_scheduler()

    elif args.command == 'scheduler-stop':
        # Остановка планировщика
        if is_scheduler_running():
            stop_scheduler()
            print("✅ Планировщик остановлен")
        else:
            print("⚠️ Планировщик не запущен")

    elif args.command == 'stats':
        # Показать статистику
        with app.app_context():
            stats = get_parser_stats()
            print("\n📊 Статистика базы данных:")
            print(f"   Всего вакансий: {stats['total_vacancies']}")
            print("   По источникам:")
            for source, count in stats['by_source']:
                print(f"      - {source}: {count}")
            print(f"   Новых карточек: {stats['new_cards']}")
            print(f"   Последнее обновление: {stats['last_updated']}")


if __name__ == "__main__":
    main()