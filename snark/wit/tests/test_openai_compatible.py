import json
import logging

import httpx2
import pytest
from wit.providers.base import (
    AIResponse,
    ContentFilterError,
    ProviderError,
    StreamUsage,
    safe_error_summary,
)
from wit.providers.config import ProviderSpec, ProviderType
from wit.providers.openai_compatible import OpenAICompatibleProvider

API_KEY = "sk-test-SECRET-1234567890"
URL = "https://llm.example.test/v1"


def make_spec(**overrides) -> ProviderSpec:
    fields = {
        "name": "testllm",
        "type": ProviderType.OPENAI_COMPATIBLE,
        "model": "test/model",
        "key_env": "TESTLLM_API_KEY",
        "url": URL,
        "extra_body": {"reasoning_effort": "low", "options": {"think": False}},
    }
    fields.update(overrides)
    return ProviderSpec(**fields)


def completion(content="hello", finish_reason="stop", usage=True, choices=True):
    body = {
        "id": "cmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "test/model",
        "choices": [],
    }
    if choices:
        body["choices"] = [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content},
            }
        ]
    if usage:
        body["usage"] = {
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
        }
    return httpx2.Response(200, json=body)


def sse(*events) -> httpx2.Response:
    payload = "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"
    return httpx2.Response(
        200, content=payload.encode(), headers={"content-type": "text/event-stream"}
    )


def delta_chunk(text=None, finish_reason=None):
    return {
        "id": "c",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "test/model",
        "choices": [
            {"index": 0, "delta": {"content": text}, "finish_reason": finish_reason}
        ],
    }


USAGE_CHUNK = {
    "id": "c",
    "object": "chat.completion.chunk",
    "created": 1,
    "model": "test/model",
    "choices": [],
    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
}


class Wire:
    """Replaces the SDK's HTTP transport: records requests, replays responses."""

    def __init__(self):
        self.requests: list[httpx2.Request] = []
        self.responses: list[httpx2.Response] = []

    def reply(self, *responses):
        self.responses.extend(responses)

    def handle(self, request):
        self.requests.append(request)
        return self.responses.pop(0)

    def json_body(self, index=-1):
        return json.loads(self.requests[index].content)


@pytest.fixture
def wire(monkeypatch):
    fake = Wire()
    monkeypatch.setattr(
        httpx2.HTTPTransport,
        "handle_request",
        lambda transport, request: fake.handle(request),
    )
    return fake


def provider(spec=None, api_key=API_KEY) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(spec or make_spec(), api_key)


class TestGenerate:
    def test_returns_text_usage_and_identity(self, wire):
        wire.reply(completion("hi there"))

        result = provider().generate("sys", "usr", temperature=0.5, max_tokens=33)

        assert isinstance(result, AIResponse)
        assert result.text == "hi there"
        assert result.provider == "testllm"
        assert result.model == "test/model"
        assert (result.input_tokens, result.output_tokens) == (11, 7)
        assert result.tokens_used == 18
        body = wire.json_body()
        assert body["model"] == "test/model"
        assert body["max_tokens"] == 33
        assert body["temperature"] == 0.5
        assert body["messages"] == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
        ]
        assert str(wire.requests[0].url) == f"{URL}/chat/completions"

    def test_missing_usage_counts_as_zero(self, wire):
        wire.reply(completion(usage=False))
        result = provider().generate("s", "u")
        assert (result.input_tokens, result.output_tokens, result.tokens_used) == (
            0,
            0,
            0,
        )

    def test_extra_body_is_sent_and_not_mutated(self, wire):
        spec = make_spec()
        wire.reply(completion(), completion())
        llm = provider(spec)

        llm.generate("s", "u")
        llm.generate("s", "u")

        for index in (0, 1):
            body = wire.json_body(index)
            assert body["reasoning_effort"] == "low"
            assert body["options"] == {"think": False}
        assert spec.extra_body == {
            "reasoning_effort": "low",
            "options": {"think": False},
        }

    def test_content_filter_raises(self, wire):
        wire.reply(completion(content="", finish_reason="content_filter"))
        with pytest.raises(ContentFilterError):
            provider().generate("s", "u")

    @pytest.mark.parametrize("content", [None, ""])
    def test_empty_content_raises_provider_error(self, wire, content):
        wire.reply(completion(content=content))
        with pytest.raises(ProviderError) as excinfo:
            provider().generate("s", "u")
        assert not isinstance(excinfo.value, ContentFilterError)

    def test_no_choices_raises_provider_error(self, wire):
        wire.reply(completion(choices=False))
        with pytest.raises(ProviderError):
            provider().generate("s", "u")


class TestStream:
    def test_yields_deltas_then_usage_and_requests_usage(self, wire):
        wire.reply(
            sse(
                delta_chunk("No"),
                delta_chunk(" thanks"),
                delta_chunk(None, "stop"),
                USAGE_CHUNK,
            )
        )

        items = list(provider().generate_stream("s", "u", max_tokens=40))

        assert items[:2] == ["No", " thanks"]
        assert items[2] == StreamUsage(input_tokens=5, output_tokens=3)
        assert len(items) == 3
        body = wire.json_body()
        assert body["stream"] is True
        assert body["stream_options"] == {"include_usage": True}
        assert body["max_tokens"] == 40
        assert body["reasoning_effort"] == "low"

    def test_content_filter_raises(self, wire):
        wire.reply(sse(delta_chunk("par"), delta_chunk(None, "content_filter")))
        stream = provider().generate_stream("s", "u")
        assert next(stream) == "par"
        with pytest.raises(ContentFilterError):
            next(stream)

    def test_empty_stream_raises_provider_error(self, wire):
        wire.reply(sse(USAGE_CHUNK))
        with pytest.raises(ProviderError):
            list(provider().generate_stream("s", "u"))

    def test_stream_with_only_empty_deltas_raises(self, wire):
        wire.reply(sse(delta_chunk(None), delta_chunk(""), USAGE_CHUNK))
        with pytest.raises(ProviderError):
            list(provider().generate_stream("s", "u"))

    def test_http_error_raises_provider_error(self, wire):
        wire.reply(httpx2.Response(400, json={"error": {"message": "bad"}}))
        with pytest.raises(ProviderError):
            list(provider().generate_stream("s", "u"))


