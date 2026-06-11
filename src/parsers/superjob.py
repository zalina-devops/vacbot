from typing import List, Optional

from src.parsers.base import BaseParser
from src.utils.http_client import (
    session,
    logger
)

from src.config.settings import SUPERJOB_TOKEN

class SuperJobParser(BaseParser):
    source_name = "superjob.ru"
    API_URL = "https://api.superjob.ru/2.0/vacancies/"

    def fetch(self, query: str) -> List[dict]:
        if not SUPERJOB_TOKEN:
            return []

        headers = {"X-Api-App-Id": SUPERJOB_TOKEN, "User-Agent": "VacBot/1.0"}
        try:
            resp = session.get(self.API_URL, params={"keyword": query, "count": 20, "page": 0}, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[superjob] Ошибка: {e}")
            return []

        results = []
        for item in data.get("objects", []):
            salary_from, salary_to = item.get("payment_from"), item.get("payment_to")
            currency = "₽" if item.get("currency") == "rub" else item.get("currency", "")
            salary = self._format_salary(salary_from, salary_to, currency)

            results.append(self.normalize(
                id=f"sj_{item.get('id', '')}",
                title=item.get("profession", ""),
                company=item.get("firm_name", ""),
                salary=salary,
                city=item.get("town", {}).get("title", ""),
                url=item.get("link", ""),
                published=str(item.get("date_published", "")),
                requirement=item.get("candidat", ""),
                responsibility=item.get("work", ""),
                remote_friendly=True
            ))
        return results

    @staticmethod
    def _format_salary(salary_from: Optional[int], salary_to: Optional[int], currency: str) -> str:
        if salary_from and salary_to:
            return f"{salary_from}–{salary_to} {currency}"
        if salary_from:
            return f"от {salary_from} {currency}"
        if salary_to:
            return f"до {salary_to} {currency}"
        return "не указана"