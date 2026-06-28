from fastmcp import Client

import snark_mcp.server as server
from snark_mcp.config import MAX_RESPONSE_CHARS


def test_format_truncates_long_text():
    long = "x" * (MAX_RESPONSE_CHARS + 500)
    out = server._format({"response": long, "persona": "p"})
    assert len(out["response"]) == MAX_RESPONSE_CHARS


def test_format_handles_missing_fields():
    out = server._format({})
    assert out["response"] == ""
    assert out["persona"] == "snark"


async def test_surface_is_read_only_and_named():
    async with Client(server.mcp) as client:
        tools = await client.list_tools()
    names = {t.name for t in tools}
    # Every tool is a snark_ generation/discovery tool; nothing writes/deletes.
    assert all(n.startswith("snark_") for n in names)
    assert not any(
        bad in n for n in names for bad in ("delete", "create", "update", "admin", "seed")
    )
    assert len(names) == 9
