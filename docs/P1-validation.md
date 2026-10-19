# P1 validation

## Implementation

- `app/models.py`, Alembic `0002`: catalog, variants, sources, provenance mapping, foreign keys and unique source keys.
- `app/catalog.py`, `routes.py`, `admin.py`, `bymykel.py`: deterministic UUIDs, authorized atomic/idempotent import, offline adapter, bilingual search, scoped keyset pagination, details and provenance.
- Web catalog, classification, pagination and item/variant details connect to the actual API. Upstream failure and valid empty response have separate messages.
- License findings and coverage restrictions in `data-sources.md`; JSON import schema in `import/catalog.schema.json`.

## Local checks

- Python pytest: **19 passed, 1 skipped** (PostgreSQL integration requires a PostgreSQL server), one upstream Starlette TestClient deprecation warning.
- SQLite Alembic `upgrade head → downgrade base → upgrade head`: passed, now at `0002`.
- Ruff, mypy, ESLint, TypeScript, Node test (1 passed), Next.js production build: passed.
- Playwright core path added; execution result will be recorded from CI. The initial local browser download failed due to a truncated archive; no browser pass is claimed here.
- Local Docker/PostgreSQL/Redis are unavailable. CI runs PostgreSQL migrations/transaction rollback, readiness, browser tests, plus a separate full Compose build/start job.

## Verified prior stage

P0 GitHub Actions passed: https://github.com/171295316/Cs2/actions/runs/39235261454

## Data and scope

No real catalog has been imported. No market prices or supply quantities have been fabricated or seeded. Production sources remain unapproved/empty until their actual dataset redistribution rights are established. Synthetic records exist only in test files. P2–P4 (#3–#5) remain subsequent stages; do not interpret empty price/supply panels as those stages being implemented.
