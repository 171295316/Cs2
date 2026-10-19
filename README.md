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
pnpm build
# 启动 API 后运行真实浏览器测试：pnpm test
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

## P1 目录迁移、来源与导入

`alembic upgrade head` 创建目录、变体、来源和映射。数据许可结论与限制见 [docs/data-sources.md](docs/data-sources.md)。生产默认空目录，未导入真实数据，不把未知值转换成 0。完整 JSON 导入格式见 [catalog.schema.json](docs/import/catalog.schema.json) 和 API `/docs`。

在核实真实数据集商业再分发权限后，于 `apps/api` 目录执行（以下参数应替换为实际依据）：

```bash
python -m app.admin --code SOURCE_CODE --name SOURCE_NAME \
  --homepage https://source.example --license-reference https://source.example/rights \
  --confirm-redistribution-rights
```

该命令显式记录人工许可审批，不会代替法律/资产权利核验。`.env` 内设置 `IMPORT_TOKEN` 后重启 API；token 仅放服务端。规范化数据 JSON 必须有 source_code、dataset_revision、evidence_url、verified_at（带时区）和 items，每个基础项/变体提供来源 external_key。核验时间不允许未来日期；不接受没有来源证据的导入。

```bash
# 此环境变量只在管理终端使用；不提交、不放 NEXT_PUBLIC_*。
curl --fail -X POST http://localhost:8000/internal/import/catalog \
  -H "Authorization: Bearer ${IMPORT_TOKEN}" -H 'Content-Type: application/json' \
  --data-binary @catalog-batch.json
```

ByMykel 离线适配（输入必须来自同一个已核实、已固定版本的实际文件；不自动下载）：

```bash
python -m app.bymykel --en skins_not_grouped.en.json --zh skins_not_grouped.zh.json \
  --category skin --revision ACTUAL_UPSTREAM_COMMIT \
  --verified-at ACTUAL_VERIFICATION_TIME_WITH_TIMEZONE \
  --evidence-url https://github.com/ByMykel/CSGO-API/blob/ACTUAL_UPSTREAM_COMMIT/public/api/en/skins_not_grouped.json \
  --out catalog-batch.json
```

中英文按源 ID 对齐。非枪皮文件按实际类别传入；不得混合分类。每批最多 1000 基础项且 2 MiB；大文件分批后分别提交。相同来源 external_key 不允许重新绑定，来源/版本冲突返回 409 并回滚整批。没有重试抓取或绕过平台限制的逻辑。

目录 API：`/v1/items?query=&category=&limit=&cursor=`，`/v1/items/{uuid}`，`/v1/items/{uuid}/variants`，`/v1/sources`。分页为稳定 ID 游标，不支持猜测的排名排序；改变筛选条件后从第一页重新开始。详情返回来源、核验时间、版本、证据链接。

端到端验证（先迁移并启动 API，然后生产构建 Web）：

```bash
pnpm build
pnpm --filter cs2-market-web exec playwright install --with-deps chromium
pnpm --filter cs2-market-web test:e2e
```

CI 验证 SQLite 单测、真实 PostgreSQL 迁移与事务、Redis readiness、浏览器核心路径，并另用 Docker Compose 构建启动全部服务。阶段结果见 docs/P0-validation.md 和 docs/P1-validation.md。P2–P4 为后续阶段，当前详情中的价格/供给面板保持无数据状态。

## P2 历史价格

迁移到 `0003` 后可使用 `/internal/import/prices` 提交规范化 JSON。先按 P1 导入真实来源映射，再以 `python -m app.admin ... --scope prices --confirm-redistribution-rights` 登记**该行情数据集**的明确二次展示许可；目录审批不代替行情审批。导入需要 Bearer token，格式见 `docs/import/prices.schema.json` 和 `/docs`。金额为严格整数最小货币单位（JPY 0 位、USD/CNY/EUR/GBP 2 位）；空价格不得用 0 填入，应不提交该观测。

查询 `/v1/items/{id}/prices` 支持 `variant_id/source/currency/price_kind/resolution/range/from/to`；range 为 7D/30D/1Y/ALL，resolution 是实际原始记录粒度，不做插值或将小时中位数平均成每日中位数。超过 20000 条要求缩小范围或选已有每日记录。来源、币种、口径、变体完全隔离；撤销专项授权立即隐藏该数据。

目前无已获许可的价格供应商，远程回填禁用。尤其 cs2.sh 普通条款限制另一个 API 的再分发，需专门许可；详见 docs/data-sources.md。图表只画实际记录；不从中位成交价生成虚构 OHLC。

## P3 供给快照

迁移到 `0004`，登记 `--scope supply` 的数据集专项再分发许可。使用相同 Bearer token：

```bash
curl --fail -X POST http://localhost:8000/internal/import/supply \
  -H "Authorization: Bearer ${IMPORT_TOKEN}" -H 'Content-Type: application/json' \
  --data-binary @supply-batch.json
curl --fail -X POST 'http://localhost:8000/internal/import/supply/csv?source_code=YOUR_APPROVED_SOURCE' \
  -H "Authorization: Bearer ${IMPORT_TOKEN}" -H 'Content-Type: text/csv' \
  --data-binary @verified-snapshots.csv
```

JSON 格式见 `docs/import/supply.schema.json`；CSV 表头见 `docs/import/supply-header.csv`（仅表头，无虚构示例值）。每条记录必须有既存来源 external_key、原始 UTC/带时区 measured_at、metric_type、quantity、methodology_version、coverage_note、sampling_method、evidence_url 和唯一 source_record_key。CSV 的数量列只接受非负整数，空 quantity 不合法；可选区间为空则表示未知。最多 1000 行/2 MiB。

`estimated_total_units` 另外必须提供 confidence_low、confidence_high、model_evidence_url；估算上下界必须包含 quantity。没有校准方法就不登记估算来源，也不导入该口径。公开样本、已发现实例、在售数均不得作为估算总量冒充。

`/v1/items/{id}/supply` 支持 variant_id、source、metric_type、methodology_version、range、from、to。不同版本不拼接；任意采样时间不推断成每天都有快照。撤销供给专项许可后，公开查询立即隐藏该源。
