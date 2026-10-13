"""Hämta webbinnehåll och läs eller spara lokala datafiler."""

import json
from typing import Any

import requests
import logging
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

pdf_dir = Path("data/pdfs")


def get_api_json(api_url: str) -> dict[str, Any] | list[Any]:
    """Hämta API-data som Python-objekt; nätverksfel loggas och skickas vidare.

    Args:
        api_url (str): Fullständig adress till API-endpointen.

    Returns:
        dict[str, Any] | list[Any]: API-svarets avkodade JSON-data.

    Raises:
        requests.RequestException: Om HTTP-anropet misslyckas.
        ValueError: Om svaret inte innehåller giltig JSON.
    """
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
    """Hämta och tolka en HTML-sida med 30 sekunders timeout.

    Args:
        url (str): Fullständig adress till webbsidan.

    Returns:
        BeautifulSoup: Sidans HTML, färdig att söka i.

    Raises:
        requests.RequestException: Om HTTP-anropet misslyckas.
    """
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


def download_pdf(row: pd.Series, output_dir: Path = pdf_dir) -> None:
    """Spara mötets PDF under dess datum om länk finns och filen saknas.

    Args:
        row (pd.Series): Mötesrad med date och pdf_url.
        output_dir (Path): Mapp där de skapade filerna sparas.

    Returns:
        None: Sparar PDF-filen om länken finns och filen inte redan finns lokalt.

    Raises:
        requests.RequestException: Om hämtningen av PDF-filen misslyckas.
    """
    if pd.isna(row["pdf_url"]):
        return

    filename = f"{row['date'].strftime('%Y-%m-%d')}.pdf"
    path = output_dir / filename

    if path.exists():
        return

    response = requests.get(row["pdf_url"], timeout=30)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    logger.info("PDF nedladdad och sparad: %s", path)


def download_meeting_pdfs(meetings_df: pd.DataFrame, output_dir: Path) -> None:
    """Ladda ner de mötesprotokoll som ännu inte finns i mappen.

    Args:
        meetings_df (pd.DataFrame): Mötestabell med datum och länkar till möten och protokoll.
        output_dir (Path): Mapp där de skapade filerna sparas.

    Returns:
        None: Sparar de protokoll som har länkar och saknas lokalt.
    """
    for _, meeting in meetings_df.iterrows():
        download_pdf(meeting, output_dir)


def read_json(path: Path) -> dict[str, Any]:
    """Läs en cachefil vars översta nivå är en ordbok.

    Args:
        path (Path): Sökväg till filen som läses eller skrivs.

    Returns:
        dict[str, Any]: JSON-filens innehåll som en ordbok.

    Raises:
        TypeError: Om JSON-filens översta nivå inte är en ordbok.
        json.JSONDecodeError: Om filen inte innehåller giltig JSON.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"Förväntade en ordbok i {path}")
    return data


def save_json(data: dict[str, Any], path: Path) -> None:
    """Spara en ordbok som läsbar JSON med svenska tecken.

    Args:
        data (dict[str, Any]): Ordbok som ska sparas som JSON.
        path (Path): Sökväg till filen som läses eller skrivs.

    Returns:
        None: Skriver JSON-filen och skapar eventuella saknade mappar.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_dataframe(path: Path) -> pd.DataFrame:
    """Läs en mötes- eller närvarotabell från CSV och tolka kolumnen date.

    Args:
        path (Path): Sökväg till filen som läses eller skrivs.

    Returns:
        pd.DataFrame: CSV-innehållet med date omvandlad till datumvärden.
    """
    return pd.read_csv(path, parse_dates=["date"])


def save_dataframe(dataframe: pd.DataFrame, path: Path) -> None:
    """Spara en tabell som CSV utan index; skapa mappen om den saknas.

    Args:
        dataframe (pd.DataFrame): Tabell som ska sparas som CSV.
        path (Path): Sökväg till filen som läses eller skrivs.

    Returns:
        None: Skriver CSV-filen utan index och skapar eventuella saknade mappar.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)
