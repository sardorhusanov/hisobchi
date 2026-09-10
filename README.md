# Hisobchi

Hisobchi is an MVP for attendance, payroll, project cash flow, expenses, and monthly profit reporting for a small family business.

## Phase 1 setup

Requirements: Python 3.12+, `uv`, Node.js 20+, npm, and Docker.

```bash
cp .env.example .env
uv sync --dev
docker compose up -d postgres
uv run alembic upgrade head
uv run uvicorn app.main:app --app-dir backend --reload
```

In another terminal, run the bot after setting `BOT_TOKEN` in `.env`:

```bash
uv run python -m app.bot.runner
```

Run the Mini App:

```bash
cd frontend
npm install
npm run dev
```

API docs are available at `http://localhost:8000/docs`; health check is `http://localhost:8000/health`.

## Tests and checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
cd frontend && npm run build
```

## Phase 1 assumptions

- PostgreSQL is the runtime database; SQLite is used only for fast unit tests.
- Telegram Mini App `initData` is validated server-side with the bot token and produces a short-lived JWT.
- The initial schema is migration-driven and includes the core entities, but feature workflows are intentionally reserved for later phases.
- The application timezone defaults to `Asia/Tashkent`; database timestamps are timezone-aware UTC values.
- Profit distribution is configured as 50/50 and rejects any configuration that does not total 100%.
