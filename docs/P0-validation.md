# P0 validation

- Python 3.12: pytest **5 passed**; Ruff and mypy passed.
- Alembic: SQLite upgrade head → downgrade base → upgrade head passed.
- Frontend: ESLint, TypeScript and Node test (1 passed); Next.js production compile passed.
- No Docker executable, PostgreSQL server or Redis server is installed in this execution environment. Compose startup and PostgreSQL/Redis integration are **not locally verified**. CI provisions PostgreSQL 16 and Redis 7 and exercises migrations; its result must be checked after push.
- No market data imported, no production provider enabled.
