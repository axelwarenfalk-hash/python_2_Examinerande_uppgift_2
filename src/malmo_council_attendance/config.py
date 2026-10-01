from dataclasses import dataclass

@dataclass(frozen=True, kw_only=True)
class ReportConfig:
    """Adresser till Malmö stads mötessidor och API:er."""

    term_start: str = "2022-10-15"
    term_end: str = "2026-10-14"

    base_url: str = 'https://motenmedborgarportal.malmo.se/'
    api_url_all_council_representatives: str = 'https://motenmedborgarportal.malmo.se/api/err/v1.0/representatives?committeeId=909&pageSize=9999'
    api_url_all_council_roles: str = 'https://motenmedborgarportal.malmo.se/api/err/v1.0/committees/909/assignments?termOfOfficeId=019511cb-0cc8-4b34-ba97-75ca4fb5ef65'
    url_all_meetings: str = 'https://motenmedborgarportal.malmo.se/committees/kommunfullmaktige#committeesRecentContent'
