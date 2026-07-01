"""Per-worker streaming concurrency cap (#56).

The module semaphore ``wit.views._stream_semaphore`` is built at import time from
``settings.MAX_CONCURRENT_STREAMS``, so ``override_settings`` cannot resize it.
These tests patch the module attribute directly with a size-1 semaphore.
"""

import threading
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from wit import views


@pytest.fixture(autouse=True)
def _locmem_cache(settings):
    # AnonRateThrottle needs a real cache backend; keep it local to the test run.
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }


class TestStreamCapacity:
    def setup_method(self):
        self.client = APIClient()

    @patch("wit.views.WitService.generate_stream")
    def test_exhausted_semaphore_returns_503_without_calling_service(
        self, mock_stream, monkeypatch
    ):
        sem = threading.BoundedSemaphore(1)
        monkeypatch.setattr(views, "_stream_semaphore", sem)
        # Occupy the only slot so the request cannot acquire one.
        assert sem.acquire(blocking=False)

        resp = self.client.get("/v1/wit/say-no/?stream=true")

        assert resp.status_code == 503
        assert resp["Content-Type"].startswith("text/event-stream")
        assert resp["Retry-After"] == "5"
        body = b"".join(resp.streaming_content).decode()
        assert "stream_capacity" in body
        assert "data: [DONE]" in body
        # Fast rejection: the LLM/service is never touched.
        mock_stream.assert_not_called()

    @pytest.mark.django_db
    @patch("wit.views.WitService.generate_stream")
    def test_stream_works_after_slot_is_released(
        self, mock_stream, monkeypatch, persona_no
    ):
        mock_stream.return_value = iter(
            [{"delta": "Hi"}, {"persona": "The Refusal Artist", "done": True}]
        )
        sem = threading.BoundedSemaphore(1)
        monkeypatch.setattr(views, "_stream_semaphore", sem)

        resp = self.client.get("/v1/wit/say-no/?stream=true")

        assert resp.status_code == 200
        assert resp["Content-Type"].startswith("text/event-stream")
        body = b"".join(resp.streaming_content).decode()
        assert 'data: {"delta": "Hi"}' in body
        assert "data: [DONE]" in body
        # The slot is freed once the stream fully drains, so it can be reused.
        assert sem.acquire(blocking=False)
        sem.release()

    @patch("wit.views.WitService.generate_stream")
    def test_guarded_generator_releases_slot_on_completion(
        self, mock_stream, monkeypatch
    ):
        mock_stream.return_value = iter([{"delta": "Hi"}, {"done": True}])
        sem = threading.BoundedSemaphore(1)
        monkeypatch.setattr(views, "_stream_semaphore", sem)
        # Mimic _stream_response taking the slot for this stream.
        assert sem.acquire(blocking=False)

        list(views.BaseWitView._sse_events_guarded("say-no", None, None, None, None))

        # finally released the slot on normal completion.
        assert sem.acquire(blocking=False)
        sem.release()

    @patch("wit.views.WitService.generate_stream")
    def test_guarded_generator_releases_slot_on_client_disconnect(
        self, mock_stream, monkeypatch
    ):
        mock_stream.return_value = iter([{"delta": "Hi"}, {"done": True}])
        sem = threading.BoundedSemaphore(1)
        monkeypatch.setattr(views, "_stream_semaphore", sem)
        assert sem.acquire(blocking=False)

        gen = views.BaseWitView._sse_events_guarded("say-no", None, None, None, None)
        next(gen)  # start streaming
        gen.close()  # client drops -> GeneratorExit -> finally releases the slot

        assert sem.acquire(blocking=False)
        sem.release()
