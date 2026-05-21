import sys
from pathlib import Path
from datetime import datetime


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetcher import collect_all
from app import db
from app.models import Vacancy, BoardCard


def run_parser_and_save():

    print(f"\n{'=' * 60}")
    print(f"🚀 Запуск парсинга вакансий: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    vacancies = collect_all()
    print(f"\n📊 Найдено вакансий: {len(vacancies)}")

    if not vacancies:
        print("⚠️ Вакансии не найдены. Проверьте подключение к источникам.")
        return 0, 0
    # добавление в бд
    added_count = 0
    updated_count = 0

    for v in vacancies:
        existing = Vacancy.query.filter_by(id=v['id']).first()

        if existing:
            existing.source = v['source']
            existing.title = v['title']
            existing.company = v['company']
            existing.salary = v['salary']
            existing.city = v['city']
            existing.url = v['url']
            existing.published = v['published']
            existing.snippet_requirement = v['snippet_requirement']
            existing.snippet_responsibility = v['snippet_responsibility']
            existing.updated_at = datetime.utcnow()
            updated_count += 1
        else:
            new_vacancy = Vacancy(
                id=v['id'],
                source=v['source'],
                title=v['title'],
                company=v['company'],
                salary=v['salary'],
                city=v['city'],
                url=v['url'],
                published=v['published'],
                snippet_requirement=v['snippet_requirement'],
                snippet_responsibility=v['snippet_responsibility']
            )
            db.session.add(new_vacancy)

            # Автоматическое создание карточки для доски
            board_card = BoardCard(
                vacancy_id=v['id'],
                status='new'
            )
            db.session.add(board_card)
            added_count += 1

    db.session.commit()

    print(f"\n💾 Результат сохранения в БД:")
    print(f"   ✨ Новых вакансий: {added_count}")
    print(f"   🔄 Обновлено: {updated_count}")
    print(f"   📊 Всего в БД: {Vacancy.query.count()}")

    return added_count, updated_count


def get_parser_stats():

    return {
        'total_vacancies': Vacancy.query.count(),
        'by_source': db.session.query(
            Vacancy.source,
            db.func.count(Vacancy.id)
        ).group_by(Vacancy.source).all(),
        'new_cards': BoardCard.query.filter_by(status='new').count(),
        'last_updated': db.session.query(db.func.max(Vacancy.updated_at)).scalar()
    }