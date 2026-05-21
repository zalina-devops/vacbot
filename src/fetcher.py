import requests
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()

def get_stopwords_from_db():
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app import create_app
        from app.models import StopWord
        app = create_app()
        with app.app_context():
            stopwords = StopWord.query.all()
            return [sw.word.lower() for sw in stopwords]
    except Exception as e:
        print(f"⚠️ Не удалось загрузить стоп-слова из БД: {e}")
        return []

def check_stopwords_in_requirements(requirement_text, stopwords):
    if not requirement_text or not stopwords:
        return False
    text_lower = requirement_text.lower()
    for sw in stopwords:
        if sw in text_lower:
            print(f"    🚫 Отфильтровано по стоп-слову: '{sw}'")
            return True
    return False

def get_search_queries_from_db():
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app import create_app
        from app.models import SearchQuery
        app = create_app()
        with app.app_context():
            queries = SearchQuery.query.filter_by(is_active=True).all()
            search_queries = [q.text for q in queries]
            if queries:
                return [q.text for q in queries]
    except Exception as e:
        print(f"⚠️ Не удалось загрузить запросы из БД: {e}")
    return [
        "QA тестировщик",
        "тестировщик стажёр",
        "python разработчик стажёр",
        "системный администратор стажёр",
        "1С стажёр",
        "техническая поддержка",
        "аналитик данных стажёр",
        "верстальщик стажёр"
    ]

"""
SEARCH_QUERIES = [
    "QA тестировщик",
    "тестировщик стажёр",
    "python разработчик стажёр",
    "системный администратор стажёр",
    "1С стажёр",
    "техническая поддержка",
    "аналитик данных стажёр",
    "верстальщик стажёр",
]
"""

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}

SUPERJOB_TOKEN = os.getenv("SUPERJOB_TOKEN", "")


class BaseParser(ABC):
    source_name: str = ""

    @abstractmethod
    def fetch(self, query: str) -> list[dict]:
        pass

    def _normalize(self, **kwargs) -> dict:
        return {
            "id": str(kwargs.get("id", "")),
            "source": self.source_name,
            "title": kwargs.get("title", ""),
            "company": kwargs.get("company", ""),
            "salary": kwargs.get("salary", "не указана"),
            "city": kwargs.get("city", ""),
            "url": kwargs.get("url", ""),
            "published": kwargs.get("published", ""),
            "snippet_requirement": kwargs.get("requirement", ""),
            "snippet_responsibility": kwargs.get("responsibility", ""),
        }


