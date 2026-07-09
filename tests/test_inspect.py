"""Tests for the /api/inspect endpoint and the served frontend."""

import config
from fastapi.testclient import TestClient

from app import app

CSV = b"ID Alias,Func 1,Func 2\n1,1,0\n2,0,1\n3,1,1\n"


def test_inspect_returns_tasks_and_count(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", None)
    client = TestClient(app)
    r = client.post("/api/inspect", files={"file": ("roster.csv", CSV, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["tasks"] == ["Func 1", "Func 2"]
    assert body["employee_count"] == 3


def test_inspect_rejects_unsupported_extension(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", None)
    client = TestClient(app)
    r = client.post("/api/inspect", files={"file": ("roster.txt", CSV, "text/plain")})
    assert r.status_code == 400


def test_inspect_rejects_oversized_upload(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", None)
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 5)
    client = TestClient(app)
    r = client.post("/api/inspect", files={"file": ("roster.csv", CSV, "text/csv")})
    assert r.status_code == 413


def test_inspect_honors_api_key_gate(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(config, "API_KEY", "s3cret")
    files = {"file": ("roster.csv", CSV, "text/csv")}
    assert client.post("/api/inspect", files=files).status_code == 401
    assert client.post(
        "/api/inspect", files=files, headers={"X-API-Key": "s3cret"}
    ).status_code == 200


def test_root_serves_frontend():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Solver" in r.text
