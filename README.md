# Hisobchi

Hisobchi is an MVP for attendance, payroll, project cash flow, expenses, and monthly profit reporting for a small family business.

## Local setup

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

The first super admin is identified by `SUPER_ADMIN_TELEGRAM_ID`. Other Telegram accounts must first be linked to a member by an administrator.

## Phase 2 features

Member management is available under `/api/v1/members` for authenticated super admins and owners. Partners can view member records; workers cannot manage or browse the member directory.

Available operations include:

- Create, list, filter, update, and deactivate members.
- Link or unlink a Telegram account using its numeric Telegram user ID.
- Create salary history for workers using integer UZS amounts.
- Automatically close an open salary period when a later salary begins.
- View historical salary periods; owners and partners cannot receive fixed salaries.

The Mini App includes the `A’zolar` screen with active/inactive filters, member forms, Telegram link state, salary history, and salary changes.

## Phase 3 features

Attendance is tracked per worker on a daily basis using integer half-day units, where `0` is absent, `1` is half-day, and `2` is full-day. The attendance model and service enforce active membership rules and reject attendance outside a member’s valid employment window.

Available API operations:

- `GET /api/v1/members/{member_id}/attendance` lists daily attendance records.
- `POST /api/v1/members/{member_id}/attendance` creates or updates a day’s attendance entry.
- `GET /api/v1/members/{member_id}/attendance/summary?year=YYYY&month=MM` returns the monthly total in half-day units and the estimated accrued salary for the active salary period.

The Mini App now includes the `Davomat` screen with per-worker daily attendance entry and a monthly summary.

## Tests and checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
cd frontend && npm run build
```

## Current limitations

- PostgreSQL is the runtime database; SQLite is used only for fast unit tests.
- Telegram Mini App `initData` is validated server-side with the bot token and produces a short-lived JWT.
- Attendance, projects, financial transactions, payroll finalization, reports, and audit history remain planned for later phases.
- The application timezone defaults to `Asia/Tashkent`; database timestamps are timezone-aware UTC values.
- Profit distribution is still configured as 50/50 through environment settings and rejects any configuration that does not total 100%.
