from fastapi.testclient import TestClient

from detector_golpe.api import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_analyze_batch():
    scam = "Aprovação imediata, sem entrevista. Pague a taxa de cadastro e chame no WhatsApp."
    r = client.post("/analyze", json={"jobs": [{"id": "1", "title": "Digitador", "text": scam}]})
    assert r.status_code == 200
    body = r.json()
    assert body[0]["verdict"] == "SUSPEITA"
    assert {"G1", "G2", "G4"} <= {s["code"] for s in body[0]["signals"]}


def test_rejects_empty_batch_and_empty_text():
    assert client.post("/analyze", json={"jobs": []}).status_code == 422
    assert client.post("/analyze", json={"jobs": [{"id": "1", "text": ""}]}).status_code == 422
