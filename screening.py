"""Strict schema screen for uploaded rosters -- keeps PII out of the system.

The only roster the app accepts is de-identified: exactly one ``ID Alias`` column
(values = a non-repeating permutation of 1..n) plus one or more ``Func <int>`` columns
whose cells are strictly True/False. Any name/PII column, stray column, bad ID set, or
non-boolean cell is rejected here -- before the roster is parsed or solved -- so employee
names never reach the service. All violations raise ``ValueError`` (the web layer maps
that to HTTP 400).
"""

import re

ID_ALIAS_COL = "ID Alias"
_FUNC_RE = re.compile(r"^Func \d+$")


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _is_boolean_cell(value) -> bool:
    """True only for an unambiguous boolean; anything else (text, blank, 2, …) is rejected."""
    if isinstance(value, bool):
        return True
    if isinstance(value, int):          # bool is caught above; here 0/1 only
        return value in (0, 1)
    if isinstance(value, float):
        return value in (0.0, 1.0)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "false", "1", "0"}
    return False


def _as_int(value, col):
    if isinstance(value, bool):
        raise ValueError(f"'{col}' must be whole numbers, got {value!r}.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        raise ValueError(f"'{col}' must be whole numbers, got {value!r}.")


def screen_task_columns(task_columns):
    """Every non-identifier column must be a unique ``Func <int>`` (never a name/PII column)."""
    if not task_columns:
        raise ValueError("Roster needs at least one 'Func N' column.")
    for col in task_columns:
        if not _FUNC_RE.match(str(col)):
            raise ValueError(
                f"Unexpected column {col!r}. Only 'ID Alias' and 'Func 1', 'Func 2', … "
                "columns are allowed -- no names or other personal data. "
                "Use the roster template to produce a valid file.")
    if len(set(task_columns)) != len(task_columns):
        raise ValueError("Duplicate 'Func N' columns are not allowed.")


def screen_id_permutation(ids):
    """The identifiers must be exactly the whole numbers 1..n, each once (no repeats)."""
    coerced = [_as_int(v, ID_ALIAS_COL) for v in ids]
    n = len(coerced)
    if sorted(coerced) != list(range(1, n + 1)):
        raise ValueError(
            f"'ID Alias' values must be the whole numbers 1..{n} with no repeats "
            f"(got {sorted(coerced)}). Use the roster template to generate them.")


def screen_roster(columns, records):
    """Validate a parsed upload against the de-identified schema. Raises ValueError."""
    if ID_ALIAS_COL not in columns:
        raise ValueError(
            f"Roster must have an '{ID_ALIAS_COL}' column and no names or other personal data. "
            "Use the roster template to produce a valid file.")
    task_columns = [col for col in columns if col != ID_ALIAS_COL]
    screen_task_columns(task_columns)

    rows = [row for row in records if not _is_blank(row.get(ID_ALIAS_COL))]
    if not rows:
        raise ValueError("Roster has no employees.")

    for row in rows:
        for col in task_columns:
            if not _is_boolean_cell(row.get(col)):
                raise ValueError(
                    f"Column {col!r} must contain only True/False values "
                    f"(found {row.get(col)!r}). Remove any names, notes, or blanks.")

    screen_id_permutation([row.get(ID_ALIAS_COL) for row in rows])
