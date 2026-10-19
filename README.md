# CS2 Market Intelligence

CS2 全品类饰品历史价格与全市场存世量分析平台。

> 存世量指全市场供应情况，不是用户 Steam 个人库存。真实总存世量通常不可直接观测。

## 项目范围
- 枪皮、刀、手套、武器箱、贴纸、胶囊、探员、音乐盒、挂件、涂鸦等全品类目录。
- 每件饰品展示**最早实际可获取**至今的历史成交价格；不同来源、币种、价格口径分别显示。
- 分别统计已识别独立实例数、公开库存样本数、平台在售数量、在条件满足时的估算总量。
- 数据必须标识来源、时间、方法及缺失区间。缺少可授权数据时显示 unavailable，不使用伪造数字。

## 建议架构
- Web: Next.js + TypeScript + Tailwind + Lightweight Charts
- API: FastAPI + Python + SQLAlchemy + Alembic
- DB: PostgreSQL；Redis 缓存/队列；Docker Compose 本地启动。

## Codex 入口
请先阅读 [AGENTS.md](AGENTS.md)、[PLAN.md](PLAN.md)、[CODEX_START.md](CODEX_START.md)。开发按照 P0→P4 阶段执行，并提交测试结果。暂不实现自动交易。

## 安全与授权
第三方 API 调用、历史批量回填、数据缓存和再分发必须符合来源许可。不要提交任何 token、API key 或 Steam 密码。生产禁止演示数据冒充真实行情。

## 本地运行（P0）
要求 Docker Compose v2，或 Node 22 + pnpm 11、Python 3.12、PostgreSQL 16、Redis 7。

```bash
cp .env.example .env
# 在 .env 中设置随机 POSTGRES_PASSWORD 和 IMPORT_TOKEN（例如 openssl rand -hex 32）
docker compose up --build
# Web http://localhost:3000，API http://localhost:8000/docs
# 就绪检查 http://localhost:8000/readyz；存活检查 /healthz
docker compose exec api alembic current
```

数据库保存在命名卷中。API 启动前自动执行迁移；生产请在单独发布任务中执行迁移，并先备份数据库。不要并行启动多个迁移进程。worker 目前仅发送心跳；未经授权的数据抓取默认关闭。

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm --filter cs2-market-web dev
python -m venv .venv
. .venv/bin/activate
pip install -r apps/api/requirements-dev.txt
# 设置 DATABASE_URL、REDIS_URL 指向本地服务；宿主开发需自行开放 DB/Redis 端口
cd apps/api
alembic upgrade head
python -m pytest -q
uvicorn app.main:app --reload
# 另一个终端在仓库根目录
ruff check --config apps/api/pyproject.toml apps/api apps/worker
mypy apps/api/app
```

不配置 DATABASE_URL 时仅用于本地 SQLite 工程验证，不代表已验证 PostgreSQL。CI 使用 PostgreSQL 16 做升级、回滚再升级测试。`/readyz` 在 DB、迁移表或 Redis 不可用时返回 503，错误细节不向客户端泄漏。
