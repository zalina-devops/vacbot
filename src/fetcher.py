# src/fetcher.py — оптимизированная версия

import time
import asyncio
import logging
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.filters import is_vacancy_suitable
from src.parsers.registry import get_parsers
from src.config.settings import SEARCH_QUERIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s"
)

logger = logging.getLogger(__name__)


def collect_all(queries: Optional[List[str]] = None) -> List[dict]:
    """
    Собирает вакансии со всех источников.
    Каждый парсер получает ВСЕ запросы сразу и сам решает, как их обработать.
    """
    start = time.time()
    
    if queries is None:
        queries = SEARCH_QUERIES

    parsers = get_parsers()

    logger.info(
        f"🚀 Запуск парсеров: "
        f"{[p.source_name for p in parsers]}"
    )
    logger.info(f"📋 Запросы ({len(queries)}): {queries}")

    all_vacancies: Dict[str, dict] = {}

    # Запускаем парсеры параллельно, но КАЖДЫЙ парсер сам обрабатывает все свои запросы
    with ThreadPoolExecutor(max_workers=len(parsers)) as executor:
        futures = {
            executor.submit(_run_parser_batch, parser, queries): parser.source_name
            for parser in parsers
        }

        for future in as_completed(futures):
            source_name = futures[future]
            try:
                items = future.result(timeout=300)  # максимум 5 минут на парсер
                before = len(all_vacancies)
                
                for item in items:
                    if item and item.get("id") and is_vacancy_suitable(item):
                        all_vacancies[item["id"]] = item
                
                added = len(all_vacancies) - before
                logger.info(f"  [{source_name}] Добавлено: +{added} (всего получено: {len(items)})")
                
            except Exception as e:
                logger.error(f"[{source_name}] Критическая ошибка: {e}")

    result = list(all_vacancies.values())

    logger.info(
        f"✅ Итого подходящих вакансий: "
        f"{len(result)} "
        f"за {time.time() - start:.1f} сек"
    )

    return result


def _run_parser_batch(parser, queries: List[str]) -> List[dict]:
    """
    Запускает парсер со всеми запросами.
    Если парсер поддерживает batch-режим (fetch_all) — использует его.
    Иначе — последовательно вызывает fetch для каждого запроса.
    """
    # Проверяем, есть ли у парсера метод fetch_all (batch-режим)
    if hasattr(parser, 'fetch_all') and callable(getattr(parser, 'fetch_all')):
        try:
            return parser.fetch_all(queries)
        except Exception as e:
            logger.warning(f"[{parser.source_name}] fetch_all не сработал: {e}, fallback на fetch")
    
    # Fallback: последовательный вызов fetch для каждого запроса
    all_items = []
    for query in queries:
        try:
            items = parser.fetch(query)
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[{parser.source_name}] Ошибка запроса '{query}': {e}")
    
    return all_items