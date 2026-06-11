from typing import List, Optional

from src.parsers.base import BaseParser
from src.utils.http_client import (
    session,
    logger
)

class TrudvsemParser(BaseParser):
    source_name = "trudvsem.ru"
    API_URL = "http://opendata.trudvsem.ru/api/v1/vacancies"

    def fetch(self, query: str) -> List[dict]:
        try:
            resp = session.get(self.API_URL, params={"text": query, "limit": 20, "offset": 0}, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[trudvsem] Ошибка: {e}")
            return []

        vacancies_data = data.get("results", {}).get("vacancies", []) or data.get("vacancies", [])
        results = []

        for item in vacancies_data:
            vacancy = item.get("vacancy", {})
            company = vacancy.get("company", {})
            region = vacancy.get("region", {})

            salary_min, salary_max = vacancy.get("salary_min"), vacancy.get("salary_max")
            salary = self._format_salary(salary_min, salary_max)

            company_code = company.get("companycode", "")
            vacancy_id = vacancy.get("id", "")

            results.append(self.normalize(
                id=f"tv_{vacancy_id}",
                title=vacancy.get("name", ""),
                company=company.get("name", ""),
                salary=salary,
                city=region.get("name", ""),
                url=f"https://trudvsem.ru/vacancy/card/{company_code}/{vacancy_id}" if company_code and vacancy_id else "",
                published=vacancy.get("creation_date", ""),
                requirement=vacancy.get("requirement", {}).get("qualification", ""),
                responsibility=vacancy.get("duty", ""),
                remote_friendly=False
            ))
        return results

    @staticmethod
    def _format_salary(salary_min: Optional[int], salary_max: Optional[int]) -> str:
        if salary_min and salary_max:
            return f"{salary_min}–{salary_max} ₽"
        if salary_min:
            return f"от {salary_min} ₽"
        if salary_max:
            return f"до {salary_max} ₽"
        return "не указана"