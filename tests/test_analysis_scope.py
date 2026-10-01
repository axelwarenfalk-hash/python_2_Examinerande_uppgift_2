import pandas as pd

from malmo_council_attendance.council import select_members_from_term_start
from malmo_council_attendance.meetings import select_term_meetings
from malmo_council_attendance.attendance import make_analysis_summary
from malmo_council_attendance.viz import make_plot_footer


def test_member_selection_includes_start_but_excludes_later_and_unknown_dates():
    members = pd.DataFrame({
        "name": ["Before", "On start", "Later", "Unknown", "Ended"],
        "date_from": ["2022-10-01", "2022-10-15", "2022-10-16", None, "2020-01-01"],
        "date_to": [None, "2026-10-14", None, None, "2022-10-14"],
    })
    included, excluded = select_members_from_term_start(members, pd.Timestamp("2022-10-15"))
    assert included.name.tolist() == ["Before", "On start"]
    assert excluded.name.tolist() == ["Later", "Unknown", "Ended"]


def test_meetings_exclude_old_future_and_next_term():
    meetings = pd.DataFrame({"date": pd.to_datetime([
        "2022-10-14", "2022-10-15", "2026-10-01", "2026-10-02", "2026-10-15",
    ])})
    selected = select_term_meetings(meetings, pd.Timestamp("2022-10-15"),
                                    pd.Timestamp("2026-10-14"), pd.Timestamp("2026-10-01"))
    assert selected.date.dt.strftime("%Y-%m-%d").tolist() == ["2022-10-15", "2026-10-01"]


def test_summary_and_footer_report_exclusions_and_all_missing_meetings():
    meetings = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"]),
        "pdf_url": ["url", None, "url", "url"],
        "read_status": ["processed", "missing_pdf", "unreadable_text", "missing_paragraphs"],
    })
    attendance = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"] * 2)})
    excluded = pd.DataFrame({"name": ["Hanna Sandberg"], "political_party": ["Arbetarepartiet Socialdemokraterna"],
                             "date_from": pd.to_datetime(["2026-09-07"])})
    summary = make_analysis_summary(meetings, attendance, excluded, pd.Timestamp("2022-10-15"),
                                    pd.Timestamp("2026-10-14"), pd.Timestamp("2026-10-01"))
    assert summary["analyzed_meetings"] == 1
    assert summary["total_meetings"] == 4
    assert len(summary["skipped_meetings"]) == 3
    footer = " ".join(make_plot_footer(summary).split())
    assert "1 av 4" in footer
    assert "Hanna Sandberg (S)" in footer
    assert "ingen pdf-länk" in footer
    assert "maskinläsbar text" in footer
    assert "paragrafer kunde inte identifieras" in footer
