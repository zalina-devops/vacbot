from src.parsers.superjob import SuperJobParser
from src.parsers.trudvsem import TrudvsemParser
from src.parsers.habr import HabrPlaywrightParser
from src.parsers.hh import HHPlaywrightParser


def get_parsers():
    """Возвращает список всех активных парсеров"""
    return [
        SuperJobParser(),
        TrudvsemParser(),
        HabrPlaywrightParser(),
        HHPlaywrightParser(),
    ]