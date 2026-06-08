---
name: backend-cloud-sql
description: Backend Cloud SQL workflow for Projects-001 FastAPI. Use when Codex needs to connect Projects-001-BE to Google Cloud SQL PostgreSQL, verify DATABASE_URL, start or stop Cloud SQL Auth Proxy, run safe read-only database checks, diagnose dashboard monthly cashflow source data, or start the backend against Cloud SQL without exposing secrets.
---

# Backend Cloud SQL

## Overview

Use this skill for backend database connectivity in `Projects-001-BE/`. The backend uses FastAPI, SQLAlchemy async, asyncpg, and `DATABASE_URL` from `Projects-001-BE/.env`.

Never print full connection strings, passwords, tokens, `.env` contents, service-account JSON, or signed URLs. Redact secrets in command output before showing the user.

## Boundaries

- Work primarily in `Projects-001-BE/` for backend checks and config.
- Do not change backend business logic unless the user explicitly asks.
- Do not edit `.env` unless the user explicitly provides the intended value or asks to update local config.
- Prefer read-only SQL while investigating. Ask before running writes, migrations, seed scripts, deletes, or destructive commands.

## Project Facts

- Backend env file: `Projects-001-BE/.env`
- Env example: `Projects-001-BE/.env.example`
- Config loader: `Projects-001-BE/app/core/config.py`
- Database engine: `Projects-001-BE/app/core/database.py`
- Expected backend URL scheme: `postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB`
- For `psql`, convert only the scheme to `postgresql://USER:PASSWORD@HOST:PORT/DB`
- Current Cloud SQL instance connection name for this project: `project001-489710:asia-southeast1:project-001`

## Connection Workflow

1. Confirm tools without exposing secrets:

```bash
command -v cloud-sql-proxy
command -v psql
command -v gcloud
```

2. Check whether port `5432` is already occupied:

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN
```

3. Start Cloud SQL Auth Proxy when no local listener exists:

```bash
cloud-sql-proxy --address 127.0.0.1 --port 5432 project001-489710:asia-southeast1:project-001
```

Keep the proxy running while testing the backend. Stop only the proxy process you started when finished.

## Safe Connection Test

Use the backend `.env` value without printing it:

```bash
python3 -c "import subprocess, sys; from dotenv import dotenv_values; raw=dotenv_values('Projects-001-BE/.env').get('DATABASE_URL') or ''; cli=raw.replace('postgresql+asyncpg://','postgresql://',1); assert raw, 'DATABASE_URL is missing'; result=subprocess.run(['psql','-X','--no-psqlrc','-v','ON_ERROR_STOP=1',cli,'-tAc','select current_database(), current_user'], capture_output=True, text=True); err=(result.stderr or '').replace(raw,'[DATABASE_URL]').replace(cli,'[DATABASE_URL]').strip(); print('database connection ok: '+(result.stdout or '').strip() if result.returncode == 0 else 'database connection failed: '+err); sys.exit(result.returncode)"
```

If `psql` is installed outside `PATH`, discover it with `command -v psql` and use that absolute path.

## Backend Runtime

Install dependencies only when needed and with user approval if network access is required:

```bash
cd Projects-001-BE
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

If Python dependency checks fail with `ModuleNotFoundError`, create or activate `.venv` before testing SQLAlchemy.

## Dashboard Cashflow Checks

The dashboard summary endpoint builds `monthly_cashflow` from:

- Income: `installments.amount` grouped by `installments.due_date`
- Expense: `transactions.base_amount` grouped by `transactions.approved_at`

Use read-only SQL to diagnose missing months:

```sql
with income as (
  select date_trunc('month', due_date)::date as month_start,
         count(*) as income_count,
         coalesce(sum(amount), 0) as income
  from installments
  where due_date is not null
  group by 1
),
expense as (
  select date_trunc('month', approved_at)::date as month_start,
         count(*) as expense_count,
         coalesce(sum(base_amount), 0) as expense
  from transactions
  where approved_at is not null
  group by 1
)
select to_char(coalesce(i.month_start, e.month_start), 'YYYY-MM') as month,
       coalesce(i.income_count, 0) as income_rows,
       coalesce(i.income, 0) as income,
       coalesce(e.expense_count, 0) as expense_rows,
       coalesce(e.expense, 0) as expense
from income i
full outer join expense e using (month_start)
order by coalesce(i.month_start, e.month_start);
```

If May or June is absent, the dashboard may show those months as zero after frontend display filling. That means there are no counted source rows for those months, not that real-world cashflow is confirmed zero.

## Cleanup

After starting local proxy or backend processes for a task, stop only processes started during the task. Verify ports are free:

```bash
lsof -nP -iTCP:5432 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
```
