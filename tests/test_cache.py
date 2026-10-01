from unittest.mock import Mock

import pandas as pd
import pytest

from malmo_council_attendance import __main__ as app
from malmo_council_attendance import council, meetings, single_meeting
from malmo_council_attendance.config import ReportConfig


@pytest.fixture
def cached_app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for flag in ("use_council_cache", "use_meetings_cache", "use_reading_cache"):
        monkeypatch.setattr(app, flag, True)
    pdf_dir = tmp_path / "data/pdfs"
    pdf_dir.mkdir(parents=True)
    pdf_path = pdf_dir / "2024-01-01.pdf"
    pdf_path.write_bytes(b"test PDF")
    api = Mock(side_effect=lambda url: (
        {"Items": [{"Id": "person-1", "Name": "Test Person",
                    "PoliticalParty": {"Name": "Testpartiet", "Id": "party-1"}}]}
        if url == ReportConfig.api_url_all_council_representatives else
        [{"RepresentativeId": "person-1", "Role": "Ledamot", "DateFrom": "2022-10-15",
          "DateTo": None, "Number": 1, "State": "Active"}]
    ))
    html = Mock()
    read_pdf = Mock(return_value=[
        "Protokollet omfattar §§1-2", "Beslutande ledamöter",
        "Test Person (S)", "Ej tjänstgörande ersättare",
    ])
    monkeypatch.setattr(council, "get_api_json", api)
    monkeypatch.setattr(meetings, "get_page_html", html)
    monkeypatch.setattr(meetings, "find_meeting_urls", lambda *args: pd.DataFrame({
        "date": [pd.Timestamp("2024-01-01")], "url": ["https://example.test/meeting"],
    }))
    monkeypatch.setattr(meetings, "find_pdf_url", lambda *args: "https://example.test/protocol.pdf")
    monkeypatch.setattr(app, "download_meeting_pdfs", Mock())
    monkeypatch.setattr(single_meeting, "get_text_from_pdf", read_pdf)
    return api, html, read_pdf, pdf_path


def test_second_run_uses_cache_and_saves_same_attendance(cached_app):
    api, html, read_pdf, _ = cached_app
    first = app.main()
    second = app.main()
    pd.testing.assert_frame_equal(first, second)
    assert api.call_count == 2
    assert html.call_count == 2
    assert read_pdf.call_count == 1
    saved = pd.read_csv(app.attendance_path, parse_dates=["date"])
    assert saved["status"].tolist() == ["present", "present"]
    assert saved["paragraph"].tolist() == [1, 2]


@pytest.mark.parametrize("flag,expected_calls", [
    ("use_council_cache", (4, 2, 1)),
    ("use_meetings_cache", (2, 4, 1)),
    ("use_reading_cache", (2, 2, 2)),
])
def test_flags_refresh_only_the_selected_stage(cached_app, monkeypatch, flag, expected_calls):
    api, html, read_pdf, _ = cached_app
    app.main()
    monkeypatch.setattr(app, flag, False)
    app.main()
    assert (api.call_count, html.call_count, read_pdf.call_count) == expected_calls


def test_changed_pdf_is_read_again(cached_app):
    _, _, read_pdf, pdf_path = cached_app
    app.main()
    pdf_path.write_bytes(b"changed PDF content")
    app.main()
    assert read_pdf.call_count == 2


def test_unreadable_pdf_keeps_status_when_cached(cached_app):
    _, _, read_pdf, _ = cached_app
    read_pdf.return_value = None
    assert app.main().empty
    assert app.main().empty
    assert read_pdf.call_count == 1
    meetings = pd.read_csv(app.analysis_meetings_path)
    assert meetings["read_status"].tolist() == ["unreadable_text"]
