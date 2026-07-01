"""drf-spectacular schema post-processing.

The wit endpoints carry an ``EventStreamRenderer`` (media type
``text/event-stream``) purely so DRF content negotiation accepts real SSE
clients for ``?stream=true`` — the streaming view returns a
``StreamingHttpResponse`` directly and never renders through DRF. It is not a
normal JSON response, so it must not appear in the OpenAPI schema: otherwise
Swagger's "Try it out" offers ``text/event-stream``, sends
``Accept: text/event-stream`` on a non-streaming request, and gets either
malformed output or a 406. Streaming stays documented via the ``stream`` query
parameter.
"""


def remove_event_stream_media_type(result, generator, request, public):
    """Strip ``text/event-stream`` from every documented request/response body."""
    for path_item in result.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            bodies = list(operation.get("responses", {}).values())
            request_body = operation.get("requestBody")
            if request_body:
                bodies.append(request_body)
            for body in bodies:
                content = body.get("content") if isinstance(body, dict) else None
                if content:
                    content.pop("text/event-stream", None)
            # Also drop it from the auto-generated ?format= parameter enum, so
            # the docs never offer ?format=event-stream either.
            for parameter in operation.get("parameters", []):
                enum = (parameter.get("schema") or {}).get("enum")
                if enum and "event-stream" in enum:
                    enum[:] = [value for value in enum if value != "event-stream"]
    return result
