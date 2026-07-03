import os
import re
import requests
from app import db
from app.models import Vacancy, UserProfile, StopWord, CoverLetterTemplate

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Список моделей для fallback (от наиболее предпочтительной к запасным)
MODELS_TO_TRY = [
    "qwen/qwen3-next-80b-a3b-instruct:free",  # Основная: мощная модель 80B
    "google/gemma-4-31b-it:free",              # Альтернатива от Google
    "nvidia/nemotron-3-super-120b-a12b:free",  # Мощная модель 120B
    "openrouter/free"                          # Автоматический роутер
]

DEFAULT_MODEL = MODELS_TO_TRY[0]

def clean_markdown(text):
    """Убирает Markdown-разметку из текста AI"""
    if not text or not isinstance(text, str):
        return text
    # Убираем заголовки ##
    text = re.sub(r'##\s*', '', text)
    # Убираем жирный текст **...**
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Заменяем списки "-" на "•"
    text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)
    return text.strip()

def call_openrouter(prompt, system_prompt=None, model=None, max_tokens=2000):
    """
    Вызов API OpenRouter с автоматическим fallback и поддержкой system prompt.
    
    Args:
        prompt: Текст запроса к модели (user message)
        system_prompt: Системная инструкция (опционально)
        model: Конкретная модель (опционально)
        max_tokens: Максимальное количество токенов в ответе
        
    Returns:
        str: Ответ модели или сообщение об ошибке
    """
    if not OPENROUTER_API_KEY:
        return "🔧 API-ключ OpenRouter не настроен. Добавьте OPENROUTER_API_KEY в .env"
    
    if model:
        models_to_try = [model]
    else:
        models_to_try = MODELS_TO_TRY
    
    last_error = None
    
    for current_model in models_to_try:
        try:
            # Формируем сообщения с system prompt если есть
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://vacbot.local",
                    "X-Title": "VacBot"
                },
                json={
                    "model": current_model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": max_tokens
                },
                timeout=90  # Увеличили таймаут
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                
                # Проверяем, не обрезан ли ответ
                finish_reason = data["choices"][0].get("finish_reason", "")
                if finish_reason == "length":
                    print(f"⚠️ Ответ от {current_model} обрезан (достигнут лимит токенов)")
                    # Можно попробовать увеличить max_tokens или сменить модель
                
                return content
                
            elif response.status_code == 404:
                print(f"⚠️ Модель {current_model} недоступна (404), пробуем следующую...")
                last_error = f"Модель {current_model} недоступна"
                continue
            elif response.status_code == 429:
                print(f"⚠️ Превышен лимит для модели {current_model} (429), пробуем следующую...")
                last_error = f"Превышен лимит запросов для модели {current_model}"
                continue
            else:
                error_text = response.text[:200]
                return f"❌ Ошибка API ({response.status_code}): {error_text}"
                
        except requests.exceptions.Timeout:
            print(f"⚠️ Таймаут для модели {current_model}, пробуем следующую...")
            last_error = f"Таймаут запроса к модели {current_model}"
            continue
        except Exception as e:
            return f"❌ Ошибка соединения: {str(e)}"
    
    return f"❌ Все модели недоступны. Последняя ошибка: {last_error}"


