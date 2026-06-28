from fastmcp import Client

import snark_mcp.server as server


async def test_lists_exactly_the_eight_tools():
    async with Client(server.mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "snark_roast",
        "snark_roast_github",
        "snark_hot_take",
        "snark_commit_message",
        "snark_reply",
        "snark_worth_it",
        "snark_wit",
        "snark_list_personas",
    }


async def test_snark_roast_returns_formatted_dict(fake_client):
    async with Client(server.mcp) as client:
        result = await client.call_tool("snark_roast", {"name": "Dave", "mood": "spicy"})
    assert result.data["response"] == "roast of Dave"
    assert result.data["persona"] == "The Friendly Roaster"
    assert ("roast", "Dave", "spicy") in fake_client.calls


async def test_snark_hot_take_maps_topic_to_q(fake_client):
    async with Client(server.mcp) as client:
        result = await client.call_tool("snark_hot_take", {"topic": "tabs vs spaces"})
    assert result.data["response"] == "wit:hot-take:tabs vs spaces"
    assert fake_client.calls[-1][:3] == ("wit", "hot-take", "tabs vs spaces")


async def test_snark_commit_message_uses_commit_message_persona(fake_client):
    async with Client(server.mcp) as client:
        await client.call_tool("snark_commit_message", {"change": "fixed the thing"})
    assert fake_client.calls[-1][:3] == ("wit", "commit-message", "fixed the thing")


async def test_snark_reply_calls_reply(fake_client):
    async with Client(server.mcp) as client:
        result = await client.call_tool("snark_reply", {"post": "ship friday"})
    assert result.data["response"] == "reply to ship friday"


async def test_snark_worth_it_calls_worth_it(fake_client):
    async with Client(server.mcp) as client:
        result = await client.call_tool("snark_worth_it", {"thing": "a standing desk"})
    assert "VERDICT" in result.data["response"]


async def test_snark_wit_passes_persona_and_query(fake_client):
    async with Client(server.mcp) as client:
        await client.call_tool("snark_wit", {"persona": "proverb", "q": "deadlines"})
    assert fake_client.calls[-1][:3] == ("wit", "proverb", "deadlines")


async def test_snark_list_personas_returns_list(fake_client):
    async with Client(server.mcp) as client:
        result = await client.call_tool("snark_list_personas", {})
    assert isinstance(result.data, list)
    assert result.data[0]["slug"] == "roast"


async def test_tool_error_is_surfaced(error_client):
    async with Client(server.mcp) as client:
        result = await client.call_tool("snark_roast", {"name": "x"}, raise_on_error=False)
    assert result.is_error
    assert "temporarily unavailable" in str(result.content)
