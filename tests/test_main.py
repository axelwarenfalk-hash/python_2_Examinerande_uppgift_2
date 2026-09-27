from unittest.mock import call, patch

import pandas as pd

from malmo_council_attendance import __main__ as app


def test_main_logs_start_and_member_replacement_summary():
    members_df = pd.DataFrame({"representative_id": [1]})
    roles_df = pd.DataFrame({"representative_id": [1]})
    merged_df = pd.DataFrame({"representative_id": [1]})
    replacements_df = pd.DataFrame({"representative_id": [2, 3]})

    with (
        patch.object(app, "config_logging") as mock_config_logging,
        patch.object(app, "get_json", side_effect=[{}, []]),
        patch.object(app, "make_all_members_dataframe", return_value=members_df),
        patch.object(app, "make_all_roles_dataframe", return_value=roles_df),
        patch.object(
            app,
            "merge_all_members_with_all_roles",
            return_value=merged_df,
        ),
        patch.object(
            app,
            "separate_members_from_replacements",
            return_value=(members_df, replacements_df),
        ),
        patch.object(app, "get_meetings"),
        patch.object(app.logger, "info") as mock_info,
    ):
        app.main()

    mock_config_logging.assert_called_once_with()
    assert mock_info.call_args_list == [
        call("Startar inläsning av kommunfullmäktiges grunddata"),
        call(
            "Grunddata klar: %d ledamotsrader och %d ersättarrader",
            1,
            2,
        ),
        call("Möteslistan är tillgänglig för vidare bearbetning"),
    ]