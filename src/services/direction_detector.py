def detect_direction(text: str) -> str:
    """Определяет направление вакансии по тексту"""
    text_lower = text.lower()

    directions = {
        'Python': ['python', 'django', 'flask', 'fastapi'],
        'QA': ['qa', 'тестировщик', 'тестирование', 'quality assurance'],
        'Аналитика': ['аналитик', 'анализ', 'data', 'bi'],
        'Техподдержка': ['поддержка', 'support', 'оператор'],
    }

    for direction, keywords in directions.items():
        if any(kw in text_lower for kw in keywords):
            return direction
    return 'Другое'