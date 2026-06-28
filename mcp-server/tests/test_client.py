import httpx
import pytest
import respx

from snark_mcp.client import SnarkAPIError, SnarkClient

BASE = "http://localhost:8100"


def _client():
    return SnarkClient(base_url=BASE)


@respx.mock
async def test_wit_builds_url_and_returns_json():
    route = respx.get(f"{BASE}/v1/wit/hot-take/").mock(
        return_value=httpx.Response(
            200, json={"response": "Tabs win.", "persona": "The Hot Take Machine", "cached": False}
        )
    )
    data = await _client().wit("hot-take", q="tabs vs spaces", mood="spicy")
    assert data["response"] == "Tabs win."
    assert route.called
    sent = route.calls.last.request
    assert sent.url.params["q"] == "tabs vs spaces"
    assert sent.url.params["mood"] == "spicy"


@respx.mock
async def test_wit_omits_empty_params():
    route = respx.get(f"{BASE}/v1/wit/hot-take/").mock(
        return_value=httpx.Response(200, json={"response": "x", "persona": "p", "cached": False})
    )
    await _client().wit("hot-take")
    assert "q" not in route.calls.last.request.url.params
    assert "mood" not in route.calls.last.request.url.params


@respx.mock
async def test_roast_url_encodes_name():
    route = respx.get(f"{BASE}/v1/wit/roast/Ada%20Lovelace/").mock(
        return_value=httpx.Response(200, json={"response": "r", "persona": "p", "cached": False})
    )
    await _client().roast("Ada Lovelace")
    assert route.called


@respx.mock
async def test_roast_encodes_slash_in_name():
    route = respx.get(f"{BASE}/v1/wit/roast/a%2Fb/").mock(
        return_value=httpx.Response(200, json={"response": "r", "persona": "p", "cached": False})
    )
    await _client().roast("a/b")
    assert route.called
    assert "%2F" in str(route.calls.last.request.url)


@respx.mock
async def test_roast_github_uses_hyphenated_path():
    route = respx.get(f"{BASE}/v1/wit/roast-github/torvalds/").mock(
        return_value=httpx.Response(200, json={"response": "r", "persona": "p", "cached": False})
    )
    await _client().roast_github("torvalds")
    assert route.called


@respx.mock
async def test_worth_it_maps_thing_to_q():
    route = respx.get(f"{BASE}/v1/wit/worth-it/").mock(
        return_value=httpx.Response(
            200, json={"response": "VERDICT: NO", "persona": "The Decision Oracle", "cached": False}
        )
    )
    await _client().worth_it("a standing desk")
    assert route.calls.last.request.url.params["q"] == "a standing desk"


@respx.mock
async def test_reply_posts_body():
    route = respx.post(f"{BASE}/v1/wit/reply/").mock(
        return_value=httpx.Response(200, json={"response": "lol", "persona": "The Reply Guy", "cached": False})
    )
    await _client().reply("ship it on friday", mood="sarcastic")
    body = respx.calls.last.request.read()
    assert b"ship it on friday" in body
    assert b"sarcastic" in body
    assert route.called


@respx.mock
async def test_list_personas_returns_list():
    respx.get(f"{BASE}/v1/wit/personas/").mock(
        return_value=httpx.Response(200, json=[{"slug": "roast", "name": "The Friendly Roaster", "tone": "playful"}])
    )
    personas = await _client().list_personas()
    assert isinstance(personas, list)
    assert personas[0]["slug"] == "roast"


@respx.mock
async def test_error_response_raises_with_message():
    respx.get(f"{BASE}/v1/wit/roast/x/").mock(
        return_value=httpx.Response(404, json={"error": "Persona 'roast' not found", "code": "persona_not_found"})
    )
    with pytest.raises(SnarkAPIError) as exc:
        await _client().roast("x")
    assert "not found" in str(exc.value)


@respx.mock
async def test_network_error_raises_snark_api_error():
    respx.get(f"{BASE}/v1/wit/hot-take/").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(SnarkAPIError) as exc:
        await _client().wit("hot-take")
    assert "Could not reach" in str(exc.value)
