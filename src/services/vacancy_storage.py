from typing import List, Dict, Optional, Tuple
import logging
from src.services.direction_detector import detect_direction

logger = logging.getLogger(__name__)

def save_to_database(vacancies: List[dict]) -> Tuple[int, int]:
    """Сохраняет вакансии в базу данных"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app import create_app, db
    from app.models import Vacancy, BoardCard

    app = create_app()
    added = updated = errors = 0

    with app.app_context():
        for vacancy in vacancies:
            try:
                if not vacancy.get('id'):
                    errors += 1
                    continue

                existing = Vacancy.query.filter_by(id=vacancy['id']).first()

                if existing:
                    existing.title = vacancy.get('title', existing.title)
                    existing.company = vacancy.get('company', existing.company)
                    existing.salary = vacancy.get('salary', existing.salary)
                    existing.city = vacancy.get('city', existing.city)
                    existing.url = vacancy.get('url', existing.url)
                    existing.published = vacancy.get('published', existing.published)
                    existing.snippet_requirement = vacancy.get('requirement', '')
                    existing.snippet_responsibility = vacancy.get('responsibility', '')
                    updated += 1
                else:
                    new_vacancy = Vacancy(
                        id=vacancy['id'],
                        source=vacancy.get('source', ''),
                        title=vacancy.get('title', ''),
                        company=vacancy.get('company', ''),
                        salary=vacancy.get('salary', 'не указана'),
                        city=vacancy.get('city', ''),
                        url=vacancy.get('url', ''),
                        published=vacancy.get('published', ''),
                        snippet_requirement=vacancy.get('requirement', ''),
                        snippet_responsibility=vacancy.get('responsibility', ''),
                        direction=detect_direction(vacancy.get('title', '') + ' ' + vacancy.get('requirement', ''))
                    )
                    db.session.add(new_vacancy)
                    db.session.add(BoardCard(vacancy_id=vacancy['id'], status='new', is_postponed=False))
                    added += 1

            except Exception as e:
                errors += 1
                logger.error(f"Ошибка сохранения {vacancy.get('id', 'unknown')}: {e}")

        db.session.commit()
        logger.info(f"💾 БД: +{added} ✨, ~{updated} 🔄, ошибок: {errors}")
        return added, updated