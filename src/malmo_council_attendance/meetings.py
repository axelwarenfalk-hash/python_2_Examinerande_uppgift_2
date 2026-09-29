from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

def find_meeting_urls(html: BeautifulSoup, base_url: str) -> pd.DataFrame:

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

    pdf_url_a_tag = html.find_all('a', id = 'openProtocol')
    pdf_url = pdf_url_a_tag[0].get("href")

    if not isinstance(pdf_url, str):
        return None
    
    if pdf_url.startswith('javascript:'):
        return None

    return pdf_url
