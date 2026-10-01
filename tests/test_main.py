from unittest.mock import patch

import pandas as pd

from malmo_council_attendance import __main__ as app


def test_main_connects_stages_and_returns_saved_attendance():
    members = pd.DataFrame({"representative_id": [1]})
    meetings = pd.DataFrame({"date": [pd.Timestamp("2024-01-01")]})
    attendance = pd.DataFrame({"status": ["present"]})
    with (
        patch.object(app, "config_logging"),
        patch.object(app, "load_council", return_value=(members, pd.DataFrame())) as council,
        patch.object(app, "load_meetings", return_value=meetings) as meeting_loader,
        patch.object(app, "select_members_from_term_start", return_value=(members, pd.DataFrame())),
        patch.object(app, "select_term_meetings", return_value=meetings),
        patch.object(app, "make_analysis_summary", return_value={}),
        patch.object(app, "save_json"),
        patch.object(app, "download_meeting_pdfs") as download,
        patch.object(app, "build_attendance", return_value=attendance) as build,
        patch.object(app, "save_dataframe") as save,
    ):
        assert app.main() is attendance
    council.assert_called_once_with(app.council_cache_path, app.use_council_cache)
    meeting_loader.assert_called_once_with(app.meetings_cache_path, app.use_meetings_cache)
    download.assert_called_once_with(meetings, app.pdf_dir)
    build.assert_called_once_with(meetings, members, app.pdf_dir, app.reading_cache_dir,
                                  app.analysis_meetings_path, app.use_reading_cache)
    save.assert_called_once_with(attendance, app.attendance_path)
