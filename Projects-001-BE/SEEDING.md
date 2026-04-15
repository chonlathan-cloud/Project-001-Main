# Round 1 Seeding

This backend now includes deterministic seed data for:

- Dashboard
- Projects / Project Detail / BOQ
- Bills admin list / edit / approve

## Files

- `scripts/seed_round1_data.py`
- `docker-compose.dev.yml`

## Dataset Shape

The seed creates:

- 4 projects
- nested BOQ trees with 3 WBS levels
- installments in `APPROVED`, `PENDING`, and `LOCKED`
- transactions for approved installments

Scenarios included:

- healthy active project
- risky active project with overdue bills
- active project with mixed MEP progress
- completed project with approved history

## Start Postgres

From `project_001_backend`:

```bash
docker compose -f docker-compose.dev.yml up -d
```

The compose file uses `pgvector/pgvector:pg16` so the `vector` extension is available for the BOQ schema.

## Run Seed

From `project_001_backend`:

```bash
./venv/bin/python scripts/seed_round1_data.py
```

What the script does:

1. loads `.env`
2. creates `vector` extension if needed
3. drops all existing tables
4. recreates schema
5. inserts the deterministic round 1 dataset
6. prints a summary

## Expected Coverage

After seeding, these endpoints should return real DB-backed data:

- `GET /api/v1/dashboard/summary`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `GET /api/v1/projects/{project_id}/boq`
- `GET /api/v1/bills/admin/bills?status=PENDING`
- `GET /api/v1/bills/admin/bills?status=APPROVED`

And these DB-backed bill actions should work against seeded records:

- `PUT /api/v1/bills/admin/bills/{bill_id}`
- `POST /api/v1/bills/admin/bills/{bill_id}/approve`

## Notes

- The seed is destructive by design because it resets the schema.
- `auth`, `settings`, and `chat` still have their own placeholder logic and are not covered by this seed round.
