"""
migrate.py — одноразовый скрипт миграции данных из JSON-файлов в PostgreSQL.

Запускать ОДИН РАЗ после настройки БД:
    python migrate.py

Что делает:
  1. Читает vacancies.json  → заполняет таблицу vacancies
  2. Читает analysis.json   → обновляет поле direction у вакансий
  3. Читает board.json      → заполняет таблицу board_cards
  4. Выводит итоговую статистику
"""

import json
import os
import sys

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import Vacancy, BoardCard

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  ⚠️  Файл не найден: {path} — пропускаем")
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def migrate_vacancies(vacancies_data: dict) -> int:
    """Импортирует вакансии из vacancies.json."""
    vacancies = vacancies_data.get("vacancies", [])
    added = 0

    for v in vacancies:
        vid = v.get("id", "").strip()
        if not vid:
            continue  # пропускаем записи без id

        # Если уже есть — не дублируем (upsert-стиль)
        existing = db.session.get(Vacancy, vid)
        if existing:
            continue

        vacancy = Vacancy(
            id=vid,
            source=v.get("source", ""),
            title=v.get("title", ""),
            company=v.get("company", ""),
            salary=v.get("salary", "не указана"),
            city=v.get("city", ""),
            url=v.get("url", ""),
            published=v.get("published", ""),
            direction=v.get("direction", "Другое"),
            snippet_requirement=v.get("snippet_requirement", ""),
            snippet_responsibility=v.get("snippet_responsibility", ""),
        )
        db.session.add(vacancy)
        added += 1

    db.session.commit()
    return added


def migrate_directions(analysis_data: dict) -> int:
    """Обновляет direction у вакансий из analysis.json."""
    analyzed = {v["id"]: v.get("direction", "Другое")
                for v in analysis_data.get("vacancies", [])}
    updated = 0

    for vid, direction in analyzed.items():
        vacancy = db.session.get(Vacancy, vid)
        if vacancy and vacancy.direction != direction:
            vacancy.direction = direction
            updated += 1

    db.session.commit()
    return updated


def migrate_board(board_data: dict) -> int:
    """Импортирует состояние канбан-доски из board.json."""
    added = 0

    for vacancy_id, card_data in board_data.items():
        # Проверяем что вакансия существует в БД
        vacancy = db.session.get(Vacancy, vacancy_id)
        if not vacancy:
            print(f"  ⚠️  Вакансия {vacancy_id} из board.json не найдена в БД — пропускаем")
            continue

        # Если карточка уже есть — обновляем, иначе создаём
        card = vacancy.board_card
        if card is None:
            card = BoardCard(vacancy_id=vacancy_id)
            db.session.add(card)

        card.status  = card_data.get("status", "new")
        card.starred = card_data.get("starred", False)
        added += 1

    db.session.commit()
    return added


def main():
    print("=" * 50)
    print("  VacBot — миграция JSON → PostgreSQL")
    print("=" * 50)

    app = create_app()

    with app.app_context():
        # Создаём таблицы если ещё нет
        db.create_all()
        print("✅ Таблицы созданы (или уже существуют)\n")

        # Шаг 1: вакансии
        print("📥 Шаг 1: импорт vacancies.json...")
        vacancies_data = load_json("vacancies.json")
        n = migrate_vacancies(vacancies_data)
        print(f"   Добавлено вакансий: {n}\n")

        # Шаг 2: направления из analysis.json
        print("🔍 Шаг 2: обновление direction из analysis.json...")
        analysis_data = load_json("analysis.json")
        n = migrate_directions(analysis_data)
        print(f"   Обновлено направлений: {n}\n")

        # Шаг 3: состояние канбан-доски
        print("📋 Шаг 3: импорт board.json...")
        board_data = load_json("board.json")
        n = migrate_board(board_data)
        print(f"   Добавлено карточек: {n}\n")

        # Итог
        total_vacancies = Vacancy.query.count()
        total_cards     = BoardCard.query.count()
        print("=" * 50)
        print(f"✅ Миграция завершена!")
        print(f"   Вакансий в БД:  {total_vacancies}")
        print(f"   Карточек канбан: {total_cards}")
        print("=" * 50)


if __name__ == "__main__":
    main()
