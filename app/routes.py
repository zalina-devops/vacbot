import os
import json
import subprocess
import sys
from datetime import datetime

from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from . import db
from .models import Vacancy, BoardCard, UserProfile, CoverLetterTemplate, SearchQuery, StopWord
from .config import Config
from .ai_agent import calculate_match_percentage

main = Blueprint("main", __name__)


# ─── Вспомогательные функции ──────────────────────────────────────────────────

def get_or_create_card(vacancy_id: str) -> BoardCard:
    """Возвращает карточку канбан, создаёт если нет."""
    card = BoardCard.query.filter_by(vacancy_id=vacancy_id).first()
    if card is None:
        card = BoardCard(vacancy_id=vacancy_id, status="new", starred=False)
        db.session.add(card)
        db.session.flush()
    return card


# ─── Страницы ─────────────────────────────────────────────────────────────────

@main.route("/")
def index():
    """Главная — канбан-доска с процентами совпадения."""
    vacancies = []
    for v in Vacancy.query.all():
        v_dict = v.to_dict()
        v_dict['match_percent'] = calculate_match_percentage(v)
        vacancies.append(v_dict)

    total = len(vacancies)
    funnel = {
        "total": total,
        "new": sum(1 for v in vacancies if v["board_status"] == "new"),
        "starred": sum(1 for v in vacancies if v["starred"]),
        "applied": sum(1 for v in vacancies if v["board_status"] == "applied"),
        "interview": sum(1 for v in vacancies if v["board_status"] == "interview"),
        "rejected": sum(1 for v in vacancies if v["board_status"] == "rejected"),
        "offer": sum(1 for v in vacancies if v["board_status"] == "offer"),
        "postponed": sum(1 for v in vacancies if v["postponed"]),
    }

    return render_template("index.html", vacancies=vacancies, funnel=funnel)


@main.route("/vacancies")
def vacancies_page():
    """Страница со списком вакансий и фильтрами."""
    direction = request.args.get("direction", "")
    source = request.args.get("source", "")
    search = request.args.get("search", "").lower()
    show_postponed = request.args.get("show_postponed", "0") == "1"

    query = Vacancy.query
    if direction:
        query = query.filter(Vacancy.direction == direction)
    if source:
        query = query.filter(Vacancy.source == source)
    if search:
        query = query.filter(
            db.or_(
                Vacancy.title.ilike(f"%{search}%"),
                Vacancy.company.ilike(f"%{search}%"),
            )
        )
    if not show_postponed:
        query = query.outerjoin(BoardCard).filter(
            db.or_(BoardCard.is_postponed == False, BoardCard.id == None)
        )

    vacancies = [v.to_dict() for v in query.all()]
    directions = sorted(set(r[0] for r in db.session.query(Vacancy.direction).distinct() if r[0]))
    sources = sorted(set(r[0] for r in db.session.query(Vacancy.source).distinct() if r[0]))

    return render_template(
        "vacancies.html",
        vacancies=vacancies,
        directions=directions,
        sources=sources,
        current_direction=direction,
        current_source=source,
        search=search,
        show_postponed=show_postponed,
    )


# ─── API эндпоинты (JSON) ─────────────────────────────────────────────────────

@main.route("/api/card/<vacancy_id>/status", methods=["POST"])
def update_status(vacancy_id: str):
    """Поменять статус карточки на канбан-доске."""
    data = request.get_json()
    new_status = data.get("status")
    valid_statuses = ["new", "starred", "applied", "interview", "rejected", "offer"]
    if new_status not in valid_statuses:
        return jsonify({"error": "invalid status"}), 400
    if not db.session.get(Vacancy, vacancy_id):
        return jsonify({"error": "vacancy not found"}), 404
    card = get_or_create_card(vacancy_id)
    if new_status == "starred":
        card.starred = True
    else:
        if card.starred:
            card.starred = False
        card.status = new_status
    db.session.commit()
    return jsonify({
        "ok": True,
        "id": vacancy_id,
        "status": new_status,
        "starred": card.starred
    })

@main.route("/api/card/<vacancy_id>/star", methods=["POST"])
def toggle_star(vacancy_id: str):
    if not db.session.get(Vacancy, vacancy_id):
        return jsonify({"error": "vacancy not found"}), 404
    card = get_or_create_card(vacancy_id)
    card.starred = not card.starred
    db.session.commit()
    return jsonify({"ok": True, "starred": card.starred})

@main.route("/api/card/<vacancy_id>/postpone", methods=["POST"])
def postpone_card(vacancy_id: str):
    if not db.session.get(Vacancy, vacancy_id):
        return jsonify({"error": "vacancy not found"}), 404
    data = request.get_json() or {}
    notes = data.get("notes", "")
    until = data.get("postpone_until")
    postponed_until = None
    if until:
        try:
            postponed_until = datetime.strptime(until, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "invalid date format, use YYYY-MM-DD"}), 400
    card = get_or_create_card(vacancy_id)
    card.is_postponed = True
    card.postponed_until = postponed_until
    card.notes = notes
    db.session.commit()
    return jsonify({
        "ok": True,
        "id": vacancy_id,
        "is_postponed": True,
        "postponed_until": until,
        "notes": notes,
    })

