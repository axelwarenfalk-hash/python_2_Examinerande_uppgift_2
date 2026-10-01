import pandas as pd

from malmo_council_attendance.attendance import make_meeting_attendance


def test_presence_replacement_and_absence_are_preserved():
    members = pd.DataFrame([
        {"representative_id": 1, "name": "A", "political_party": "S"},
        {"representative_id": 2, "name": "B", "political_party": "S"},
    ])
    reading = {
        "paragraphs": [1, 2],
        "members": [{"name": "A", "paragraphs": [1]}],
        "replacements": [{"name": "C", "replaces": [
            {"member": {"name": "A"}, "paragraphs": [1, 2]},
        ]}],
    }
    rows = make_meeting_attendance(pd.Timestamp("2024-01-01"), members, reading)
    assert [(row["member"], row["paragraph"], row["status"], row["replaced_by"]) for row in rows] == [
        ("A", 1, "present", None),
        ("B", 1, "absent_without_replacement", None),
        ("A", 2, "absent_with_replacement", "C"),
        ("B", 2, "absent_without_replacement", None),
    ]
