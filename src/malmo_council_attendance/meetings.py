from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import requests
from .io import (
    get_page_html
)




def find_meeting_links(html, base_url):

    links = html.find_all("a", class_="accessible-table-cell")

    meetings = {}

    for link in links:
        href = link.get("href")
        aria_label = link.get("aria-label")
        
        if href is not None and aria_label is not None:
            meetings[aria_label] = urljoin(base_url, href)

    meetings_df = pd.DataFrame(list(meetings.items()), columns=["date", "url"])
    
    meetings_df["date"] = pd.to_datetime(
    meetings_df["date"].str.extract(r"(\d{4}-\d{2}-\d{2})")[0])

    meetings_df = meetings_df[meetings_df["date"].dt.date <= pd.Timestamp.today().date()].copy()

    return meetings_df


def get_pdf_link(html):

    protocol_pdf = html.find_all(
    'a',
    id = 'openProtocol'
    )

    protocol_href = protocol_pdf[0].get("href")

    return protocol_href


def find_pdf_links(url):
    html = get_page_html(url)
    link = get_pdf_link(html)
    print(link)
    return link