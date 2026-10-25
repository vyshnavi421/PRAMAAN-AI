"""Regression tests for demo-mode authentication guards."""

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_demo_login_rejected_when_demo_mode_disabled(monkeypatch):
    monkeypatch.setattr(settings, "IS_DEMO_MODE", False)

    response = client.post(
        "/api/v1/auth/session",
        json={"user_id": "usr-officer-01"},
    )

    assert response.status_code == 403


def test_demo_user_discovery_rejected_when_demo_mode_disabled(monkeypatch):
    monkeypatch.setattr(settings, "IS_DEMO_MODE", False)

    response = client.get("/api/v1/auth/demo-users")

    assert response.status_code == 403


def test_demo_login_available_when_demo_mode_enabled(monkeypatch):
    monkeypatch.setattr(settings, "IS_DEMO_MODE", True)

    response = client.post(
        "/api/v1/auth/session",
        json={"user_id": "usr-officer-01"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "REVIEWER"