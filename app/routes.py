import os
import json
import subprocess
import sys
import threading

from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, Response, render_template_string, make_response

from . import db
from .models import Vacancy, BoardCard, UserProfile, CoverLetterTemplate, SearchQuery, StopWord
from .config import Config
from .ai_agent import calculate_match_percentage

main = Blueprint("main", __name__)

parser_lock = threading.Lock()
parser_running = False

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

    # Получаем уникальные направления из БД
    directions = sorted(set(
        r[0] for r in db.session.query(Vacancy.direction).distinct() if r[0]
    ))
    sources = sorted(set(
        r[0] for r in db.session.query(Vacancy.source).distinct() if r[0]
    ))

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
    """Меняет статус карточки на канбан-доске."""
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
        card.status = "starred"
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
    """Добавляет / убирает вакансию из избранного."""
    if not db.session.get(Vacancy, vacancy_id):
        return jsonify({"error": "vacancy not found"}), 404

    card = get_or_create_card(vacancy_id)
    card.starred = not card.starred

    if card.starred:
        card.status = "starred"
    elif card.status == "starred":
        card.status = "new"

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
    global parser_running

    if parser_running:
        return jsonify({
            "ok": False,
            "error": "Парсер уже выполняется"
        }), 409

    try:
        parser_running = True

        import sys
        import json
        from pathlib import Path

        src_path = Path(__file__).parent.parent / 'src'
        sys.path.insert(0, str(src_path))

        from src.fetcher import collect_all
        from src.services.vacancy_storage import save_to_database

        print("🚀 Запуск парсинга через /api/run-parser")

        vacancies = collect_all()

        if vacancies:
            save_to_database(vacancies)

            with open(
                'data/vacancies.json',
                'w',
                encoding='utf-8'
            ) as f:
                json.dump(
                    vacancies,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

        return jsonify({
            "ok": True,
            "message": f"Парсер завершен. Найдено {len(vacancies)} вакансий",
            "total": len(vacancies)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500

    finally:
        parser_running = False

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
@main.route("/api/adapt-resume/<vacancy_id>", methods=["GET", "POST"])
def api_adapt_resume(vacancy_id):
    try:
        from app.ai_agent import adapt_resume
        result = adapt_resume(vacancy_id)
        if result is None:
            result = "Ошибка: AI вернул пустой ответ. Проверьте API-ключ и баланс OpenRouter."
        return jsonify({"success": True, "text": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
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

# ============= НОВЫЕ РОУТЫ ДЛЯ ФИЛЬТРОВ =============

@main.route('/filters', methods=['GET'])
def manage_filters():
    """Страница управления фильтрами"""
    whitelist = [q.text for q in SearchQuery.query.filter_by(is_active=True).all()]
    blacklist = [sw.word for sw in StopWord.query.all()]
    return render_template('filters.html', whitelist=whitelist, blacklist=blacklist)

@main.route('/save-filters', methods=['POST'])
def save_filters():
    """Сохраняет фильтры из формы"""
    try:
        # Очищаем старые фильтры
        SearchQuery.query.delete()
        StopWord.query.delete()

        # Сохраняем белый список (разрешенные слова)
        whitelist_words = request.form.getlist('whitelist[]')
        for word in whitelist_words:
            if word and word.strip():
                db.session.add(SearchQuery(
                    text=word.strip().lower(),
                    is_active=True
                ))

        # Сохраняем черный список (стоп-слова)
        blacklist_words = request.form.getlist('blacklist[]')
        for word in blacklist_words:
            if word and word.strip():
                db.session.add(StopWord(word=word.strip().lower()))

        db.session.commit()
        flash('✅ Фильтры успешно сохранены!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'❌ Ошибка при сохранении: {str(e)}', 'error')

    return redirect(url_for('main.manage_filters'))


@main.route('/api/rebuild-database', methods=['POST'])
def rebuild_database():
    try:
        BoardCard.query.delete()
        Vacancy.query.delete()

        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "База данных очищена"
        })

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@main.route('/api/download-backup')
def download_backup():
    """Скачивание бэкапа базы данных"""
    vacancies = Vacancy.query.all()
    backup_data = []

    for v in vacancies:
        backup_data.append({
            'id': v.id,
            'title': v.title,
            'company': v.company,
            'url': v.url,
            'salary': v.salary,
            'direction': v.direction,
            'source': v.source,
            'snippet_requirement': v.snippet_requirement,
            'created_at': v.created_at.isoformat() if v.created_at else None
        })

    backup_json = json.dumps(backup_data, ensure_ascii=False, indent=2)

    return Response(
        backup_json,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=vacbot_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        }
    )
    
# ---------- PDF Резюме ----------
@main.route("/api/resume/pdf/<path:vacancy_id>")
def generate_resume_pdf(vacancy_id):
    from app.ai_agent import adapt_resume
    from app.models import Vacancy
    
    profile = UserProfile.query.first()
    if not profile:
        return jsonify({'error': 'Профиль не заполнен'}), 400
    
    vacancy = db.session.get(Vacancy, vacancy_id)
    clean = request.args.get('clean', '0') == '1'
    
    # Получаем адаптированный текст
    try:
        adapted_text = adapt_resume(vacancy_id)
        if adapted_text.startswith('❌') or adapted_text.startswith('🔧'):
            adapted_text = None
    except:
        adapted_text = None
    
    # HTML-шаблон резюме
    html_template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Резюме — {{ name }}</title>
    <style>
        @page { size: A4; margin: 0; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #2d3436; line-height: 1.6; padding: 20px; }
        .page { width: 210mm; min-height: 297mm; padding: 50px; background: white; margin: 0 auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3); border-radius: 12px; position: relative; overflow: hidden; }
        .top-bar { position: absolute; top: 0; left: 0; right: 0; height: 6px; background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%); }
        .header { display: flex; align-items: center; gap: 30px; margin-bottom: 35px; padding-bottom: 25px; border-bottom: 2px solid #f0f0f0; }
        .avatar { width: 90px; height: 90px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-size: 32px; font-weight: 700; flex-shrink: 0; box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4); }
        .name-block h1 { font-size: 30px; font-weight: 700; color: #2d3436; margin-bottom: 6px; letter-spacing: -0.5px; }
        .subtitle { color: #636e72; font-size: 14px; margin-bottom: 3px; }
        .contact-info { display: flex; gap: 15px; margin-top: 10px; font-size: 12px; color: #636e72; flex-wrap: wrap; }
        .contact-item { display: flex; align-items: center; gap: 5px; background: #f8f9fa; padding: 4px 10px; border-radius: 12px; }
        .section { margin-bottom: 25px; }
        .section-title { font-size: 13px; font-weight: 700; color: #667eea; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid #e8e8e8; display: flex; align-items: center; gap: 8px; }
        .section-title::before { content: ''; width: 4px; height: 18px; background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); border-radius: 2px; }
        .about-text { font-size: 13px; color: #4a4a4a; line-height: 1.8; text-align: justify; }
        .skills-container { display: flex; flex-wrap: wrap; gap: 8px; }
        .skill-tag { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border: 1px solid #dee2e6; padding: 5px 14px; border-radius: 20px; font-size: 12px; color: #495057; font-weight: 500; }
        .skill-tag.highlight { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-color: transparent; box-shadow: 0 3px 10px rgba(102, 126, 234, 0.3); }
        .project-card { background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); border-left: 4px solid #667eea; padding: 15px 18px; margin-bottom: 12px; border-radius: 0 10px 10px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .project-name { font-weight: 700; color: #2d3436; font-size: 14px; margin-bottom: 5px; }
        .project-desc { color: #636e72; font-size: 12px; line-height: 1.6; }
        .experience-text { font-size: 13px; color: #4a4a4a; line-height: 1.7; padding-left: 15px; border-left: 3px solid #e8e8e8; }
        .adapted-block { background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 100%); border: 1px solid #ffeaa7; border-radius: 10px; padding: 18px; margin-top: 20px; position: relative; }
        .adapted-label { font-size: 10px; font-weight: 700; color: #d63031; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .adapted-text { font-size: 13px; color: #2d3436; line-height: 1.7; }
        .footer { margin-top: 35px; padding-top: 15px; border-top: 2px solid #f0f0f0; text-align: center; font-size: 11px; color: #b2bec3; }
        .footer a { color: #667eea; text-decoration: none; }
        .print-btn { position: fixed; top: 20px; right: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); z-index: 1000; }
        .print-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); }
        @media print { body { background: white; padding: 0; } .page { box-shadow: none; border-radius: 0; margin: 0; } .print-btn { display: none; } }
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">🖨️ Печать / Сохранить как PDF</button>
    
    <div class="page">
        <div class="top-bar"></div>
        
        <div class="header">
            <div class="avatar">{{ name[0] if name and name|length > 0 else '?' }}</div>
            <div class="name-block">
                <h1>{{ name or 'Имя не указано' }}</h1>
                <p class="subtitle">{{ specialty or 'Специальность не указана' }}</p>
                <p class="subtitle">{{ education or 'Образование не указано' }}</p>
                <div class="contact-info">
                    <span class="contact-item">🌐 {{ languages or 'Языки не указаны' }}</span>
                    <span class="contact-item">💰 {{ expected_salary or 'По договорённости' }}</span>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">О себе</div>
            {% if adapted_text %}
                <p class="about-text">{{ adapted_text | safe }}</p>
            {% else %}
                <p class="about-text">{{ about or 'Информация не заполнена' }}</p>
            {% endif %}
        </div>

        <div class="section">
            <div class="section-title">Ключевые навыки</div>
            <div class="skills-container">
                {% for skill in skills.split(',') %}
                    {% if skill.strip() %}
                    <span class="skill-tag {% if skill.strip().lower() in ['docker', 'python', 'postgresql', 'git', 'docker compose', 'linux', 'bash', 'flask', 'node.js', 'express', 'rest api', 'jwt', 'nginx', 'ci/cd'] %}highlight{% endif %}">
                        {{ skill.strip() }}
                    </span>
                    {% endif %}
                {% endfor %}
            </div>
        </div>

        {% if projects %}
        <div class="section">
            <div class="section-title">Проекты</div>
            {% for project in projects.split(';') %}
                {% if project.strip() %}
                <div class="project-card">
                    {% set parts = project.split('—', 1) %}
                    <div class="project-name">{{ parts[0].strip() }}</div>
                    {% if parts|length > 1 %}
                    <div class="project-desc">{{ parts[1].strip() }}</div>
                    {% endif %}
                </div>
                {% endif %}
            {% endfor %}
        </div>
        {% endif %}

        {% if experience %}
        <div class="section">
            <div class="section-title">Опыт</div>
            <div class="experience-text">{{ experience }}</div>
        </div>
        {% endif %}

        {% if adapted_text and not clean %}
        <div class="adapted-block">
            <div class="adapted-label">✨ Адаптировано под вакансию: {{ vacancy_title or 'Текущая вакансия' }}</div>
            <div class="adapted-text">{{ adapted_text | safe }}</div>
        </div>
        {% endif %}

        <div class="footer">
            <p>GitHub: <a href="https://github.com/zali-dev">github.com/zali-dev</a></p>
            {% if not clean %}
            <p style="margin-top: 5px;">Резюме сгенерировано с помощью VacBot</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

    # Рендерим через Flask (правильный Jinja2)
    html = render_template_string(html_template,
        name=profile.name,
        specialty=profile.specialty,
        education=profile.education,
        about=profile.about,
        skills=profile.skills or '',
        projects=profile.projects,
        experience=profile.experience,
        languages=profile.languages,
        expected_salary=profile.expected_salary,
        adapted_text=adapted_text,
        vacancy_title=vacancy.title if vacancy else None,
        clean=clean
    )
    
    # Генерируем PDF через pdfkit (альтернатива weasyprint для Windows)
    try:
        import pdfkit
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
        pdf = pdfkit.from_string(html, False, configuration=config)
    except Exception as e:
        # Если pdfkit не работает — возвращаем HTML для печати
        return Response(html, mimetype='text/html')
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=resume_{"clean_" if clean else ""}{profile.name or "vacbot"}_{vacancy_id}.pdf'
    return response
