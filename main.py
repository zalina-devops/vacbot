import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.fetcher import collect_all, save_to_json
from src.analyzer import load_vacancies, analyze, print_report, save_analysis, print_by_source

def main():
    os.makedirs("data", exist_ok=True)
    print("╔══════════════════════════════════════╗")
    print("║   VacBot — мультисорс поиск работы   ║")
    print("╚══════════════════════════════════════╝\n")

    print("Шаг 1/2: Сбор вакансий...\n")
    vacancies = collect_all()
    save_to_json(vacancies, "data/vacancies.json")

    print("\nШаг 2/2: Анализ...\n")
    vacancies = load_vacancies("data/vacancies.json")
    analysis = analyze(vacancies)
    print_report(analysis)
    print_by_source(analysis)
    save_analysis(analysis, "data/analysis.json")

    print("\n✓ Готово!")

if __name__ == "__main__":
    main()
