"""Smoke tests for the browser demo's basic delivery path.

These checks do not prove that every interactive workflow works in a real browser;
they guard the key entry points needed to start the local demo.
"""
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_a_demo_disclosure_and_mode_flag():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert isinstance(payload["is_demo_mode"], bool)
    assert "DEMO" in payload.get("banner", "").upper()


def test_root_serves_the_pramaan_demo_with_clear_disclosure():
    response = client.get("/")

    assert response.status_code == 200
    assert "PRAMAAN-AI" in response.text
    assert "DEMO DATA" in response.text
    assert "NOT CONNECTED TO LIVE AICTE SYSTEMS" in response.text


def test_browser_entry_and_stylesheet_are_served():
    app_module = client.get("/js/app.js")
    api_module = client.get("/js/api.js")
    stylesheet = client.get("/css/tokens.css")

    assert app_module.status_code == 200
    assert "AppRouter" in app_module.text
    assert api_module.status_code == 200
    assert "class ApiClient" in api_module.text
    assert stylesheet.status_code == 200
