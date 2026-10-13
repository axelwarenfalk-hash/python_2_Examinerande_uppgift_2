"""Kör programmets steg: grunddata, möten, PDF:er och närvarotabell."""

import logging

import pandas as pd

from .attendance import build_attendance, make_analysis_summary
from .config import ReportConfig
from .config_logging import config_logging
from .council import load_council, select_members_from_term_start
from .io import download_meeting_pdfs, save_dataframe, save_json
from .meetings import load_meetings, select_term_meetings

logger = logging.getLogger("malmo_council_attendance")


def main() -> pd.DataFrame:
    """Kör datainsamlingen, spara attendance.csv och returnera närvarotabellen.

    Args:
        Inga parametrar.

    Returns:
        pd.DataFrame: Närvarotabellen. Sparar även närvaro, mötesstatus och analysmetadata enligt ReportConfig.
    """
    config_logging()
    members_df, replacements_df = load_council(ReportConfig.council_cache_path, ReportConfig.use_council_cache)
    term_start = pd.Timestamp(ReportConfig.term_start)
    term_end = pd.Timestamp(ReportConfig.term_end)
    as_of = pd.Timestamp.today().normalize()
    members_df, excluded_members = select_members_from_term_start(members_df, term_start)
    meetings_df = load_meetings(ReportConfig.meetings_cache_path, ReportConfig.use_meetings_cache)
    meetings_df = select_term_meetings(meetings_df, term_start, term_end, as_of)
    download_meeting_pdfs(meetings_df, ReportConfig.pdf_dir)
    attendance_df = build_attendance(
        meetings_df, members_df, ReportConfig.pdf_dir, ReportConfig.reading_cache_dir,
        ReportConfig.analysis_meetings_path, ReportConfig.use_reading_cache,
    )
    save_dataframe(attendance_df, ReportConfig.attendance_path)
    summary = make_analysis_summary(meetings_df, attendance_df, excluded_members, term_start, term_end, as_of)
    save_json(summary, ReportConfig.analysis_summary_path)
    logger.info("Sparade närvarotabell med %d rader i %s", len(attendance_df), ReportConfig.attendance_path)
    print(attendance_df)
    return attendance_df


if __name__ == "__main__":
    main()
