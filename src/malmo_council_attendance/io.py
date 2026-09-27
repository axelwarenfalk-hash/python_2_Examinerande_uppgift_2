import requests
import logging
from typing import Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def get_api_json(api_url: str) -> Any:
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        logger.exception("API-anrop misslyckades: %s", api_url)
        raise

    logger.info(
        "API-anrop lyckades: %s (HTTP %s)",
        api_url,
        response.status_code,
    )
    return data


def get_page_html(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup