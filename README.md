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

## Deploy under a stack manager

`deploy/compose.yaml` is a variant for tools that manage compose stacks and inject variables as the stack's environment (Komodo, Portainer, etc.). It pulls the published image `ghcr.io/ptinkler/std-bot` rather than building locally. The bot only connects out to Discord, so no port or reverse proxy is needed.

| Variable | Required | Default |
|---|---|---|
| `DISCORD_TOKEN` | Yes | — |
| `STD_BOT_UID` | Yes | — |
| `STD_BOT_GID` | Yes | — |
| `STD_BOT_DATA_DIR` | Yes | — |
| `STD_BOT_VERSION` | No | `latest` |

`STD_BOT_DATA_DIR` is the host folder that holds `polls.db`. It must be owned by `STD_BOT_UID:STD_BOT_GID` and should be on local disk, not a network share.

## Environment variables

| Variable | Required | Default |
|---|---|---|
| `DISCORD_TOKEN` | Yes | — |
| `DB_PATH` | No | `/data/polls.db` |
| `BACKUP_INTERVAL_HOURS` | No | `24` (`0` = off) |
| `BACKUP_KEEP` | No | `7` |
| `BACKUP_DIR` | No | `backups/` beside the database |
| `UID` | No | `1000` |
| `GID` | No | `1000` |

## Data persistence

Polls are stored in a SQLite database. The `./data` directory is mounted to `/data` in the container — without this mount, all polls are lost on restart.

The bot also copies its database by itself: every `BACKUP_INTERVAL_HOURS` a consistent snapshot goes to `backups/` beside the database (`polls-<timestamp>.db`), and all but the newest `BACKUP_KEEP` are deleted. The copy is made with SQLite's `VACUUM INTO`, so it is safe while the bot is running. That guards against a bad migration or a deleted row, not a dead disk, so still copy the data directory elsewhere. To restore: stop the bot, copy a snapshot over `polls.db`, start it.

## Local development

```bash
pip install uv
uv sync
cp .env.example .env
# edit .env
.venv/bin/python main.py
```
