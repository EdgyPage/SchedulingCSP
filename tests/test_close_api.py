import io

from fastapi.testclient import TestClient
from openpyxl import load_workbook

import config
from app import app

INFEASIBLE = {
    "tasks": ["A", "B", "C"],
    "employees": [
        {"id": 1, "name": "a", "approved": ["A"]},
        {"id": 2, "name": "b", "approved": ["B"]},
        {"id": 3, "name": "c", "approved": ["C"]},
    ],
    "minimums": [1, 1, 3],       # C needs 3 but only employee 3 can do it
    "seed": 0,
}


def _client(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", None)
    return TestClient(app)


def test_solve_endpoint_returns_infeasibility_and_closest(monkeypatch):
    body = _client(monkeypatch).post("/api/solve", json=INFEASIBLE).json()
    assert body["count"] == 0
    assert body["tasks"] == ["A", "B", "C"]
    assert any(r["task"] == "C" for r in body["infeasibility"]["reasons"])
    closest = body["closest"]
    assert closest["metric"] == "cosine" and closest["mode"] == "thorough"
    assert closest["schedules"][0]["coverage"] == [1, 1, 1]


def test_solve_endpoint_rejects_bad_metric_mode_and_minimums(monkeypatch):
    client = _client(monkeypatch)
    assert client.post("/api/solve", json={**INFEASIBLE, "metric": "nope"}).status_code == 400
    assert client.post("/api/solve", json={**INFEASIBLE, "mode": "nope"}).status_code == 400
    assert client.post("/api/solve", json={**INFEASIBLE, "minimums": [1, 1, 1.5]}).status_code == 400


def test_export_with_meta_adds_summary(monkeypatch):
    client = _client(monkeypatch)
    payload = {
        "schedules": [[{"Name": "a", "ID": 1, "Function": "A"}]],
        "meta": {
            "tasks": ["A", "B"], "target": [1, 2], "metric": "cosine", "mode": "thorough",
            "schedules": [{"distance": 0.1, "coverage": [1, 1], "shortfall": [0, 1],
                           "covered": 2, "target_total": 3}],
        },
    }
    xlsx = client.post("/api/export?format=xlsx", json=payload)
    assert xlsx.status_code == 200
    assert "Summary" in load_workbook(io.BytesIO(xlsx.content)).sheetnames
    assert b"Closest schedules" in client.post("/api/export?format=csv", json=payload).content
