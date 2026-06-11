# src/utils/http_client.py

import requests
import logging

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

def create_session() -> requests.Session:
    """
    Создаёт HTTP-сессию
    с автоматическими повторами запросов
    """

    session = requests.Session()

    retry_strategy = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504
        ]
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy
    )

    session.mount(
        "http://",
        adapter
    )

    session.mount(
        "https://",
        adapter
    )

    return session


session = create_session()