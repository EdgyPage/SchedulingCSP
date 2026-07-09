import csv
import io

from openpyxl import load_workbook

import io_adapters as ia

ROWS = [
    {"ID": 1, "Name": "Alice", "A": True, "B": False},
    {"ID": 2, "Name": "Bob", "A": False, "B": True},
]
COLUMNS = ["ID", "Name", "A", "B"]


def _rows_to_csv_bytes(rows, columns):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def _read_xlsx_sheet(xlsx, sheet):
    wb = load_workbook(io.BytesIO(xlsx))
    rows = list(wb[sheet].iter_rows(values_only=True))
    header = list(rows[0])
    data = [dict(zip(header, row)) for row in rows[1:]]
    return header, data


def test_parsers_agree_across_formats():
    emps_rec, tasks_rec = ia.parse_roster_records(ROWS, COLUMNS)

    emps_csv, tasks_csv = ia.parse_roster_csv(_rows_to_csv_bytes(ROWS, COLUMNS))

    form = {
        "tasks": ["A", "B"],
        "employees": [
            {"id": 1, "name": "Alice", "approved": ["A"]},
            {"id": 2, "name": "Bob", "approved": ["B"]},
        ],
    }
    emps_form, tasks_form = ia.parse_roster_form(form)

    assert tasks_rec == tasks_csv == tasks_form == ["A", "B"]
    for group in (emps_rec, emps_csv, emps_form):
        assert [emp.taskStatuses for emp in group] == [[True, False], [False, True]]


def test_missing_required_column_raises():
    try:
        ia.parse_roster_records([{"ID": 1, "A": True}], ["ID", "A"])  # no Name column
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
    header, data = _read_xlsx_sheet(xlsx, "Schedule_1")
    assert header == ["Name", "ID", "Function"]
    assert len(data) == 2

    csv_bytes = ia.results_to_csv_bytes(results)
    assert b"Schedule,Name,ID,Function" in csv_bytes


def test_closest_export_includes_summary_when_meta_given():
    """A near-miss export carries a Summary sheet / block; a plain export does not."""
    results = [[{"Name": "alice", "ID": 1, "Function": "A"}]]
    meta = {
        "tasks": ["A", "B"], "target": [2, 1], "metric": "cosine", "mode": "thorough",
        "schedules": [
            {"distance": 0.05, "coverage": [1, 1], "shortfall": [1, 0],
             "covered": 2, "target_total": 3},
        ],
    }

    xlsx = ia.results_to_xlsx_bytes(results, meta=meta)
    assert "Summary" in load_workbook(io.BytesIO(xlsx)).sheetnames
    assert "Summary" not in load_workbook(io.BytesIO(ia.results_to_xlsx_bytes(results))).sheetnames

    csv_bytes = ia.results_to_csv_bytes(results, meta=meta)
    assert b"Closest schedules" in csv_bytes
    assert b"Closest schedules" not in ia.results_to_csv_bytes(results)
