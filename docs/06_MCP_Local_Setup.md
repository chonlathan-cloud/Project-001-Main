# Project-Local MCP Setup

This project keeps project-specific MCP servers in `.codex/config.toml` instead of the global `~/.codex/config.toml`.

## Stitch

The local Stitch MCP config expects this environment variable:

```bash
export STITCH_API_KEY="your-stitch-api-key"
```

The project-local config should use this shape:

```toml
[mcp_servers.stitch]
url = "https://stitch.googleapis.com/mcp"
env_http_headers = { "X-Goog-Api-Key" = "STITCH_API_KEY" }
default_tools_approval_mode = "prompt"
```

Do not commit real API keys, service account keys, or production credentials. Keep project MCPs out of the global Codex config unless they are safe for every workspace.
