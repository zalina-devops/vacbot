import os
import requests
from app import db
from app.models import Vacancy, UserProfile, StopWord, CoverLetterTemplate

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_openrouter(prompt, model="openrouter/auto"):
    if not OPENROUTER_API_KEY:
        return "🔧 API-ключ OpenRouter не настроен."
    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ Ошибка API: {response.status_code} - {response.text}"
    except Exception as e:
        return f"❌ Ошибка: {e}"


def adapt_resume(vacancy_id):
    vacancy = db.session.get(Vacancy, vacancy_id) # тута
    if not vacancy:
        return "Вакансия не найдена"
    profile = UserProfile.query.first()
    if not profile:
        return "Профиль не заполнен"

    prompt = f"""
Ты — эксперт по адаптации резюме. Твоя задача — переписать резюме соискателя под конкретную вакансию.

Вакансия:
Название: {vacancy.title}
Компания: {vacancy.company}
Основные требования:
{vacancy.snippet_requirement or 'Не указаны'}
Обязанности:
{vacancy.snippet_responsibility or 'Не указаны'}

Профиль соискателя:
Имя: {profile.name or ''}
Специальность: {profile.specialty or ''}
Образование: {profile.education or ''}
Опыт: {profile.experience or ''}
Навыки: {profile.skills or ''}
Языки: {profile.languages or ''}
Проекты: {profile.projects or ''}
О себе: {profile.about or ''}

Напиши адаптированную версию раздела "О себе" и "Ключевые навыки" (кратко, 3–5 предложений), которая максимально соответствует требованиям вакансии. Используй ключевые слова из вакансии, покажи релевантность опыта. Сохрани правдивость информации.
Ответ должен быть на русском языке.
"""
    return call_openrouter(prompt)


def generate_cover_letter(vacancy_id):
    vacancy = db.session.get(Vacancy, vacancy_id) # тута
    if not vacancy:
        return "Вакансия не найдена"
    profile = UserProfile.query.first()
    if not profile:
        return "Профиль не заполнен"

    prompt = f"""
Ты — ассистент по написанию сопроводительных писем. На основе данных о соискателе и вакансии создай убедительное, лаконичное письмо (3–4 абзаца).

Вакансия: {vacancy.title} в компании {vacancy.company}
Требования: {vacancy.snippet_requirement or 'Не указаны'}

О соискателе:
Имя: {profile.name or ''}
Специальность: {profile.specialty or ''}
Навыки: {profile.skills or ''}
Опыт: {profile.experience or ''}
Проекты: {profile.projects or ''}

Письмо должно быть на русском языке, начинаться с "Здравствуйте!", показывать связь навыков с требованиями, быть без шаблонных фраз. Не упоминай отсутствующие навыки.
"""
    return call_openrouter(prompt)


def calculate_match_percentage(vacancy):
    profile = UserProfile.query.first()
    if not profile:
        return 0
    profile_skills = set(s.strip().lower() for s in (profile.skills or "").split(',') if s.strip())
    preferred_dirs = set(d.strip().lower() for d in (profile.preferred_directions or "").split(',') if d.strip())

    req = (vacancy.snippet_requirement or "") + " " + (vacancy.title or "")
    req_lower = req.lower()
    matched_skills = sum(1 for skill in profile_skills if skill in req_lower)
    skill_score = (matched_skills / len(profile_skills)) * 60 if profile_skills else 0

    vacancy_dir = (vacancy.direction or "").lower()
    if preferred_dirs and vacancy_dir in preferred_dirs:
        dir_score = 30
    elif not preferred_dirs:
        dir_score = 15
    else:
        dir_score = 0

    salary_score = 10 if vacancy.salary and "не указана" not in vacancy.salary else 0
    total = min(100, skill_score + dir_score + salary_score)
    return int(total)


def get_stopwords_list():
    stopwords = StopWord.query.all()
    return [sw.word for sw in stopwords]


def filter_requirements_with_stopwords(requirement_text):
    stopwords = get_stopwords_list()
    if not stopwords:
        return requirement_text
    lines = requirement_text.split('\n')
    filtered_lines = []
    for line in lines:
        line_lower = line.lower()
        if any(sw.lower() in line_lower for sw in stopwords):
            continue
        filtered_lines.append(line)
    return '\n'.join(filtered_lines)