import re
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


class BaseParser(ABC):
    """Для API-парсеров (SuperJob, Trudvsem)"""
    source_name: str = ""

    @abstractmethod
    def fetch(self, query: str) -> List[dict]:
        pass

    def normalize(self, **kwargs) -> dict:
        return {
            "id": str(kwargs.get("id", "")),
            "source": self.source_name,
            "title": clean_text(kwargs.get("title", "")),
            "company": clean_text(kwargs.get("company", "")),
            "salary": clean_text(kwargs.get("salary", "не указана")),
            "city": clean_text(kwargs.get("city", "")),
            "url": kwargs.get("url", ""),
            "published": clean_text(kwargs.get("published", "")),
            "requirement": clean_text(kwargs.get("requirement", "")),
            "responsibility": clean_text(kwargs.get("responsibility", "")),
            "remote_friendly": bool(kwargs.get("remote_friendly", False))
        }


# ==================== PLAYWRIGHT ====================
async def get_browser():
    """Простой браузер без сложного stealth"""
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
        ]
    )
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    )
    return p, browser, context


class BasePlaywrightParser(ABC):
    """Для HH и Habr"""
    source_name: str = ""
    NAV_TIMEOUT = 90000
    PAGE_TIMEOUT = 60000

    async def _get_page(self, context):
        page = await context.new_page()
        page.set_default_timeout(self.PAGE_TIMEOUT)
        page.set_default_navigation_timeout(self.NAV_TIMEOUT)
        return page