class TestAvailability:
    def test_unavailable_when_declared_key_is_empty(self, wire):
        llm = provider(api_key="")

        assert llm.is_available() is False
        assert llm.health_check() is False
        with pytest.raises(ProviderError, match=r"no API key \(set TESTLLM_API_KEY\)"):
            llm.generate("s", "u")
        with pytest.raises(ProviderError, match=r"no API key \(set TESTLLM_API_KEY\)"):
            list(llm.generate_stream("s", "u"))
        assert wire.requests == []

    def test_keyless_provider_is_available(self, wire):
        wire.reply(completion())
        llm = provider(
            make_spec(key_env=None, url="http://localhost:11434/v1"), api_key=""
        )

        assert llm.is_available() is True
        assert llm.generate("s", "u").text == "hello"
        assert wire.requests[0].headers["authorization"] == "Bearer keyless"

    def test_health_check(self, wire):
        wire.reply(completion(), httpx2.Response(400, json={"error": {"message": "x"}}))
        llm = provider()
        assert llm.health_check() is True
        assert llm.health_check() is False


class TestErrorHandling:
    def test_auth_error_omits_body_and_key(self, wire, caplog):
        wire.reply(
            httpx2.Response(
                401, json={"error": {"message": f"Incorrect API key: {API_KEY}"}}
            )
        )
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ProviderError) as excinfo:
                provider().generate("s", "u")

        message = str(excinfo.value)
        assert "AuthenticationError" in message and "401" in message
        assert "Incorrect API key" not in message
        assert API_KEY not in message
        assert excinfo.value.__cause__ is None
        assert excinfo.value.__suppress_context__ is True
        assert API_KEY not in caplog.text

    def test_other_errors_scrub_the_key(self, wire, caplog):
        wire.reply(
            httpx2.Response(
                400, json={"error": {"message": f"bad request near {API_KEY} here"}}
            )
        )
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ProviderError) as excinfo:
                provider().generate("s", "u")

        message = str(excinfo.value)
        assert "bad request near ***" in message
        assert API_KEY not in message
        assert API_KEY not in caplog.text

    def test_stream_errors_scrub_the_key(self, wire):
        wire.reply(httpx2.Response(400, json={"error": {"message": f"echo {API_KEY}"}}))
        with pytest.raises(ProviderError) as excinfo:
            list(provider().generate_stream("s", "u"))
        assert API_KEY not in str(excinfo.value)
        assert "***" in str(excinfo.value)


class TestSafeErrorSummary:
    class _StatusError(Exception):
        def __init__(self, message, status_code):
            super().__init__(message)
            self.status_code = status_code

    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_statuses_drop_the_message(self, status):
        summary = safe_error_summary(
            self._StatusError("leaks secret", status), ["secret"]
        )
        assert summary == f"_StatusError (status {status})"

    def test_other_statuses_scrub_every_secret(self):
        exc = self._StatusError("a one-secret b two-secret c", 500)
        summary = safe_error_summary(exc, ["one-secret", "two-secret", ""])
        assert summary == "_StatusError (status 500): a *** b *** c"

    def test_message_without_status(self):
        assert safe_error_summary(ValueError("boom"), []) == "ValueError: boom"

    def test_truncates_after_scrubbing(self):
        summary = safe_error_summary(ValueError("x" * 1000), [])
        assert len(summary) == 300


class TestNoAmbientEnvironment:
    def test_env_credentials_url_and_headers_do_not_reach_the_wire(
        self, wire, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-ENV-KEY")
        monkeypatch.setenv("OPENAI_ORG_ID", "org-env")
        monkeypatch.setenv("OPENAI_PROJECT_ID", "proj-env")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://env.example.test/v1")
        monkeypatch.setenv("OPENAI_ADMIN_KEY", "sk-ENV-ADMIN")
        monkeypatch.setenv(
            "OPENAI_CUSTOM_HEADERS", "Authorization: Bearer sk-ENV-HEADER"
        )
        wire.reply(completion())

        provider().generate("s", "u")

        request = wire.requests[0]
        assert request.url.host == "llm.example.test"
        assert request.headers["authorization"] == f"Bearer {API_KEY}"
        assert "openai-organization" not in request.headers
        assert "openai-project" not in request.headers
        assert b"sk-ENV-KEY" not in request.content
        assert "sk-ENV" not in str(request.headers)

    def test_keyless_ignores_env_api_key(self, wire, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-ENV-KEY")
        wire.reply(completion())

        provider(make_spec(key_env=None), api_key="").generate("s", "u")

        assert "sk-ENV-KEY" not in wire.requests[0].headers["authorization"]

    def test_redirect_is_not_followed(self, wire):
        wire.reply(
            httpx2.Response(
                307, headers={"location": "https://attacker.example.test/steal"}
            ),
            completion(),
        )

        with pytest.raises(ProviderError):
            provider().generate("s", "u")

        assert [r.url.host for r in wire.requests] == ["llm.example.test"]
