import httpx
from test_finance import entry


def test_upload_and_download_use_user_jwt(client, household, monkeypatch):
    h = household
    expense = client.post("/api/entries", json=entry(h)).json()
    calls = []

    def storage(method, path, identity, **kwargs):
        calls.append((method, path, identity.id, kwargs))
        return httpx.Response(200, content=b"%PDF-1.7\nfixture")

    monkeypatch.setattr("app.routers.storage.storage_request", storage)
    response = client.post(
        "/api/entries/" + expense["id"] + "/attachments?filename=comprovante.pdf",
        content=b"%PDF-1.7\nfixture",
        headers={"Content-Type": "application/pdf"},
    )
    assert response.status_code == 201, response.text
    assert str(calls[0][2]) == h["rita"]
    assert calls[0][1].startswith(
        "object/comprovantes/" + h["rita"] + "/" + expense["id"]
    )
    id = response.json()["id"]
    result = client.get("/api/attachments/" + id)
    assert result.status_code == 200
    assert result.content.startswith(b"%PDF-")
    assert result.headers["content-disposition"].startswith("attachment;")
    assert len(client.get("/api/entries/" + expense["id"] + "/attachments").json()) == 1


def test_invalid_content_and_oversized_upload_rejected(client, household):
    expense = client.post("/api/entries", json=entry(household)).json()
    path = "/api/entries/" + expense["id"] + "/attachments?filename=file.pdf"
    assert (
        client.post(
            path, content=b"not pdf", headers={"Content-Type": "application/pdf"}
        ).status_code
        == 415
    )
    assert (
        client.post(
            path, content=b"<html>", headers={"Content-Type": "text/html"}
        ).status_code
        == 415
    )
    assert (
        client.post(
            path,
            content=b"%PDF-" + b"x" * (5 * 1024 * 1024),
            headers={"Content-Type": "application/pdf"},
        ).status_code
        == 413
    )
