# Stella MCP HTTP API Bridge

A local FastAPI facade over Stella's stdio MCP server. One MCP subprocess and
`ClientSession` are created during application lifespan and reused for every
request.

## Security

- `STELLA_API_TOKEN` enables bearer authentication on every `/v1/*` route.
- The token is optional only for loopback binds (`127.0.0.1`, `::1`, or
  `localhost`). Startup fails if `STELLA_API_HOST` is non-loopback and no token
  is configured.
- `/health` is intentionally unauthenticated for process/container probes and
  returns no Stella data.
- State mutation, raw Cypher, chart memory, and autopoietic tools are excluded
  by an explicit denylist and return HTTP 403.
- Do not put tokens in command history or source control. Supply them through a
  secret manager or protected environment file.

## Local setup

From `clawd/stella/api_bridge`:

```bash
../.venv/bin/pip install -r requirements.txt
STELLA_API_HOST=127.0.0.1 ../.venv/bin/python app.py
```

The service listens on `http://127.0.0.1:3010` by default. For a non-loopback
bind, set both variables before startup:

```bash
STELLA_API_HOST=0.0.0.0 STELLA_API_TOKEN='set-via-secret-manager' \
  ../.venv/bin/python app.py
```

Optional settings:

| Variable | Default | Purpose |
|---|---|---|
| `STELLA_API_HOST` | `127.0.0.1` | Uvicorn bind host |
| `STELLA_API_PORT` | `3010` | Uvicorn bind port |
| `STELLA_API_TOKEN` | unset | Bearer token; mandatory off loopback |
| `STELLA_MCP_PYTHON` | `../.venv/bin/python` | MCP subprocess interpreter |
| `STELLA_MCP_SERVER` | `../stella_server.py` | Stella MCP server path |
| `STELLA_LOG_LEVEL` | `info` | Uvicorn log level |

## API

- `GET /health` — process/MCP connection status (public).
- `GET /v1/tools` — allowed MCP tool metadata.
- `POST /v1/tools/{name}` — call an allowed tool. The JSON request body is
  passed as MCP tool arguments.
- `GET /v1/snapshot` — concurrently requests the current Moon, planet
  positions, aspects, and dignities. Successful values are under `data`;
  individual failures are under `errors`, with `partial: true`.

Example:

```bash
curl -H "Authorization: Bearer $STELLA_API_TOKEN" \
  http://127.0.0.1:3010/v1/snapshot

curl -X POST \
  -H "Authorization: Bearer $STELLA_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{}' http://127.0.0.1:3010/v1/tools/get_current_moon
```

MCP text blocks containing valid JSON are decoded to native JSON. MCP
`structuredContent` is returned directly. Other MCP block types are serialized
to JSON-compatible objects.

## Tests

```bash
../.venv/bin/python -m pytest -q tests
```

Tests use a mocked gateway and never launch Stella or access chart data.

## Docker

Build with the Stella directory as context (not `api_bridge`):

```bash
docker build -f api_bridge/Dockerfile -t stella-api .
docker run --rm -p 3010:3010 \
  -e STELLA_API_TOKEN='set-via-secret-manager' stella-api
```

The image copies only Stella code and public reference datasets; it does not
copy `charts/`, chart memories, credentials, or the local virtual environment.
A token is mandatory because the image binds to `0.0.0.0`.
