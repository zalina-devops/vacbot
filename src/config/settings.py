# src/config/settings.py
import os

# РАСШИРЕННЫЕ поисковые запросы
SEARCH_QUERIES = [
    # Python разработка (ваш приоритет)
    #"python разработчик",
    #"python developer",
    #"python программист",
    #"python стажер",
    #"стажер",

    # Web разработка
    # "django разработчик",
    # "flask разработчик",

    # Парсинг и автоматизация
    # "парсинг python",
    # "автоматизация python",
    #"scrapy разработчик",

    # Работа с данными
    # "аналитик данных python",
    # "data обработка",
    #"оператор пк",

    "python стажер",
    "junior python",
    "junior python developer",
    "python trainee",

    "тестировщик junior",
    "qa junior",
    "manual qa",

    "разметка данных",
    "data annotation",
    "data labeling",

    # "ассистент аналитика",
    "junior analyst",

    #"обработка данных",
]

# Не использовать слова-исключения в поиске
EXCLUDE_WORDS = [
    "call-центр", "продажи", "телемаркетинг"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

CACHE_TTL = 30
SUPERJOB_TOKEN = os.getenv("SUPERJOB_TOKEN", "")