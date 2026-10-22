---
name: setup-ai-tutor
description: Sets up and starts the Dynamous Agentic Coding course's AI Tutor sample project locally - env file, uv dependencies, Postgres via Docker, Alembic migrations, FastAPI dev server. Use only inside that sample repo, on first setup or a fresh clone; adapt or delete it in any other project.
---

# Set Up the AI Tutor Locally

Run the following commands to set up and start the AI Tutor locally. This skill is specific to the course's AI
Tutor sample project: if the repo you are in has no `pyproject.toml`, `alembic/`, or compose file with a `db`
service, you are in the wrong project - say so and stop.

## Input

None required. Run from the repository root.

## Process

### 0. Check Prerequisites

Stop with a clear message naming what is missing - do not start the steps below and fail halfway:

```bash
command -v uv >/dev/null || echo "MISSING: uv (https://docs.astral.sh/uv/)"
command -v docker >/dev/null || echo "MISSING: docker"
docker info >/dev/null 2>&1 || echo "Docker daemon is not running"
docker compose version >/dev/null 2>&1 || docker-compose version >/dev/null 2>&1 || echo "MISSING: docker compose"
```

Use `docker compose` (Compose v2+). Fall back to `docker-compose` only if that is the one installed; Compose v1
is unmaintained, so tell the user. Whichever one passed the check is `COMPOSE` below: use it for every compose
command in this skill (`docker compose up -d db` becomes `docker-compose up -d db`, and so on).

### 1. Create Environment File
```bash
test -f .env || cp .env.example .env
```
Creates your local environment configuration from the example template. Do not overwrite an existing `.env`, and
**never print, cat, or echo the contents of `.env`** - it holds credentials. If a value must be filled in, name
the key and tell the user to edit the file.

### 2. Install Dependencies
```bash
uv sync
```
Installs all Python packages defined in pyproject.toml.

### 3. Start Database
```bash
$COMPOSE up -d db        # COMPOSE is `docker compose` or `docker-compose`, from Step 0
```
Starts PostgreSQL in a Docker container. Wait until the container reports healthy (`$COMPOSE ps`) before
migrating; migrations against a database that is still booting fail with a connection error that looks like a
config problem.

### 4. Run Database Migrations
```bash
uv run alembic upgrade head
```
Applies all pending database migrations.

### 5. Start Development Server
```bash
uv run uvicorn app.main:app --reload --port 8123
```
Starts the FastAPI server with hot-reload on port 8123. This runs in the foreground; start it in a background
process (or a second terminal) so the validation step can run.

### 6. Validate Setup

Check that everything is working:

```bash
# Test API health
curl -s http://localhost:8123/health

# Test database connection
curl -s http://localhost:8123/health/db
```

Report what each actually returned. A healthy install answers `{"status":"healthy"}` on both; anything else is
a failed setup, not a warning.

## Output

A running local AI Tutor instance, plus a short summary of each step's result.

### Access Points

- Swagger UI: http://localhost:8123/docs
- Health Check: http://localhost:8123/health
- Database: localhost (Docker container)

## Cleanup

To stop services:
```bash
# Stop dev server: Ctrl+C
# Stop database: $COMPOSE down   (the command chosen in Step 0)
```

## Notes

- Port numbers and the exact compose service name may differ - check `compose.yaml` / `docker-compose.yml`,
  `.env.example`, and the project README for project-specific values before running.
