# std-bot

Discord bot for scheduling events via availability polls. Use `/std` to create a poll, let people vote on dates, then finalize to create a Discord scheduled event.

## Deploy with Docker Compose

```bash
cp .env.example .env
# edit .env — set DISCORD_TOKEN, UID, GID
docker compose up -d
```

Get your UID/GID:
```bash
id -u && id -g
```

Logs:
```bash
docker compose logs -f
```

## Environment variables

| Variable | Required | Default |
|---|---|---|
| `DISCORD_TOKEN` | Yes | — |
| `DB_PATH` | No | `/data/polls.db` |
| `UID` | No | `1000` |
| `GID` | No | `1000` |

## Data persistence

Polls are stored in a SQLite database. The `./data` directory is mounted to `/data` in the container — without this mount, all polls are lost on restart.

## Local development

```bash
pip install uv
uv sync
cp .env.example .env
# edit .env
.venv/bin/python main.py
```
