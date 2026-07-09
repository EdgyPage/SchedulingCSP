import pytest

from screening import (
    ID_ALIAS_COL, screen_id_permutation, screen_roster, screen_task_columns,
)


def _roster(n=3, funcs=2):
    columns = [ID_ALIAS_COL] + [f"Func {i}" for i in range(1, funcs + 1)]
    records = [
        {ID_ALIAS_COL: i, **{f"Func {j}": (i + j) % 2 == 0 for j in range(1, funcs + 1)}}
        for i in range(1, n + 1)
    ]
    return columns, records


def test_valid_roster_passes():
    columns, records = _roster()
    screen_roster(columns, records)  # must not raise


def test_rejects_name_column():
    columns, records = _roster()
    columns.append("Name")
    for r in records:
        r["Name"] = "alice"
    with pytest.raises(ValueError, match="Unexpected column"):
        screen_roster(columns, records)


def test_rejects_missing_id_alias():
    _, records = _roster()
    with pytest.raises(ValueError, match="ID Alias"):
        screen_roster(["ID", "Func 1", "Func 2"], records)


def test_rejects_non_func_task_column():
    with pytest.raises(ValueError, match="Unexpected column"):
        screen_roster([ID_ALIAS_COL, "Func 1", "Shift"],
                      [{ID_ALIAS_COL: 1, "Func 1": True, "Shift": True}])


def test_rejects_duplicate_func_column():
    with pytest.raises(ValueError, match="Duplicate"):
        screen_task_columns(["Func 1", "Func 1"])


def test_rejects_no_func_columns():
    with pytest.raises(ValueError, match="at least one"):
        screen_task_columns([])


def test_rejects_non_boolean_cell():
    columns, records = _roster(n=2, funcs=1)
    records[0]["Func 1"] = "maybe"
    with pytest.raises(ValueError, match="True/False"):
        screen_roster(columns, records)


def test_rejects_blank_cell():
    columns, records = _roster(n=2, funcs=1)
    records[0]["Func 1"] = None
    with pytest.raises(ValueError, match="True/False"):
        screen_roster(columns, records)


@pytest.mark.parametrize("bad_ids", [[1, 2, 2], [1, 2, 4], [0, 1, 2], [2, 3]])
def test_rejects_non_permutation_ids(bad_ids):
    with pytest.raises(ValueError):
        screen_id_permutation(bad_ids)


def test_permutation_accepts_any_order():
    screen_id_permutation([3, 1, 2])  # order doesn't matter


def test_boolean_and_string_forms_accepted():
    # True/False, 0/1, and "TRUE"/"false" (from CSV) all count as booleans; string ids too.
    columns = [ID_ALIAS_COL, "Func 1", "Func 2", "Func 3"]
    records = [
        {ID_ALIAS_COL: "1", "Func 1": True, "Func 2": 0, "Func 3": "TRUE"},
        {ID_ALIAS_COL: "2", "Func 1": False, "Func 2": 1, "Func 3": "false"},
    ]
    screen_roster(columns, records)
