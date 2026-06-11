# src/filters/vacancy_filters.py

import time
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

_cached_filters: Optional[Tuple[List[str], List[str]]] = None
_cached_filters_time: Optional[float] = None

HARD_BLACKLIST = [
    "call center",
    "колл центр",
    "колл-центр",
    "оператор call",
    "оператор контактного центра",
    "контактный центр",
    "оператор контакт-центра",
    "телемаркетолог",
    "менеджер по продажам",
    "продажи",
    "активные продажи",
    "холодные звонки",
    "исходящие звонки",
    "оператор на телефоне",
    "оператор поддержки клиентов",
    "консультант по продажам",

    "офис",
    "работа в офисе",
    "на территории работодателя",
    "полная занятость в офисе",

    "высшее образование",
    "оконченное высшее образование",
    "бакалавр",
    "магистр",

    "опыт работы от",
    "опыт более",
    "опыт коммерческой разработки",

    # руководство
    "руководитель",
    "teamlead",
    "team lead",
    "tech lead",
    "lead",
    "директор",
    "начальник",

    # опытные позиции
    "senior",
    "middle",
    "middle+",
    "ведущий",
    "архитектор",

    "devops",
    "sre",
    "системный администратор",
    "администратор баз данных",
    "dba",

    # продажи
    "продаж",
    "sales",

    # hr
    "hr",
    "рекрутер",
    "подбор персонала",

    # маркетинг
    "маркетолог",
    "seo",
    "smm",
    "таргетолог",

    # юриспруденция
    "юрист",
    "legal",

    # бухгалтерия
    "бухгалтер",

    # ассистенты
    "ассистент",
    "помощник",

    # аналитика не по данным
    "бизнес-аналитик",
    "бизнес аналитик",
    "системный аналитик",
    "system analyst",
    "аналитик 1с",
    "1с аналитик",
    "финансовый аналитик",
    "product analyst",
    "product manager",
    "продуктовый аналитик",
    "продуктолог",
    "scrum мастер",

    # менеджеры
    "manager",
    "менеджер",
    "account manager",
    "project manager",

    # маркетинг
    "pr",
    "маркетинг",

    # обработка документов
    "обработка заявок",
    "персональных данных",
    "внесение данных",
    "оператор базы данных",
    "делопроизводитель",

    # кадровое
    "hr",
    "кадры",
    "персонал",
    # мобильная разработка
    "ios",
    "android",
    "swift",
    "kotlin",

    # 1с
    "1с",

    # data engineering
    "data engineer",
    "дата инженер",

    # big data
    "hadoop",
    "spark",
    "bigdata",
    "big data",

    # биоинформатика
    "биоинформатик",
    "bioinformatics",
]

def get_active_filters() -> Tuple[List[str], List[str]]:
    """
    Получает фильтры из БД с кэшированием на 30 секунд
    """

    global _cached_filters
    global _cached_filters_time

    now = time.time()

    if (
        _cached_filters is not None
        and _cached_filters_time
        and (now - _cached_filters_time) < 30
    ):
        return _cached_filters

    try:
        from app import create_app
        from app.models import SearchQuery, StopWord

        app = create_app()

        with app.app_context():

            whitelist = [
                q.text.lower()
                for q in SearchQuery.query.filter_by(
                    is_active=True
                ).all()
            ]

            blacklist = [
                sw.word.lower()
                for sw in StopWord.query.all()
            ]

            _cached_filters = (
                whitelist,
                blacklist
            )

            _cached_filters_time = now

            return whitelist, blacklist

    except Exception as e:

        logger.warning(
            f"Ошибка получения фильтров: {e}"
        )

        return [], []


def is_vacancy_suitable(vacancy: dict) -> bool:

    whitelist, blacklist = get_active_filters()

    title = vacancy.get(
        "title",
        ""
    ).lower()

    requirement = vacancy.get(
        "requirement",
        ""
    ).lower()

    text = (
            title + " " +
            requirement
    ).lower()

    for word in HARD_BLACKLIST:
        if word in text:
            return False

    for word in blacklist:

        if (
            word
            and (
                word in title
                or word in requirement
            )
        ):
            return False

    if whitelist:

        for word in whitelist:

            if (
                word
                and (
                    word in title
                    or word in requirement
                )
            ):
                return True

        return False

    return True
