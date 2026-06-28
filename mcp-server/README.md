# snark-mcp

An [MCP](https://modelcontextprotocol.io) server for the **Snark** humor API —
roasts, hot takes, honest commit messages, and more — usable from Claude Code,
Claude Desktop, Cursor, and any other MCP client.

It is a **thin client**: it makes no LLM calls and needs no database. Each tool
calls a running Snark REST API over HTTP and returns the result. All the
personas, prompts, caching, and the actual LLM call live in the Snark API — this
package just exposes a curated set of endpoints as MCP tools.

## Tools

| Tool | What it does |
|------|--------------|
| `snark_roast` | Roast a person by name |
| `snark_roast_github` | Roast a public GitHub profile |
| `snark_hot_take` | Spicy opinion on a topic |
| `snark_commit_message` | Honest git commit message |
| `snark_reply` | Sarcastic reply to a post |
| `snark_worth_it` | "Is it worth it?" verdict |
| `snark_wit` | Any persona by slug (use `snark_list_personas` to discover them) |
| `snark_list_personas` | List the available personas |

## Requirements

1. **A running Snark API.** The MCP server calls it over HTTP. Start one with the
   Docker stack from the repo root (`docker compose --profile dev up`) or point at
   any reachable instance.
2. **The server configured via `SNARK_API_URL`** — the base URL of that API
   (default `http://localhost:8100`). If your stack runs on another port (e.g.
   `WIT_PORT=8200` in `.env`), set `SNARK_API_URL` to match.

> **Not yet published to PyPI.** Until it is, install from source (below). Once
> published, the simplest form will be `uvx snark-mcp` with no clone needed.

## Install from source

From the repo root:

```bash
make mcp-install        # creates mcp-server/.venv and installs the package
```

or manually:

```bash
cd mcp-server
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

This gives you the `snark-mcp` executable at `mcp-server/.venv/bin/snark-mcp`,
which the client configs below point at. (Replace `/path/to/snark` with the
absolute path to your clone.)

## Connect a client

### Claude Code (CLI)

`claude mcp add` supports scopes, including **per-project** — the snark tools are
only active in this project and the config is private to you (not committed):

```bash
claude mcp add snark \
  -e SNARK_API_URL=http://localhost:8100 \
  -- /path/to/snark/mcp-server/.venv/bin/snark-mcp
```

- Default scope is `local` (this project, private). Use `-s project` to share via
  a committed `.mcp.json`, or `-s user` for all your projects.
- Verify with `claude mcp get snark`; remove with `claude mcp remove snark`.
- Restart the session to load the tools, then just ask naturally
  (*"roast the github user torvalds"*).

To skip per-call approval prompts, allow the server in
`.claude/settings.local.json` (gitignored):

```json
{ "permissions": { "allow": ["mcp__snark"] } }
```

### Claude Desktop

Claude Desktop is **global only** (no per-project scoping). Edit
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows), then fully restart Claude:

```json
{
  "mcpServers": {
    "snark": {
      "command": "/path/to/snark/mcp-server/.venv/bin/snark-mcp",
      "env": { "SNARK_API_URL": "http://localhost:8100" }
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` (project-scoped) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "snark": {
      "type": "stdio",
      "command": "/path/to/snark/mcp-server/.venv/bin/snark-mcp",
      "env": { "SNARK_API_URL": "http://localhost:8100" }
    }
  }
}
```

## Run it standalone

From the repo root, the Makefile wraps the common modes (`SNARK_API_URL` defaults
to `http://localhost:$(WIT_PORT)` from your `.env`, else `:8100`):

```bash
make mcp            # stdio (what MCP clients spawn; waits on stdin)
make mcp-http       # Streamable HTTP on MCP_PORT (default 8000) -> http://127.0.0.1:8000/mcp
make mcp-inspect    # open the MCP Inspector against a stdio server
make mcp-test       # run the test suite

# overrides:
make mcp-http SNARK_API_URL=http://localhost:8200 MCP_PORT=8001
```

Or directly:

```bash
SNARK_API_URL=http://localhost:8100 mcp-server/.venv/bin/snark-mcp            # stdio
SNARK_API_URL=http://localhost:8100 mcp-server/.venv/bin/snark-mcp --http     # Streamable HTTP
```

> A bare stdio launch just waits on stdin — that's normal; stdio servers are meant
> to be spawned by an MCP client. To poke at it by hand, use `make mcp-inspect`
> (Inspector UI) or `--http` plus a real JSON-RPC client. A plain browser GET to
> the HTTP endpoint returns `406 Not Acceptable` by design (MCP clients must send
> `Accept: text/event-stream`).

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SNARK_API_URL` | `http://localhost:8100` | Base URL of the Snark REST API |

## Testing

```bash
make mcp-test
# or
cd mcp-server && .venv/bin/pytest -v
```

The suite mocks the HTTP layer and uses FastMCP's in-memory client, so it needs no
running services.

## Design notes

- **Thin wrapper, read-only.** Every tool maps to a GET/POST generation endpoint;
  there are no write, delete, or admin tools.
- **Curated, not auto-generated.** ~8 high-value tools rather than one-per-endpoint,
  which keeps tool selection reliable for the model.
- **Errors and untrusted text.** API/network failures surface as a clean tool error;
  upstream humor text is returned in a labelled field and length-capped.
- **Transport.** stdio by default (local clients); `--http` serves Streamable HTTP
  for hosted use. SSE is deprecated and not used.
