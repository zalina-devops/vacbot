import asyncio
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import quote

from src.parsers.base import BasePlaywrightParser, get_browser

logger = logging.getLogger(__name__)


class HHPlaywrightParser(BasePlaywrightParser):
    """Парсер hh.ru"""
    
    source_name = "hh.ru"

    def fetch(self, query: str, max_results: int = 25) -> List[Dict]:
        """Главный синхронный метод"""
        try:
            return asyncio.run(self._fetch_all([query], max_results))
        except Exception as e:
            logger.error(f"[hh.ru] Критическая ошибка в fetch: {e}")
            return []

    async def _fetch_all(self, queries: List[str], max_results: int = 25) -> List[Dict]:
        all_vacancies = []
        
        try:
            p, browser, context = await get_browser()
            page = await self._get_page(context)

            for query in queries:
                for attempt in range(3):
                    try:
                        vacancies = await self._fetch_single(page, query, max_results)
                        all_vacancies.extend(vacancies)
                        await asyncio.sleep(3)
                        break
                    except Exception as e:
                        logger.warning(f"[hh.ru] Попытка {attempt+1}/3 '{query}' не удалась: {e}")
                        if attempt < 2:
                            await asyncio.sleep(7 * (attempt + 1))
        finally:
            if 'page' in locals():
                await page.close()
            if 'browser' in locals():
                await browser.close()
            if 'p' in locals():
                await p.stop()

        # Уникализация
        seen = set()
        unique = []
        for v in all_vacancies:
            if v["id"] not in seen:
                seen.add(v["id"])
                unique.append(v)
        
        logger.info(f"[hh.ru] Всего уникальных: {len(unique)}")
        return unique

    async def _fetch_single(self, page, query: str, max_results: int) -> List[Dict]:
        vacancies = []
        url = f"https://hh.ru/search/vacancy?text={quote(query)}&from=suggest_post"
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(2000)
            
            try:
                await page.wait_for_selector('[data-qa="vacancy-serp__vacancy"]', timeout=20000)
            except asyncio.TimeoutError:
                logger.info(f"[hh.ru] Нет вакансий по запросу '{query}'")
                return []
            
            await page.wait_for_timeout(1500)
            
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select('[data-qa="vacancy-serp__vacancy"]')
            
            for card in cards[:max_results]:
                vacancy = self._parse_card(card)
                if vacancy:
                    vacancies.append(vacancy)
                    
        except Exception as e:
            logger.error(f"[hh.ru] Ошибка '{query}': {e}")
        
        logger.info(f"[hh.ru] '{query}' — {len(vacancies)} вакансий")
        return vacancies

    def _parse_card(self, card) -> Dict:
        title_el = card.select_one('[data-qa="serp-item__title"]')
        if not title_el:
            return None
            
        title = title_el.get_text(" ", strip=True)
        url_full = title_el.get("href", "")
        vacancy_id = url_full.split("/")[-1].split("?")[0] if url_full else ""
        
        company_el = card.select_one('[data-qa="vacancy-serp__vacancy-employer"]')
        company = company_el.get_text(" ", strip=True) if company_el else ""
        
        salary_el = card.select_one('[data-qa="vacancy-serp__vacancy-compensation"]')
        salary = salary_el.get_text(" ", strip=True) if salary_el else "не указана"
        
        city_el = card.select_one('[data-qa="vacancy-serp__vacancy-address"]')
        city = city_el.get_text(" ", strip=True) if city_el else ""
        
        return {
            "id": f"hh_{vacancy_id}" if vacancy_id else f"hh_{hash(title)}",
            "source": self.source_name,
            "title": title,
            "company": company,
            "salary": salary,
            "city": city,
            "url": url_full,
            "requirement": "",
            "responsibility": "",
            "remote_friendly": any(x in city.lower() for x in ["удален", "remote", "удалённо"])
        }
