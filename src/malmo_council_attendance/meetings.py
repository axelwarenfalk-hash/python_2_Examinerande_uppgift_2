"""Hämta möteslistan och hitta länkar till protokoll."""

from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import logging

from .config import ReportConfig
from .io import get_page_html, read_dataframe, save_dataframe

logger = logging.getLogger(__name__)


def select_term_meetings(
    meetings_df: pd.DataFrame, term_start: pd.Timestamp, term_end: pd.Timestamp,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    """Välj kända möten inom mandatperioden till och med angivet datum.

    Args:
        meetings_df (pd.DataFrame): Mötestabell med datum och länkar till möten och protokoll.
        term_start (pd.Timestamp): Mandatperiodens första datum, inklusive.
        term_end (pd.Timestamp): Mandatperiodens sista datum, inklusive.
        as_of (pd.Timestamp): Senaste datum som får ingå i analysen.

    Returns:
        pd.DataFrame: Kopia av möten från term_start till det tidigaste av term_end och as_of.
    """
    dates = pd.to_datetime(meetings_df["date"])
    return meetings_df.loc[dates.between(term_start, min(term_end, as_of))].copy()

def find_meeting_urls(html: BeautifulSoup, base_url: str) -> pd.DataFrame:
    """Extrahera datum och absoluta möteslänkar för möten till och med idag.

    Args:
        html (BeautifulSoup): Tolkad HTML för möteslistan.
        base_url (str): Basadress för att omvandla relativa möteslänkar till absoluta.

    Returns:
        pd.DataFrame: Kolumnerna date och url för möten till och med dagens datum.
    """

    links = html.find_all("a", class_="accessible-table-cell")

    meetings = {}

    for link in links:
        href = link.get("href")
        aria_label = link.get("aria-label")

        if isinstance(href, str) and isinstance(aria_label, str):
            meetings[aria_label] = urljoin(base_url, href)

    meetings_df = pd.DataFrame(list(meetings.items()), columns=["date", "url"])

    meetings_df["date"] = pd.to_datetime(
    meetings_df["date"].str.extract(r"(\d{4}-\d{2}-\d{2})")[0])

    meetings_df = meetings_df[meetings_df["date"].dt.date <= pd.Timestamp.today().date()].copy()

    return meetings_df


def find_pdf_url(html: BeautifulSoup) -> str | None:
    """Läs protokollets länk från elementet med id openProtocol.

    Args:
        html (BeautifulSoup): Tolkad HTML för ett enskilt möte.

    Returns:
        str | None: Protokollets href, eller None om href saknas eller är en JavaScript-länk.

    Raises:
        IndexError: Om HTML-sidan saknar länken med id openProtocol.
    """

    pdf_url_a_tag = html.find_all('a', id = 'openProtocol')
    pdf_url = pdf_url_a_tag[0].get("href")

    if not isinstance(pdf_url, str):
        return None

    if pdf_url.startswith('javascript:'):
        return None

    return pdf_url


def load_meetings(cache_path: Path, use_cache: bool = True) -> pd.DataFrame:
    """Läs sparade möteslänkar eller hämta möten och protokollänkar på nytt.

    Args:
        cache_path (Path): Sökväg till funktionens cachefil.
        use_cache (bool): Om True används befintlig giltig cache; annars hämtas eller läses data om.

    Returns:
        pd.DataFrame: Mötestabell med date, url och pdf_url. Nyhämtade länkar sparas i cachefilen.
    """
    if use_cache and cache_path.exists():
        logger.info("Läser möteslänkar från cache")
        return read_dataframe(cache_path)
    html = get_page_html(ReportConfig.url_all_meetings)
    meetings_df = find_meeting_urls(html, ReportConfig.base_url)
    pdf_urls = []
    for url in meetings_df["url"]:
        pdf_urls.append(find_pdf_url(get_page_html(url)))
    meetings_df["pdf_url"] = pdf_urls
    save_dataframe(meetings_df, cache_path)
    return meetings_df
