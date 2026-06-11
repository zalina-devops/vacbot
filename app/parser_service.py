# app/parser_service.py
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetcher import collect_all
from src.services.vacancy_storage import save_to_database
from src.services.parser_stats import get_parser_stats


def run_parser_and_save():
    print(f"\n{'=' * 60}")
    print(f"🚀 Запуск парсинга вакансий: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    all_vacancies = collect_all()

    print(f"\n📊 Найдено вакансий: {len(all_vacancies)}")

    if not all_vacancies:
        print("⚠️ Нет вакансий.")
        return 0, 0

    return save_to_database(all_vacancies)

