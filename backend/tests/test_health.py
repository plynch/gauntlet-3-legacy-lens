from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["service"] == "LegacyLens API"
    assert payload["qdrant_configured"] is True
    assert payload["openai_mode"] in {"openai", "fallback"}
    assert "degraded_reason" in payload