@main.route("/api/card/<vacancy_id>/restore", methods=["POST"])
def restore_card(vacancy_id: str):
    if not db.session.get(Vacancy, vacancy_id):
        return jsonify({"error": "vacancy not found"}), 404
    card = get_or_create_card(vacancy_id)
    card.is_postponed = False
    card.postponed_until = None
    db.session.commit()
    return jsonify({"ok": True, "id": vacancy_id, "is_postponed": False})

@main.route("/api/card/<vacancy_id>/delete", methods=["DELETE"])
def delete_card(vacancy_id: str):
    vacancy = db.session.get(Vacancy, vacancy_id)
    if not vacancy:
        return jsonify({"error": "vacancy not found"}), 404

    BoardCard.query.filter_by(vacancy_id=vacancy_id).delete()
    db.session.delete(vacancy)
    db.session.commit()

    return jsonify({"ok": True, "id": vacancy_id, "deleted": True})

@main.route("/api/run-parser", methods=["POST"])
def run_parser():
    try:
        import sys
        from pathlib import Path
        src_path = Path(__file__).parent.parent / 'src'
        sys.path.insert(0, str(src_path))
        from fetcher import collect_all, save_to_database
        vacancies = collect_all()
        if vacancies:
            save_to_database(vacancies)
            with open('data/vacancies.json', 'w', encoding='utf-8') as f:
                json.dump(vacancies, f, ensure_ascii=False, indent=2)
        return jsonify({
            "ok": True,
            "message": f"Парсер завершен. Найдено {len(vacancies)} вакансий",
            "total": len(vacancies)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

@main.route("/api/stats")
def stats():
    total = Vacancy.query.count()
    by_direction_list = db.session.query(
        Vacancy.direction,
        db.func.count(Vacancy.id)
    ).group_by(Vacancy.direction).all()
    by_direction = {d or 'Другое': c for d, c in by_direction_list}
    by_source_list = db.session.query(
        Vacancy.source,
        db.func.count(Vacancy.id)
    ).group_by(Vacancy.source).all()
    by_source = {s: c for s, c in by_source_list}
    board_stats = {
        'new': BoardCard.query.filter_by(status='new').count(),
        'applied': BoardCard.query.filter_by(status='applied').count(),
        'interview': BoardCard.query.filter_by(status='interview').count(),
        'rejected': BoardCard.query.filter_by(status='rejected').count(),
        'offer': BoardCard.query.filter_by(status='offer').count(),
        'postponed': BoardCard.query.filter_by(is_postponed=True).count(),
        'starred': BoardCard.query.filter_by(starred=True).count() if hasattr(BoardCard, 'starred') else 0
    }
    return jsonify({
        "total": total,
        "by_direction": by_direction,
        "by_source": by_source,
        "board_stats": board_stats
    })

# ---------- AI-агент (адаптация резюме и письма) ----------
@main.route("/api/adapt-resume/<vacancy_id>", methods=["POST"])
def api_adapt_resume(vacancy_id):
    try:
        from app.ai_agent import adapt_resume
        result = adapt_resume(vacancy_id)
        return jsonify({"success": True, "text": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@main.route("/api/generate-cover-letter/<vacancy_id>", methods=["POST"])
def api_generate_cover_letter(vacancy_id):
    try:
        from app.ai_agent import generate_cover_letter
        result = generate_cover_letter(vacancy_id)
        return jsonify({"success": True, "text": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ---------- Профиль (расширенный) ----------
@main.route("/profile")
def profile_page():
    return render_template("profile.html")

@main.route("/api/profile", methods=["GET"])
def api_profile_get():
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile()
        db.session.add(profile)
        db.session.commit()
    return jsonify({
        "id": profile.id,
        "name": profile.name or "",
        "specialty": profile.specialty or "",
        "education": profile.education or "",
        "experience": profile.experience or "",
        "skills": profile.skills or "",
        "languages": profile.languages or "",
        "preferred_directions": profile.preferred_directions or "",
        "expected_salary": profile.expected_salary or "",
        "about": profile.about or "",
        "status": profile.status or "",
        "projects": profile.projects or "",
        "contacts": profile.contacts or ""
    })

@main.route("/api/profile", methods=["POST"])
def api_profile_save():
    data = request.get_json()
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile()
        db.session.add(profile)
    profile.name = data.get("name", "")
    profile.specialty = data.get("specialty", "")
    profile.education = data.get("education", "")
    profile.experience = data.get("experience", "")
    profile.skills = data.get("skills", "")
    profile.languages = data.get("languages", "")
    profile.preferred_directions = data.get("preferred_directions", "")
    profile.expected_salary = data.get("expected_salary", "")
    profile.about = data.get("about", "")
    profile.status = data.get("status", "")
    profile.projects = data.get("projects", "")
    profile.contacts = data.get("contacts", "")
    db.session.commit()
    return jsonify({"success": True})

@main.route("/api/profile/default", methods=["POST"])
def api_profile_default():
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile()
        db.session.add(profile)
    profile.name = "Анна Петрова"
    profile.specialty = "09.02.07 Информационные системы и программирование"
    profile.education = "Колледж, 3 курс, дистанционная форма"
    profile.experience = "Нет опыта работы"
    profile.skills = "Python, Git, SQL, HTML, CSS, JavaScript"
    profile.languages = "Русский (родной), Английский (A2)"
    profile.preferred_directions = "QA, Python-разработка, Техподдержка"
    profile.expected_salary = "30 000 - 50 000 руб."
    profile.about = "Студентка 3 курса колледжа, внимательна к деталям, быстро учусь"
    profile.status = "Студент"
    profile.projects = "VacBot — парсер вакансий"
    profile.contacts = "example@mail.com"
    db.session.commit()
    return jsonify({"success": True})

# ---------- Сопроводительное письмо ----------
@main.route("/cover-letter", methods=["GET", "POST"])
def cover_letter_page():
    template = CoverLetterTemplate.query.filter_by(name="default").first()
    if template is None:
        template = CoverLetterTemplate(
            name="default",
            template_text="Уважаемый {company},\n\nМеня зовут {name}, я {status}...\n\nС уважением, {name}"
        )
        db.session.add(template)
        db.session.commit()
    if request.method == "POST":
        template.template_text = request.form.get("template", "")
        db.session.commit()
        return redirect(url_for("main.cover_letter_page"))
    return render_template("cover_letter.html", template=template.template_text)

# ---------- Поисковые запросы ----------
@main.route("/search-queries", methods=["GET", "POST"])
def search_queries_page():
    if request.method == "POST":
        SearchQuery.query.delete()
        raw = request.form.get("queries", "")
        for line in raw.split("\n"):
            q = line.strip()
            if q:
                db.session.add(SearchQuery(text=q))
        db.session.commit()
        return redirect(url_for("main.search_queries_page"))
    queries = SearchQuery.query.order_by(SearchQuery.id).all()
    return render_template("search_queries.html", queries=[q.text for q in queries])

# ---------- Стоп-слова ----------
@main.route("/stopwords")
def stopwords_page():
    return render_template("stopwords.html")

@main.route("/api/stopwords", methods=["GET"])
def api_stopwords():
    words = StopWord.query.order_by(StopWord.word).all()
    return jsonify([{"id": w.id, "word": w.word, "category": w.category} for w in words])

@main.route("/api/stopwords/add", methods=["POST"])
def api_stopwords_add():
    data = request.get_json()
    word = data.get("word", "").strip().lower()
    category = data.get("category", "general")
    if not word:
        return jsonify({"error": "Слово не может быть пустым"}), 400
    if StopWord.query.filter_by(word=word).first():
        return jsonify({"error": "Такое слово уже есть"}), 400
    sw = StopWord(word=word, category=category)
    db.session.add(sw)
    db.session.commit()
    return jsonify({"success": True, "id": sw.id})

@main.route("/api/stopwords/delete/<int:word_id>", methods=["POST"])
def api_stopwords_delete(word_id):
    sw = StopWord.query.get_or_404(word_id)
    db.session.delete(sw)
    db.session.commit()
    return jsonify({"success": True})

@main.route("/api/stopwords/bulk", methods=["POST"])
def api_stopwords_bulk():
    data = request.get_json()
    words = data.get("words", [])
    StopWord.query.delete()
    for w in words:
        db.session.add(StopWord(word=w["word"].lower(), category=w.get("category", "general")))
    db.session.commit()
    return jsonify({"success": True, "count": len(words)})

# ---------- Администрирование (планировщик) ----------
@main.route('/admin/parse', methods=['POST'])
def manual_parse():
    from app.parser_service import run_parser_and_save
    added, updated = run_parser_and_save()
    return jsonify({
        'status': 'success',
        'added': added,
        'updated': updated,
        'total': Vacancy.query.count()
    })

@main.route('/admin/parse/start-scheduler', methods=['POST'])
def start_scheduler_route():
    from app.scheduler import start_scheduler
    interval = int(os.getenv('PARSING_INTERVAL_HOURS', 24))
    start_scheduler(interval_hours=interval, run_immediately=False)
    return jsonify({'status': 'scheduler_started', 'interval_hours': interval})

@main.route('/admin/parse/stop-scheduler', methods=['POST'])
def stop_scheduler_route():
    from app.scheduler import stop_scheduler
    stop_scheduler()
    return jsonify({'status': 'scheduler_stopped'})