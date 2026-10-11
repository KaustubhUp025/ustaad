from fastapi.testclient import TestClient

from app.main import app


def test_healthz_served_under_api_prefix():
    assert TestClient(app).get("/api/healthz").json()["ok"] is True


def test_healthz_reports_models(monkeypatch):
    monkeypatch.setenv("FLASH_MODEL", "gemini-3.8-flash")
    body = TestClient(app).get("/healthz").json()
    assert body["ok"] is True
    assert body["flash_model"] == "gemini-3.8-flash"