def adapt_resume(vacancy_id):
    """Адаптирует резюме под конкретную вакансию с помощью AI."""
    vacancy = db.session.get(Vacancy, vacancy_id)
    if not vacancy:
        return "Вакансия не найдена"
    
    profile = UserProfile.query.first()
    if not profile:
        return "Профиль не заполнен"

    system_prompt = """Ты — карьерный консультант для junior-разработчиков. 
Твоя задача — адаптировать резюме под конкретную вакансию, используя ТОЛЬКО информацию из профиля соискателя.
НЕ выдумывай навыки, которых нет в профиле.
Отвечай ТОЛЬКО на русском языке.
НЕ используй Markdown-символы: не ставь ##, **, *, __, не используй дефисы в начале строк.
Ничего не объясняй, не рассуждай, не комментируй свои действия. Просто выведи готовый текст резюме."""

    prompt = f"""Адаптируй резюме под следующую вакансию.

ВАЖНЫЕ ПРАВИЛА:
1. Используй ТОЛЬКО навыки из профиля. НЕ выдумывай опыт.
2. Учебные проекты — это валидный опыт.
3. Если в вакансии требуется навык, которого нет в профиле — промолчи о нём.
4. Пиши уверенно, но честно: "изучаю", "применяла в проектах", "базовый уровень".
5. Раздел "О себе" должен содержать 3-4 полных предложения.
6. Раздел "Ключевые навыки" должен содержать 4-6 пунктов.
7. Для списка навыков используй цифры с точкой (1., 2., 3.) — НЕ используй дефисы.
8. НЕ используй Markdown: не ставь ##, **, *, __, не используй дефисы в начале строк.
9. НЕ объясняй, НЕ рассуждай, НЕ комментируй. Просто выведи текст.

ВАКАНСИЯ:
Название: {vacancy.title}
Компания: {vacancy.company}
Требования: {vacancy.snippet_requirement or 'Не указаны'}

ПРОФИЛЬ СОИСКАТЕЛЯ:
Имя: {profile.name or ''}
Специальность: {profile.specialty or ''}
Навыки: {profile.skills or ''}
Опыт: {profile.experience or ''}
Проекты: {profile.projects or ''}
О себе: {profile.about or ''}

Выведи ТОЛЬКО текст резюме в следующем формате (без Markdown, без дефисов):

[3-4 полных предложения о себе]

Ключевые навыки
1. [навык 1: как применяла в проектах]
2. [навык 2: как применяла в проектах]
3. [навык 3: уровень владения]
4. [навык 4: уровень владения]
5. [навык 5: уровень владения]
6. [навык 6: уровень владения]

Ничего лишнего не пиши. Только текст в указанном формате."""

    result = call_openrouter(prompt, system_prompt=system_prompt, max_tokens=2000)
    
    # Очистка Markdown на всякий случай
    if result and isinstance(result, str):
        result = clean_markdown(result)
    
    return result


def generate_cover_letter(vacancy_id):
    """Генерирует сопроводительное письмо для конкретной вакансии."""
    vacancy = db.session.get(Vacancy, vacancy_id)
    if not vacancy:
        return "Вакансия не найдена"
    
    profile = UserProfile.query.first()
    if not profile:
        return "Профиль не заполнен"

    system_prompt = """Ты — HR-эксперт, который пишет сопроводительные письма для junior-специалистов.
Пиши на русском языке, искренне и конкретно.
НЕ упоминай навыки, которых нет в профиле соискателя.
Объём: 3-4 коротких абзаца, максимум 200 слов.
НЕ используй Markdown-символы.
Ничего не объясняй, не рассуждай, просто напиши письмо."""

    prompt = f"""Напиши сопроводительное письмо для вакансии.

ТРЕБОВАНИЯ К ПИСЬМУ:
1. Начинается с "Здравствуйте!" и обращения к компании
2. Показывает искренний интерес к вакансии (не шаблонный)
3. Связывает 1-2 конкретных навыка из профиля с требованиями вакансии
4. Упоминает учебные проекты как доказательство навыков
5. Заканчивается вопросом о следующих шагах
6. НЕ упоминает навыки, которых нет в профиле
7. Объём: 3-4 коротких абзаца, максимум 200 слов
8. НЕ используй Markdown: не ставь ##, **, *, __, не используй дефисы
9. НЕ объясняй, НЕ рассуждай, просто напиши письмо

ВАКАНСИЯ:
Название: {vacancy.title}
Компания: {vacancy.company}
Требования: {vacancy.snippet_requirement or 'Не указаны'}

ПРОФИЛЬ СОИСКАТЕЛЯ:
Имя: {profile.name or ''}
Специальность: {profile.specialty or ''}
Навыки: {profile.skills or ''}
Опыт: {profile.experience or ''}
Проекты: {profile.projects or ''}
О себе: {profile.about or ''}

Напиши письмо в следующем формате:

Здравствуйте!

[1 абзац: интерес + связь с компанией]

[2 абзац: релевантный опыт/проекты]

[3 абзац: мотивация + закрывающий вопрос]

С уважением,
{profile.name or 'Соискатель'}

Ничего лишнего не пиши. Только текст письма."""

    result = call_openrouter(prompt, system_prompt=system_prompt, max_tokens=1500)
    
    # Очистка Markdown
    if result and isinstance(result, str):
        result = clean_markdown(result)
    
    return result


def calculate_match_percentage(vacancy):
    """Вычисляет процент соответствия вакансии профилю соискателя."""
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
    """Получает список стоп-слов из базы данных."""
    stopwords = StopWord.query.all()
    return [sw.word for sw in stopwords]


def filter_requirements_with_stopwords(requirement_text):
    """Фильтрует требования вакансии, удаляя строки с стоп-словами."""
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