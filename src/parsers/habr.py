import asyncio
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import quote

from src.parsers.base import BasePlaywrightParser, get_browser

logger = logging.getLogger(__name__)


class HabrPlaywrightParser(BasePlaywrightParser):
    source_name = "habr.com"

    def fetch(self, query: str, max_results: int = 25) -> List[Dict]:
        try:
            return asyncio.run(self._fetch_all([query], max_results))
        except Exception as e:
            logger.error(f"[habr] Критическая ошибка: {e}")
            return []

    async def _fetch_all(self, queries: List[str], max_results: int = 25) -> List[Dict]:
        all_vacancies = []
        p, browser, context = None, None, None
        
        try:
            p, browser, context = await get_browser()
            page = await self._get_page(context)

            for query in queries:
                for attempt in range(2):  # меньше попыток
                    try:
                        vacancies = await self._fetch_single(page, query, max_results)
                        all_vacancies.extend(vacancies)
                        await asyncio.sleep(4)
                        break
                    except Exception as e:
                        logger.warning(f"[habr] Попытка {attempt+1} '{query}' ошибка: {e}")
                        await asyncio.sleep(5)
        finally:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if p:
                await p.stop()

        # уникализация
        seen = set()
        unique = [v for v in all_vacancies if v["id"] not in seen and not seen.add(v["id"])]
        
        logger.info(f"[habr.com] Всего уникальных: {len(unique)}")
        return unique

    async def _fetch_single(self, page, query: str, max_results: int) -> List[Dict]:
        vacancies = []
        url = f"https://career.habr.com/vacancies?q={quote(query)}&type=all"
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            try:
                await page.wait_for_selector(".vacancy-card", timeout=12000)
            except:
                logger.info(f"[habr] Нет вакансий по '{query}'")
                return []

            await page.wait_for_timeout(800)
            
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.find_all("div", class_="vacancy-card")
            
            for card in cards[:max_results]:
                vacancy = self._parse_card(card)
                if vacancy:
                    vacancies.append(vacancy)
        except Exception as e:
            logger.error(f"[habr] Ошибка {query}: {e}")
        
        logger.info(f"[habr.com] '{query}' — {len(vacancies)} вакансий")
        return vacancies

    def _parse_card(self, card) -> Dict:
        # (тот же код, что был раньше)
        title_el = card.find("a", class_="vacancy-card__title-link")
        if not title_el:
            return None
            
        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        vacancy_id = href.split("/")[-1] if href else ""
        url_full = f"https://career.habr.com{href}" if href else ""
        
        company = card.select_one(".vacancy-card__company a")
        company = company.get_text(strip=True) if company else ""
        
        salary = "не указана"
        salary_wrapper = card.find("div", class_="vacancy-card__salary")
        if salary_wrapper:
            basic = salary_wrapper.find("div", class_="basic-salary")
            if basic:
                salary = basic.get_text(" ", strip=True)
        
        city = card.find("div", class_="vacancy-card__meta")
        city = city.get_text(strip=True) if city else ""
        
        requirement = card.find("div", class_="vacancy-card__skills")
        requirement = requirement.get_text(strip=True) if requirement else ""
        
        return {
            "id": f"habr_{vacancy_id}" if vacancy_id else f"habr_{hash(title)}",
            "source": self.source_name,
            "title": title,
            "company": company,
            "salary": salary,
            "city": city,
            "url": url_full,
            "requirement": requirement,
            "responsibility": "",
            "remote_friendly": any(k in city.lower() for k in ["удален", "remote", "удалённо"])
        }
