import httpx
import pytest

from ingestion.http_client import get_with_retry


def _client_with_handler(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_returns_response_on_success():
    def handler(request):
        return httpx.Response(200, json={"ok": True})

    client = _client_with_handler(handler)
    response = get_with_retry(client, "https://example.com")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_retries_on_retryable_status_then_succeeds():
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    client = _client_with_handler(handler)
    response = get_with_retry(client, "https://example.com", max_retries=3, backoff_seconds=0)

    assert response.status_code == 200
    assert calls["count"] == 3


def test_raises_after_exhausting_retries():
    def handler(request):
        return httpx.Response(503)

    client = _client_with_handler(handler)

    with pytest.raises(httpx.HTTPStatusError):
        get_with_retry(client, "https://example.com", max_retries=2, backoff_seconds=0)


def test_does_not_retry_non_retryable_error():
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        return httpx.Response(404)

    client = _client_with_handler(handler)

    with pytest.raises(httpx.HTTPStatusError):
        get_with_retry(client, "https://example.com", max_retries=3, backoff_seconds=0)

    assert calls["count"] == 1
