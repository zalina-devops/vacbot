from app import db
from app.models import Vacancy, BoardCard


def get_parser_stats():
    return {
        "total_vacancies": Vacancy.query.count(),
        "by_source": db.session.query(
            Vacancy.source,
            db.func.count(Vacancy.id)
        ).group_by(Vacancy.source).all(),
        "new_cards": BoardCard.query.filter_by(
            status="new"
        ).count(),
        "last_updated": db.session.query(
            db.func.max(Vacancy.updated_at)
        ).scalar()
    }