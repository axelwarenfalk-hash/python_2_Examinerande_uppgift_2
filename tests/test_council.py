import pandas as pd
import pytest
from unittest.mock import patch

from malmo_council_attendance.council import (
    make_all_members_dataframe,
    make_all_roles_dataframe,
    merge_all_members_with_all_roles,
)


def test_make_all_members_dataframe_normalizes_and_selects_member_columns():
    json_data = {
        "Items": [
            {
                "Id": 42,
                "Name": "Testperson",
                "PoliticalParty": {"Name": "Arbetarpartiet", "Id": 7},
                "UnneededField": "ignorera",
            }
        ]
    }

    with patch("malmo_council_attendance.council.logger.info") as mock_info:
        result = make_all_members_dataframe(json_data)

    expected = pd.DataFrame(
        [
            {
                "representative_id": 42,
                "name": "Testperson",
                "political_party": "Arbetarpartiet",
                "political_party_id": 7,
            }
        ]
    )
    pd.testing.assert_frame_equal(result, expected)
    mock_info.assert_called_once_with("Normaliserade %d ledamöter", 1)


def test_make_all_members_dataframe_returns_empty_frame_with_expected_columns():
    with pytest.raises(KeyError):
        make_all_members_dataframe({"Items": []})


def test_make_all_roles_dataframe_selects_role_columns():
    json_data = [
        {
            "RepresentativeId": 42,
            "Role": "Ledamot",
            "DateFrom": "2022-10-15",
            "DateTo": None,
            "Number": 1,
            "State": "Active",
            "Committee_Name": "Kommunfullmäktige",
            "UnneededField": "ignorera",
        }
    ]

    with patch("malmo_council_attendance.council.logger.info") as mock_info:
        result = make_all_roles_dataframe(json_data)

    expected = pd.DataFrame(
        [
            {
                "representative_id": 42,
                "role": "Ledamot",
                "date_from": "2022-10-15",
                "date_to": None,
                "council_number": 1,
                "state": "Active",
            }
        ]
    )
    pd.testing.assert_frame_equal(result, expected)
    mock_info.assert_called_once_with("Normaliserade %d rollrader", 1)


def test_make_all_roles_dataframe_raises_key_error_for_empty_input():
    with pytest.raises(KeyError):
        make_all_roles_dataframe([])


def test_merge_all_members_with_all_roles_left_merges_on_representative_id():
    members_df = pd.DataFrame(
        [
            {
                "representative_id": 42,
                "name": "Testperson",
                "political_party": "Arbetarpartiet",
                "political_party_id": 7,
            },
            {
                "representative_id": 99,
                "name": "Utan roll",
                "political_party": "Gröna partiet",
                "political_party_id": 8,
            },
        ]
    )
    roles_df = pd.DataFrame(
        [
            {
                "representative_id": 42,
                "role": "Ledamot",
                "date_from": "2022-10-15",
                "date_to": None,
                "council_number": 1,
                "state": "Current",
            },
            {
                "representative_id": 42,
                "role": "Ordförande",
                "date_from": "2023-01-01",
                "date_to": None,
                "council_number": 1,
                "state": "Current",
            },
        ]
    )

    with patch("malmo_council_attendance.council.logger.info") as mock_info:
        result = merge_all_members_with_all_roles(members_df, roles_df)

    expected_matches = pd.DataFrame(
        [
            {
                "representative_id": 42,
                "name": "Testperson",
                "political_party": "Arbetarpartiet",
                "political_party_id": 7,
                "role": "Ledamot",
                "date_from": "2022-10-15",
                "date_to": None,
                "council_number": 1,
                "state": "Current",
            },
            {
                "representative_id": 42,
                "name": "Testperson",
                "political_party": "Arbetarpartiet",
                "political_party_id": 7,
                "role": "Ordförande",
                "date_from": "2023-01-01",
                "date_to": None,
                "council_number": 1,
                "state": "Current",
            },
        ]
    )
    pd.testing.assert_frame_equal(
        result.iloc[:2],
        expected_matches,
        check_dtype=False,
    )
    assert result.loc[2, "representative_id"] == 99
    assert result.loc[2, "name"] == "Utan roll"
    assert result.loc[2, roles_df.columns.drop("representative_id")].isna().all()
    mock_info.assert_called_once_with(
        "Slog ihop ledamöter och roller: %d personer, %d rollrader, %d resultat",
        2,
        2,
        3,
    )


def test_merge_all_members_with_all_roles_keeps_members_when_roles_are_empty():
    members_df = pd.DataFrame(
        [{"representative_id": 42, "name": "Testperson"}]
    )
    roles_df = pd.DataFrame(columns=["representative_id", "role"])

    result = merge_all_members_with_all_roles(members_df, roles_df)

    assert result[["representative_id", "name"]].to_dict("records") == [
        {"representative_id": 42, "name": "Testperson"}
    ]
    assert pd.isna(result.loc[0, "role"])


def test_separate_members_from_replacements_logs_row_counts():
    from malmo_council_attendance.council import separate_members_from_replacements

    data = pd.DataFrame(
        [
            {"name": "Ledamot", "council_number": 1},
            {"name": "Ersättare", "council_number": 62},
        ]
    )

    with patch("malmo_council_attendance.council.logger.info") as mock_info:
        members_df, replacements_df = separate_members_from_replacements(data)

    assert members_df["name"].tolist() == ["Ledamot"]
    assert replacements_df["name"].tolist() == ["Ersättare"]
    mock_info.assert_called_once_with(
        "Delade upp rådata: %d ledamotsrader, %d ersättarrader",
        1,
        1,
    )