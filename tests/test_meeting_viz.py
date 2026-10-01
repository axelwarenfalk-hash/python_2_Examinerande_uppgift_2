import pandas as pd

from malmo_council_attendance.viz import summarize_meeting_attendance


def test_meeting_counts_do_not_depend_on_paragraph_count():
    rows = []
    for date, statuses in [
        ("2024-01-01", ["present", "absent_with_replacement", "present"]),
        ("2024-02-01", ["absent_with_replacement"] * 10),
        ("2024-03-01", ["absent_without_replacement"]),
    ]:
        for status in statuses:
            rows.append(dict(date=date, representative_id=1, member="A", party="S", status=status))
    data = pd.DataFrame(rows)
    result = summarize_meeting_attendance(data, ["party"]).iloc[0]
    assert result.observations == 3
    assert abs(result.present - 100 / 3) < 1e-8
    assert abs(result.absent_with_replacement - 100 / 3) < 1e-8
    assert abs(result.absent_without_replacement - 100 / 3) < 1e-8
    assert abs(result.present + result.absent_with_replacement + result.absent_without_replacement - 100) < 1e-8
