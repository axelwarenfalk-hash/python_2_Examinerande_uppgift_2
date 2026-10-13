from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True, kw_only=True)
class ReportConfig:
    """Inställningar för datainsamling, cache, sökvägar och rapportperiod."""

    # False hämtar/läser om den delen och uppdaterar dess cache.
    use_council_cache: bool = True
    use_meetings_cache: bool = True
    # Sätt False efter ändringar i PDF-tolkningen i single_meeting.py.
    use_reading_cache: bool = True

    council_cache_path: Path = Path("data/council.json")
    meetings_cache_path: Path = Path("data/meeting_protocol_links.csv")
    reading_cache_dir: Path = Path("data/reading_cache")
    attendance_path: Path = Path("data/attendance.csv")
    pdf_dir: Path = Path("data/pdfs")
    analysis_meetings_path: Path = Path("data/analysis_meetings.csv")
    analysis_summary_path: Path = Path("data/analysis_summary.json")

    term_start: str = "2022-10-15"
    term_end: str = "2026-10-14"

    base_url: str = 'https://motenmedborgarportal.malmo.se/'
    api_url_all_council_representatives: str = 'https://motenmedborgarportal.malmo.se/api/err/v1.0/representatives?committeeId=909&pageSize=9999'
    api_url_all_council_roles: str = 'https://motenmedborgarportal.malmo.se/api/err/v1.0/committees/909/assignments?termOfOfficeId=019511cb-0cc8-4b34-ba97-75ca4fb5ef65'
    url_all_meetings: str = 'https://motenmedborgarportal.malmo.se/committees/kommunfullmaktige#committeesRecentContent'
