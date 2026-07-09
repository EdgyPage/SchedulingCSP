"""Sanity checks for the shipped roster template (frontend/roster-template.xlsx).

The template is authored in Excel -- it carries a Power Query that openpyxl cannot create --
so this only confirms the downloadable file still loads and advertises the upload contract
the site documents: an ``Encoded`` table with headers ID Alias, Func 1, Func 2, ... The
encode/decode behavior is verified in Excel (see docs/roster-template-spec.md).
"""

import os
import re

import pytest
from openpyxl import load_workbook

_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "roster-template.xlsx")


@pytest.fixture(scope="module")
def wb():
    if not os.path.exists(_TEMPLATE):
        pytest.skip("roster template not present")
    return load_workbook(_TEMPLATE)


def _headers(wb, table_name):
    for ws in wb.worksheets:
        if table_name in ws.tables:
            return [c.value for c in ws[ws.tables[table_name].ref][0]]
    raise AssertionError(f"table {table_name!r} not found in any sheet")


def test_template_loads_with_core_tables(wb):
    tables = {name for ws in wb.worksheets for name in ws.tables}
    assert {"Roster", "Encoded", "SolverOutput"} <= tables


def test_encoded_advertises_the_upload_schema(wb):
    headers = _headers(wb, "Encoded")
    assert headers[0] == "ID Alias"
    assert headers[1:], "expected at least one Func column"
    assert all(re.fullmatch(r"Func \d+", str(h)) for h in headers[1:])
