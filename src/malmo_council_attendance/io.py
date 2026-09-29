import requests
import logging
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

pdf_dir = Path("data/pdfs")
pdf_dir.mkdir(parents=True, exist_ok=True)


def get_api_json(api_url: str) -> dict | list:
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


def get_page_html(url: str) -> BeautifulSoup:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Hämtning av webbsidan misslyckades: %s", url)
        raise

    logger.info(
        "Webbsidan hämtades: %s (HTTP %s)",
        url,
        response.status_code,
    )
    return BeautifulSoup(response.text, "html.parser")


def download_pdf(row: pd.Series) -> None:
    if pd.isna(row["pdf_url"]):
        return

    filename = f"{row['date'].strftime('%Y-%m-%d')}.pdf"
    path = pdf_dir / filename

    if path.exists():
        return

    response = requests.get(row["pdf_url"], timeout=30)
    response.raise_for_status()
    path.write_bytes(response.content)
    logger.info("PDF nedladdad och sparad: %s", path)
