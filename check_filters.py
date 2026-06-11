import json
from pathlib import Path

# Простая версия фильтра без БД (для анализа)
def is_vacancy_suitable_simple(vacancy: dict) -> bool:
    title = (vacancy.get("title") or "").lower()
    requirement = (vacancy.get("requirement") or "").lower()
    city = (vacancy.get("city") or "").lower()
    full_text = f"{title} {requirement} {city}"

    # Жёсткие слова-исключения
    bad_words = [
        "senior", "middle", "lead", "ведущий", "архитектор", "teamlead",
        "опыт от", "опыт более", "коммерческ", "офис", "гибрид",
        "call center", "колл центр", "телемаркет", "оператор"
    ]

    for word in bad_words:
        if word in full_text:
            return False

    # Должно быть хотя бы одно хорошее слово
    good_words = ["junior", "стажер", "стажёр", "trainee", "intern", "ученик", "младший"]
    return any(word in full_text for word in good_words)


def check_filters():
    path = Path("data/vacancies.json")
    if not path.exists():
        print("Файл data/vacancies.json не найден!")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    vacancies = data.get("vacancies", []) if isinstance(data, dict) else data

    passed = []
    blocked = []

    print("🔍 Проверка фильтров...\n")

    for v in vacancies:
        if is_vacancy_suitable_simple(v):
            passed.append(v)
        else:
            blocked.append(v)

    print(f"✅ Прошло фильтры: {len(passed)}")
    print(f"🚫 Отфильтровано: {len(blocked)}\n")

    print("=== ПРОШЛИ ФИЛЬТРЫ (первые 20) ===")
    for v in passed[:20]:
        print(f"✓ {v.get('title')} | {v.get('company')} | {v.get('city')}")

    if blocked:
        print("\n=== ПРИМЕРЫ ОТФИЛЬТРОВАННЫХ ===")
        for v in blocked[:10]:
            print(f"✗ {v.get('title')} | {v.get('company')}")

if __name__ == "__main__":
    check_filters()