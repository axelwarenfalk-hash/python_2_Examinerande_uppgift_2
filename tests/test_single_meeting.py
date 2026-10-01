from malmo_council_attendance.single_meeting import (
    merge_attendance_lines,
    structure_replacements_section,
)


def test_comma_before_replaces_preserves_both_assignments():
    rows = merge_attendance_lines([
        "Amanda Johannesson (S) §§234-238 (p. 1-2), ersätter Sanna Axelsson (S),",
        "§ 238 (p. 8-11), §§240-242 ersätter Björn Gudmundsson (S)",
    ])
    replacements = structure_replacements_section(rows, list(range(234, 243)))

    assert len(replacements) == 1
    assignments = replacements[0]["replaces"]
    assert [row["member"]["name"] for row in assignments] == [
        "Sanna Axelsson", "Björn Gudmundsson",
    ]
    assert [row["paragraphs"] for row in assignments] == [
        [234, 235, 236, 237, 238], [238, 240, 241, 242],
    ]


def test_comma_inside_party_parenthesis_preserves_three_assignments():
    rows = merge_attendance_lines([
        "Isabel Enström (MP) § 193 (p. 4–5) ersätter Stefana Hoti (MP,)",
        "§ 193 (p. 6–10) ersätter Mohamed Yassin (MP), § 193 (p. 11),",
        "§§ 194–198 ersätter Surra Al Sakban (MP)",
        "Nästa Person (S)",
    ])

    assert rows[1] == "Nästa Person (S)"
    replacements = structure_replacements_section(rows[:1], list(range(190, 199)))
    assignments = replacements[0]["replaces"]
    assert [row["member"]["name"] for row in assignments] == [
        "Stefana Hoti", "Mohamed Yassin", "Surra Al Sakban",
    ]
    assert all(row["member"]["party"] == "MP" for row in assignments)
    assert [row["paragraphs"] for row in assignments] == [
        [193], [193], [193, 194, 195, 196, 197, 198],
    ]
