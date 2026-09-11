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

## Phase 4 features

Projects and cash-flow tracking are available to authenticated super admins, owners, and partners for viewing. Super admins and owners can create or update projects, assign active members, and record income or expenses.

Available API operations:

- `GET/POST /api/v1/projects` lists and creates projects.
- `PATCH /api/v1/projects/{project_id}` updates a project.
- `GET/POST/DELETE /api/v1/projects/{project_id}/members/{member_id}` manages project assignments.
- `GET/POST /api/v1/transactions` lists and records financial transactions.
- `GET /api/v1/finance/summary?year=YYYY&month=MM` returns monthly income, expenses, and net cash flow.

The Mini App includes the `Loyihalar` screen with project creation, monthly finance totals, and recent income entries.

## Phase 5 features

Monthly payroll can be finalized from attendance and the salary snapshot effective at the start of the month. Finalized payroll records can receive partial payments up to the earned amount. The monthly report combines income, expenses, payroll, and net profit.

Available API operations:

- `GET /api/v1/payroll?year=YYYY&month=MM` lists finalized payroll records.
- `POST /api/v1/payroll/finalize?year=YYYY&month=MM` creates or refreshes monthly payroll snapshots.
- `POST /api/v1/payroll/{payroll_id}/payments` records a payroll payment.
- `GET /api/v1/reports/monthly?year=YYYY&month=MM` returns the monthly financial report.

The Mini App includes the `Hisobotlar` screen with monthly totals and payroll finalization.

## Phase 6 features

Business mutations now create append-only audit events in the same transaction as the change. Audit history records the actor, action, entity, entity ID, timestamp, and structured details.

Available API operations:

- `GET /api/v1/audit` lists audit events for authorized users.
- `GET /api/v1/audit?entity_type=member&action=member.created&limit=100` filters audit events.

Audit history remains read-only through the API; audit rows are not updated or deleted by application services.

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
- Advanced audit export and retention policies remain planned for later phases.
- The application timezone defaults to `Asia/Tashkent`; database timestamps are timezone-aware UTC values.
- Profit distribution is still configured as 50/50 through environment settings and rejects any configuration that does not total 100%.
