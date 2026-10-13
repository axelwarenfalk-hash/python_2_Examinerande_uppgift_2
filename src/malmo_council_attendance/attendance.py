"""Bygg närvarotabeller från mötenas tolkade personposter."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from .io import save_dataframe
from .single_meeting import load_meeting_reading

logger = logging.getLogger(__name__)

ATTENDANCE_COLUMNS = [
    "date", "paragraph", "representative_id", "member", "party", "status", "replaced_by",
]


def make_analysis_summary(
    meetings_df: pd.DataFrame, attendance_df: pd.DataFrame, excluded_members: pd.DataFrame,
    term_start: pd.Timestamp, term_end: pd.Timestamp, as_of: pd.Timestamp,
) -> dict[str, Any]:
    """Beskriv analysens urval och varje utelämnat möte för figurernas fotnoter.

    Args:
        meetings_df (pd.DataFrame): Mötestabell med datum och länkar till möten och protokoll.
        attendance_df (pd.DataFrame): Närvarotabell med en rad per ledamot och paragraf.
        excluded_members (pd.DataFrame): Tabell över ledamöter som inte ingår i analysens urval.
        term_start (pd.Timestamp): Mandatperiodens första datum, inklusive.
        term_end (pd.Timestamp): Mandatperiodens sista datum, inklusive.
        as_of (pd.Timestamp): Senaste datum som får ingå i analysen.

    Returns:
        dict[str, Any]: Period, mötesantal, bortvalda ledamöter och orsaker till utelämnade möten.
    """
    analyzed_dates = set(pd.to_datetime(attendance_df["date"]).dt.strftime("%Y-%m-%d"))
    skipped = []
    for meeting in meetings_df.itertuples():
        date = meeting.date.strftime("%Y-%m-%d")
        if date in analyzed_dates:
            continue
        status = meeting.read_status
        if status == "missing_pdf":
            reason = "Ingen PDF-länk i möteslistan" if pd.isna(meeting.pdf_url) else "PDF-filen saknas lokalt"
        else:
            reason = {
                "unreadable_text": "Närvarodelen saknar maskinläsbar text",
                "missing_paragraphs": "Mötets paragrafer kunde inte identifieras",
                "not_processed": "Mötet har inte behandlats",
                "processed": "Inga närvarorader i urvalet",
            }.get(status, f"Okänd lässtatus: {status}")
        skipped.append({"date": date, "reason": reason})
    excluded = []
    for member in excluded_members.sort_values("name").itertuples():
        start = member.date_from
        excluded.append({
            "name": member.name,
            "party": member.political_party,
            "date_from": None if pd.isna(start) else pd.Timestamp(start).strftime("%Y-%m-%d"),
        })
    return {
        "term_start": term_start.strftime("%Y-%m-%d"),
        "term_end": term_end.strftime("%Y-%m-%d"),
        "as_of": min(as_of, term_end).strftime("%Y-%m-%d"),
        "total_meetings": int(meetings_df["date"].nunique()),
        "analyzed_meetings": len(analyzed_dates),
        "excluded_members": excluded,
        "skipped_meetings": skipped,
    }


def make_meeting_attendance(
    meeting_date: pd.Timestamp, members_df: pd.DataFrame, reading: dict[str, Any]
) -> list[dict[str, Any]]:
    """Skapa en rad per ledamot och paragraf; egen närvaro prioriteras över ersättning.

    Args:
        meeting_date (pd.Timestamp): Datum för det aktuella mötet.
        members_df (pd.DataFrame): Ledamotstabell med person-id, namn, parti och uppdragsdatum.
        reading (dict[str, Any]): Tolkad mötesdata med paragrafer, ledamöter och ersättningar.

    Returns:
        list[dict[str, Any]]: Närvarorader med datum, paragraf, person-id, namn, parti, status och eventuell ersättare.
    """
    attendance_rows = []
    meeting_paragraphs = reading["paragraphs"]
    members_attendance = reading["members"]
    replacements_attendance = reading["replacements"]
    for paragraph in meeting_paragraphs:
        for _, member in members_df.iterrows():
            status = "absent_without_replacement"
            replaced_by = None

            for attending_member in members_attendance:
                if attending_member["name"] == member["name"]:
                    if paragraph in attending_member["paragraphs"]:
                        status = "present"
                        break

            if status != "present":
                for replacement in replacements_attendance:
                    for replaced_member in replacement["replaces"]:
                        if replaced_member["member"]["name"] == member["name"]:
                            if paragraph in replaced_member["paragraphs"]:
                                status = "absent_with_replacement"
                                replaced_by = replacement["name"]
                                break
                    if replaced_by is not None:
                        break

            attendance_rows.append({
                "date": meeting_date,
                "paragraph": paragraph,
                "representative_id": member["representative_id"],
                "member": member["name"],
                "party": member["political_party"],
                "status": status,
                "replaced_by": replaced_by,
            })

    return attendance_rows


def build_attendance(
    meetings_df: pd.DataFrame,
    members_df: pd.DataFrame,
    pdf_dir: Path,
    reading_cache_dir: Path,
    meetings_cache_path: Path,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Läs möten, uppdatera deras lässtatus och sammanfoga alla närvarorader. Ändrar meetings_df genom att sätta read_status och sparar status efter varje möte.

    Args:
        meetings_df (pd.DataFrame): Mötestabell med datum och länkar till möten och protokoll.
        members_df (pd.DataFrame): Ledamotstabell med person-id, namn, parti och uppdragsdatum.
        pdf_dir (Path): Mapp med protokoll namngivna som ÅÅÅÅ-MM-DD.pdf.
        reading_cache_dir (Path): Mapp för cachade PDF-tolkningar i JSON-format.
        meetings_cache_path (Path): CSV-fil där mötestabellen och dess lässtatus sparas.
        use_cache (bool): Om True används befintlig giltig cache; annars hämtas eller läses data om.

    Returns:
        pd.DataFrame: Alla närvarorader med kolumnerna i ATTENDANCE_COLUMNS; kan vara tom.
    """
    attendance_rows = []
    meetings_df["read_status"] = "not_processed"
    save_dataframe(meetings_df, meetings_cache_path)
    for index, meeting in meetings_df.iterrows():
        pdf_path = pdf_dir / (meeting["date"].strftime("%Y-%m-%d") + ".pdf")
        reading = load_meeting_reading(pdf_path, reading_cache_dir, use_cache)
        if reading["status"] == "processed":
            attendance_rows.extend(make_meeting_attendance(meeting["date"], members_df, reading))
        meetings_df.at[index, "read_status"] = reading["status"]
        save_dataframe(meetings_df, meetings_cache_path)
    return pd.DataFrame(attendance_rows, columns=ATTENDANCE_COLUMNS)
