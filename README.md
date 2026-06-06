# Acme Ltd — Financial Markets Data Warehouse

A temporal, NoSQL (MongoDB) data warehouse for financial-market data, with a REST
API, analytics, a web dashboard, and (next) an MCP-powered LLM assistant.

The key idea: records are **never updated or deleted in place**. Edits add a new
version, deletions add a marker, and every read accepts an `as_of` date so you can
see exactly what the warehouse held at any past moment. Different asset classes and
providers can carry different fields (stored as free-form `attributes` / `indicators`).

## Run it (local)

Needs Python 3.10+ and MongoDB running on `localhost:27017`.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (mac/linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m ingest.seed           # load sample data ("195 points appended")
uvicorn app.main:app --reload
```

Then open:
- http://localhost:8000/ — dashboard
- http://localhost:8000/docs — REST API (Q1–Q5)

## Run it (Docker, alternative)

```bash
docker compose up --build
docker compose exec api python -m ingest.seed
```
Same URLs, plus http://localhost:8081 (mongo-express, to view raw documents).

## Try the temporal model

On the dashboard, pick an asset and drag the **"viewing as of"** date back to
mid-2024: Tesla reappears (delisted 2024-09-01) and Apple's profile reverts to its
older version (edited 2024-06-01). Same effect in the API:

```
GET /assets                              # Tesla absent (deleted)
GET /assets?as_of=2024-08-01T00:00:00    # Tesla back
GET /assets/stock:US:AAPL?as_of=2024-03-01T00:00:00   # older description
```

## Tests

```bash
python -m pytest -q      # 13 tests, in-memory Mongo, no DB needed
```

## What's where

```
app/         config, MongoDB, models, temporal core, repository, FastAPI, dashboard
ingest/      data providers, ingestion runner, seed script
analytics/   trend / risk / forecast metrics (+ PySpark skeleton)
mcp_server/  MCP assistant: tools.py (logic) + server.py (FastMCP tools)
tests/       temporal + API + MCP + ingestion tests
```

## LLM assistant (MCP, UC4)

The warehouse is exposed as MCP tools (`list_assets`, `get_asset`, `list_sources`,
`get_source`, `get_time_series`, `summarize_trends`, `compare_assets`,
`explain_change`) so an LLM client can answer questions grounded only in stored
data. Each tool calls the tested Repository / analytics layer.

Run the server (Mongo must be running and seeded):

```bash
pip install mcp          # already in requirements.txt
python -m mcp_server.server
```

Connect it to **Claude Desktop** — edit its config
(`%APPDATA%\Claude\claude_desktop_config.json` on Windows;
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "acme-dwh": {
      "command": "D:\\Faculta\\DW\\acme-dwh\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "D:\\Faculta\\DW\\acme-dwh",
      "env": { "MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "acme_dwh" }
    }
  }
}
```

Restart Claude Desktop and ask e.g. *"Compare AAPL and BTC and explain which is
riskier."* For a quick visual demo of the tools without a chat client, use the
inspector: `pip install "mcp[cli]"` then `mcp dev mcp_server/server.py`.

## Requirement → code

| Requirement | Where |
|---|---|
| NoSQL store (mandatory) | MongoDB — `app/db.py` |
| Heterogeneous attributes | free-form dicts — `app/models.py` |
| Temporal, append-only | `app/temporal.py`, `app/repository.py` |
| Provenance / vendors (UC1) | `data_sources` + `source_id` on every record; `ingest/` |
| REST API Q1–Q5 (UC2) | `app/main.py` |
| Analytics / Spark (UC3) | `analytics/` + `/analytics` endpoint |
| Dashboard (usability) | `app/static/dashboard.html` |
| LLM via MCP (UC4) | `mcp_server/server.py` (8 tools + prompt, FastMCP) |

## Still to do

Promote analytics to PySpark (UC3), LangFlow bonus flow, report + demo video.

Here is the link to the video presentation:
https://drive.google.com/file/d/1nxfXMHXOTlOpXpBt0tAamTNbIMEUAdeg/view?usp=sharing
https://drive.google.com/file/d/1nxfXMHXOTlOpXpBt0tAamTNbIMEUAdeg/view?usp=sharing
