import io

import pandas as pd

import io_adapters as ia


def test_parsers_agree_across_formats():
    df = pd.DataFrame([
        {"ID": 1, "Name": "Alice", "A": True, "B": False},
        {"ID": 2, "Name": "Bob", "A": False, "B": True},
    ])
    emps_df, tasks_df = ia.parse_roster_dataframe(df)

    emps_csv, tasks_csv = ia.parse_roster_csv(df.to_csv(index=False).encode())

    form = {
        "tasks": ["A", "B"],
        "employees": [
            {"id": 1, "name": "Alice", "approved": ["A"]},
            {"id": 2, "name": "Bob", "approved": ["B"]},
        ],
    }
    emps_form, tasks_form = ia.parse_roster_form(form)

    assert tasks_df == tasks_csv == tasks_form == ["A", "B"]
    for group in (emps_df, emps_csv, emps_form):
        assert [emp.taskStatuses for emp in group] == [[True, False], [False, True]]


def test_missing_required_column_raises():
    df = pd.DataFrame([{"ID": 1, "A": True}])  # no Name column
    try:
        ia.parse_roster_dataframe(df)
    except ValueError as exc:
        assert "Name" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing Name column")


def test_result_serializers_produce_valid_files():
    results = [
        [
            {"Name": "alice", "ID": 1, "Function": "A"},
            {"Name": "bob", "ID": 2, "Function": "Unassigned"},
        ],
    ]

    xlsx = ia.results_to_xlsx_bytes(results)
    assert xlsx[:2] == b"PK"  # xlsx is a zip archive
    back = pd.read_excel(io.BytesIO(xlsx), sheet_name="Schedule_1")
    assert list(back.columns) == ["Name", "ID", "Function"]
    assert len(back) == 2

    csv = ia.results_to_csv_bytes(results)
    assert b"Schedule,Name,ID,Function" in csv