class HHParser(BaseParser):
    source_name = "hh.ru"
    BASE_URL = "https://hh.ru/search/vacancy"

    def fetch(self, query: str) -> list[dict]:
        params = {
            "text": query,
            "schedule": "remote",
            "experience": "noExperience",
            "per_page": 20,
            "page": 0,
        }
        try:
            resp = requests.get(
                self.BASE_URL, params=params,
                headers=BROWSER_HEADERS, timeout=15
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"    [hh.ru] Ошибка: {e}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("div", {"data-qa": "vacancy-serp__vacancy"})

        if not cards:
            os.makedirs("data", exist_ok=True)
            with open("data/debug_hh.html", "w", encoding="utf-8") as f:
                f.write(resp.text[:8000])
            print("    [hh.ru] Карточки не найдены, HTML → data/debug_hh.html")
            return []

        results = []
        for card in cards:
            v = self._parse_card(card)
            if v:
                results.append(v)
        return results

    def _parse_card(self, card) -> dict | None:
        try:
            title_el = card.find("a", {"data-qa": "serp-item__title"})
            if not title_el:
                return None
            raw_url = title_el.get("href", "").split("?")[0]
            import re
            url = re.sub(r'https?://[a-z-]+\.hh\.ru', 'https://hh.ru', raw_url)
            vacancy_id = f"hh_{url.split('/')[-1]}"

            company_el = (
                card.find("a", {"data-qa": "vacancy-serp__vacancy-employer"}) or
                card.find("span", {"data-qa": "vacancy-serp__vacancy-employer"})
            )
            salary_el = card.find("span", {"data-qa": "vacancy-serp__vacancy-compensation"})
            city_el = (
                card.find("span", {"data-qa": "vacancy-serp__vacancy-address"}) or
                card.find("div", {"data-qa": "vacancy-serp__vacancy-address"})
            )
            date_el = card.find("span", {"data-qa": "vacancy-serp__vacancy-date"})
            req_el = card.find("div", {"data-qa": "vacancy-serp__vacancy_snippet_requirement"})
            resp_el = card.find("div", {"data-qa": "vacancy-serp__vacancy_snippet_responsibility"})

            return self._normalize(
                id=vacancy_id,
                title=title_el.get_text(strip=True),
                company=company_el.get_text(strip=True) if company_el else "",
                salary=salary_el.get_text(strip=True) if salary_el else "не указана",
                city=city_el.get_text(strip=True) if city_el else "",
                url=url,
                published=date_el.get_text(strip=True) if date_el else "",
                requirement=req_el.get_text(strip=True) if req_el else "",
                responsibility=resp_el.get_text(strip=True) if resp_el else "",
            )
        except Exception as e:
            print(f"    [hh.ru] Ошибка карточки: {e}")
            return None


class SuperJobParser(BaseParser):
    source_name = "superjob.ru"
    API_URL = "https://api.superjob.ru/2.0/vacancies/"

    def fetch(self, query: str) -> list[dict]:
        if not SUPERJOB_TOKEN:
            print("    [superjob] Токен не задан, пропускаю. Задай SUPERJOB_TOKEN в .env")
            return []

        headers = {
            "X-Api-App-Id": SUPERJOB_TOKEN,
            "User-Agent": "VacBot/1.0",
        }
        params = {
            "keyword": query,
            "count": 20,
            "page": 0,
        }
        try:
            resp = requests.get(self.API_URL, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"    [superjob] Ошибка: {e}")
            return []

        results = []
        for item in data.get("objects", []):
            salary = self._parse_salary(item)
            results.append(self._normalize(
                id=f"sj_{item.get('id', '')}",
                title=item.get("profession", ""),
                company=item.get("firm_name", ""),
                salary=salary,
                city=item.get("town", {}).get("title", ""),
                url=item.get("link", ""),
                published=str(item.get("date_published", "")),
                requirement=item.get("candidat", ""),
                responsibility=item.get("work", ""),
            ))
        return results

    def _parse_salary(self, item: dict) -> str:
        s_from = item.get("payment_from")
        s_to = item.get("payment_to")
        currency = item.get("currency", "rub")
        cur_label = "₽" if currency == "rub" else currency
        if s_from and s_to:
            return f"{s_from}–{s_to} {cur_label}"
        if s_from:
            return f"от {s_from} {cur_label}"
        if s_to:
            return f"до {s_to} {cur_label}"
        return "не указана"


class TrudvsemParser(BaseParser):
    source_name = "trudvsem.ru"
    API_URL = "http://opendata.trudvsem.ru/api/v1/vacancies"

    def fetch(self, query: str) -> list[dict]:
        params = {
            "text": query,
            "limit": 20,
            "offset": 0,
        }
        try:
            resp = requests.get(
                self.API_URL, params=params,
                headers={"User-Agent": "VacBot/1.0"}, timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"    [trudvsem] Ошибка: {e}")
            return []
        except ValueError as e:
            print(f"    [trudvsem] Не удалось разобрать JSON: {e}")
            return []

        results = []
        vacancies = data.get("results", {}).get("vacancies", []) or data.get("vacancies", [])
        for item in vacancies:
            v = item.get("vacancy", {})
            company = v.get("company", {})
            region = v.get("region", {})
            salary_from = v.get("salary_min")
            salary_to = v.get("salary_max")

            if salary_from and salary_to:
                salary = f"{salary_from}–{salary_to} ₽"
            elif salary_from:
                salary = f"от {salary_from} ₽"
            elif salary_to:
                salary = f"до {salary_to} ₽"
            else:
                salary = "не указана"

            results.append(self._normalize(
                id=f"tv_{v.get('id', '')}",
                title=v.get("name", ""),
                company=company.get("name", ""),
                salary=salary,
                city=region.get("name", ""),
                url=f"https://trudvsem.ru/vacancy/card/{company.get('companycode','')}/{v.get('id','')}",
                published=v.get("creation_date", ""),
                requirement=v.get("requirement", {}).get("qualification", ""),
                responsibility=v.get("duty", ""),
            ))
        return results


PARSERS = [
    HHParser(),
    SuperJobParser(),
    TrudvsemParser(),
]


def collect_all(queries: list[str] = None) -> list[dict]:
    if queries is None:
        queries = get_search_queries_from_db()

    all_vacancies: dict[str, dict] = {}
    for query in queries:
        print(f"\n  Запрос: '{query}'")
        for parser in PARSERS:
            items = parser.fetch(query)
            before = len(all_vacancies)
            for v in items:
                if v and v.get("id"):
                    all_vacancies[v["id"]] = v
            added = len(all_vacancies) - before
            print(f"    [{parser.source_name}] +{added} новых")
            time.sleep(0.5)
        time.sleep(1.0)

    result = list(all_vacancies.values())
    print(f"\n  Итого уникальных вакансий: {len(result)}")
    return result


def save_to_json(vacancies: list[dict], path: str = "data/vacancies.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    output = {
        "fetched_at": datetime.now().isoformat(),
        "count": len(vacancies),
        "sources": list({v["source"] for v in vacancies}),
        "vacancies": vacancies,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  Сохранено в {path}")


def save_to_database(vacancies: list[dict]):
    """Сохраняет вакансии напрямую в PostgreSQL, фильтруя по стоп-словам."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app import create_app, db
    from app.models import Vacancy, BoardCard


    stopwords = get_stopwords_from_db()
    if stopwords:
        print(f"📋 Загружено стоп-слов: {len(stopwords)}")

    app = create_app()
    with app.app_context():
        added_count = 0
        updated_count = 0
        filtered_count = 0

        for v in vacancies:
            requirement = v.get('snippet_requirement', '')
            if check_stopwords_in_requirements(requirement, stopwords):
                filtered_count += 1
                continue

            existing = Vacancy.query.filter_by(id=v['id']).first()

            if existing:
                existing.source = v['source']
                existing.title = v['title']
                existing.company = v['company']
                existing.salary = v['salary']
                existing.city = v['city']
                existing.url = v['url']
                existing.published = v['published']
                existing.snippet_requirement = v.get('snippet_requirement', '')
                existing.snippet_responsibility = v.get('snippet_responsibility', '')
                updated_count += 1
            else:
                new_vacancy = Vacancy(
                    id=v['id'],
                    source=v['source'],
                    title=v['title'],
                    company=v['company'],
                    salary=v['salary'],
                    city=v['city'],
                    url=v['url'],
                    published=v['published'],
                    snippet_requirement=v.get('snippet_requirement', ''),
                    snippet_responsibility=v.get('snippet_responsibility', '')
                )
                db.session.add(new_vacancy)

                board_card = BoardCard(
                    vacancy_id=v['id'],
                    status='new',
                    is_postponed=False
                )
                db.session.add(board_card)
                added_count += 1

        db.session.commit()
        print(f"\n💾 База данных:")
        print(f"   ✨ Добавлено: {added_count}")
        print(f"   🔄 Обновлено: {updated_count}")
        print(f"   🚫 Отфильтровано по стоп-словам: {filtered_count}")
        print(f"   📊 Всего в БД: {Vacancy.query.count()}")


    # Отправка уведомлений в Telegram о новых вакансиях
    if added_count > 0:
        try:
            from app.telegram_bot import notify_new_vacancies

            # Сборка добавленных вакансий для уведомления
            added_vacancies = []
            for v in vacancies:
                existing = Vacancy.query.filter_by(id=v['id']).first()
                if existing and existing.created_at and existing.created_at > datetime.utcnow() - timedelta(minutes=1):
                    added_vacancies.append(existing)

            if added_vacancies:

                import asyncio
                import threading


                def run_async_notify():
                    asyncio.run(notify_new_vacancies(added_vacancies))


                notify_thread = threading.Thread(target=run_async_notify, daemon=True)
                notify_thread.start()
        except Exception as e:
            print(f"⚠️ Ошибка отправки уведомлений: {e}")


if __name__ == "__main__":
    print("=== VacBot: мультисорс парсер ===\n")
    vacancies = collect_all()
    save_to_json(vacancies, "data/vacancies.json")
    save_to_database(vacancies)
    print(f"\n✅ Готово! {len(vacancies)} вакансий обработано.")