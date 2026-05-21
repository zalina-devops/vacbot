import json
from collections import Counter


# Ключевые слова по направлениям
DIRECTIONS = {
    "QA / Тестирование": [
        "тестировщик", "qa", "quality", "тестирование", "tester",
        "postman", "jira", "баг", "тест-кейс", "selenium",
    ],
    "Python / Backend": [
        "python", "django", "fastapi", "flask", "backend",
        "бэкенд", "разработчик", "developer",
    ],
    "1С": [
        "1с", "1c", "bsl", "конфигурация", "внедрение 1с",
    ],
    "Сисадмин / Техподдержка": [
        "администратор", "техподдержка", "поддержка", "helpdesk",
        "windows", "linux", "active directory", "сети",
    ],
    "Аналитика данных": [
        "аналитик", "analyst", "sql", "pandas", "excel", "bi",
        "tableau", "power bi", "данные",
    ],
    "Фронтенд / Верстка": [
        "html", "css", "javascript", "верстальщик", "frontend",
        "react", "vue", "js",
    ],
}


def detect_direction(vacancy: dict) -> str:
    """Определяет направление вакансии по ключевым словам."""
    text = " ".join([
        vacancy.get("title", ""),
        vacancy.get("snippet_requirement", "") or "",
        vacancy.get("snippet_responsibility", "") or "",
    ]).lower()

    scores = {}
    for direction, keywords in DIRECTIONS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[direction] = score

    if not scores:
        return "Другое"
    return max(scores, key=scores.get)


def load_vacancies(path: str = "data/vacancies.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["vacancies"]


def analyze(vacancies: list[dict]) -> dict:
    """Анализирует список вакансий, возвращает статистику и разбивку по направлениям."""
    enriched = []
    for v in vacancies:
        v["direction"] = detect_direction(v)
        enriched.append(v)

    direction_counts = Counter(v["direction"] for v in enriched)

    with_salary = [v for v in enriched if v["salary"] != "не указана"]

    return {
        "total": len(enriched),
        "with_salary": len(with_salary),
        "by_direction": dict(direction_counts.most_common()),
        "vacancies": enriched,
    }


def print_report(analysis: dict):
    """Выводит читаемый отчёт в терминал."""
    print(f"\n{'='*50}")
    print(f"  Всего вакансий:       {analysis['total']}")
    print(f"  С указанной зарплатой: {analysis['with_salary']}")
    print(f"\n  Разбивка по направлениям:")
    for direction, count in analysis["by_direction"].items():
        bar = "█" * count
        print(f"    {direction:<30} {count:>3}  {bar}")

    print(f"\n  Топ-5 вакансий (первые по списку):")
    for v in analysis["vacancies"][:5]:
        print(f"\n  [{v['direction']}] {v['title']}")
        print(f"    Компания: {v['company']}")
        print(f"    Зарплата: {v['salary']}")
        print(f"    Ссылка:   {v['url']}")


def save_analysis(analysis: dict, path: str = "data/analysis.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"\n  Анализ сохранён в {path}")


if __name__ == "__main__":
    print("=== VacBot: анализ вакансий ===")
    vacancies = load_vacancies()
    analysis = analyze(vacancies)
    print_report(analysis)
    save_analysis(analysis)


def print_by_source(analysis: dict):
    source_counts = Counter(v["source"] for v in analysis["vacancies"] if "source" in v)
    if source_counts:
        print("\n  По источникам:")
        for src, cnt in source_counts.most_common():
            bar = "█" * cnt
            print(f"    {src:<20} {cnt:>3}  {bar}")
