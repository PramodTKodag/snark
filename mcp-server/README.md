# snark-mcp

An [MCP](https://modelcontextprotocol.io) server for the **Snark** humor API —
roasts, hot takes, honest commit messages, and more — for Claude Desktop,
Cursor, and other MCP clients.

It is a thin wrapper over the Snark REST API. Point it at a running Snark
instance with the `SNARK_API_URL` environment variable (default
`http://localhost:8100`).

## Tools

| Tool | What it does |
|------|--------------|
| `snark_roast` | Roast a person by name |
| `snark_roast_github` | Roast a GitHub profile |
| `snark_hot_take` | Spicy opinion on a topic |
| `snark_commit_message` | Honest git commit message |
| `snark_reply` | Sarcastic reply to a post |
| `snark_worth_it` | "Is it worth it?" verdict |
| `snark_wit` | Any persona by slug |
| `snark_list_personas` | Discover available personas |

## Install

Requires [uv](https://docs.astral.sh/uv/). `uvx` runs the server with no manual
install.

### Smoke test

```bash
SNARK_API_URL=http://localhost:8100 uvx snark-mcp
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows), then fully restart
Claude:

```json
{
  "mcpServers": {
    "snark": {
      "command": "uvx",
      "args": ["snark-mcp"],
      "env": { "SNARK_API_URL": "https://your-snark-instance.example.com" }
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "snark": {
      "type": "stdio",
      "command": "uvx",
      "args": ["snark-mcp"],
      "env": { "SNARK_API_URL": "https://your-snark-instance.example.com" }
    }
  }
}
```

## Hosted (Streamable HTTP)

```bash
uvx snark-mcp --http --host 0.0.0.0 --port 8000
```

## Development

```bash
cd mcp-server
pip install -e ".[dev]"
pytest -v
```
