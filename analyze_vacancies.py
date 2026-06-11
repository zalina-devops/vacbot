import json
from pathlib import Path

def analyze_vacancies(file_path="data/vacancies.json"):
    path = Path(file_path)
    if not path.exists():
        print(f"Файл {file_path} не найден!")
        return

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    vacancies = data.get("vacancies", []) if isinstance(data, dict) else data

    print(f"\n=== АНАЛИЗ ВАКАНСИЙ ({len(vacancies)} шт.) ===\n")

    junior_keywords = ["junior", "стажер", "стажёр", "trainee", "intern", "ученик", "младший"]
    good = []
    middle_senior = []
    office = []
    other = []

    for v in vacancies:
        title = v.get("title", "").lower()
        city = v.get("city", "").lower()
        requirement = v.get("requirement", "").lower()
        full = f"{title} {city} {requirement}"

        if any(k in full for k in junior_keywords):
            good.append(v)
        elif any(x in full for x in ["middle", "senior", "lead", "ведущий"]):
            middle_senior.append(v)
        elif any(x in full for x in ["офис", "гибрид", "на территории"]):
            office.append(v)
        else:
            other.append(v)

    print(f"✅ Подходящие (Junior / Стажёр): {len(good)}")
    print(f"❌ Middle/Senior: {len(middle_senior)}")
    print(f"🏢 Офис/Гибрид: {len(office)}")
    print(f"📦 Остальные: {len(other)}\n")

    print("=== ТОП ПОДХОДЯЩИХ ВАКАНСИЙ ===")
    for v in good[:15]:
        print(f"• {v.get('title')} | {v.get('company')} | {v.get('city')} | {v.get('salary')}")

    if middle_senior:
        print("\n=== Примеры Middle/Senior (отфильтровать): ===")
        for v in middle_senior[:5]:
            print(f"• {v.get('title')} | {v.get('company')}")

if __name__ == "__main__":
    analyze_vacancies()