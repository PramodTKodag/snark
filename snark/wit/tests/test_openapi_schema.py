import json

import pytest
from base.schema import remove_event_stream_media_type
from rest_framework.test import APIClient


def test_hook_strips_event_stream_keeps_json():
    result = {
        "paths": {
            "/v1/wit/hot-take/": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {"schema": {}},
                                "text/event-stream": {"schema": {}},
                            }
                        }
                    }
                }
            }
        }
    }
    out = remove_event_stream_media_type(result, None, None, True)
    content = out["paths"]["/v1/wit/hot-take/"]["get"]["responses"]["200"]["content"]
    assert "text/event-stream" not in content
    assert "application/json" in content


@pytest.mark.django_db
def test_openapi_schema_excludes_event_stream():
    resp = APIClient().get("/v1/wit/schema/", {"format": "json"})
    assert resp.status_code == 200
    schema = json.loads(resp.content)

    json_response_seen = False
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            # No response/request body advertises the SSE shim media type.
            bodies = list(operation.get("responses", {}).values())
            if operation.get("requestBody"):
                bodies.append(operation["requestBody"])
            for body in bodies:
                content = body.get("content") or {}
                assert "text/event-stream" not in content
                if "application/json" in content:
                    json_response_seen = True
            # No parameter enum (e.g. ?format=) offers event-stream.
            for parameter in operation.get("parameters", []):
                enum = (parameter.get("schema") or {}).get("enum") or []
                assert "event-stream" not in enum

    # Sanity: normal JSON responses are still documented.
    assert json_response_seen
