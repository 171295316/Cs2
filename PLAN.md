# CS2 Market Intelligence 可执行开发方案
日期：2026-10-19

## 1. 产品目标与范围
公开网站，提供 **CS2 所有可交易饰品** 的目录检索、从最早实际可取得记录开始的历史价格走势、全市场存世量/可观察供给分析。类别：枪皮（含磨损/StatTrak/纪念品）、刀、手套、武器箱、收藏包、贴纸、胶囊、探员、音乐盒、挂件、涂鸦、布章等。

用户所说「库存」专指市场存世量 Supply，**不是个人 Steam 库存**。MVP 不包含交易或 Steam 登录。中文默认、深色响应式。

## 2. 交付阶段
- **P0 工程初始化**：pnpm monorepo、Next.js + TypeScript + Tailwind、FastAPI + SQLAlchemy + Alembic、PostgreSQL 16、Redis、Docker Compose、.env.example、GitHub Actions、测试与运行文档。
- **P1 品类目录**：item/variant 模型、稳定 ID、来源映射、中英文名称、market_hash_name、图片、分类、搜索、分页、详情。研究 ByMykel/CSGO-API 开源数据及商业许可；许可不明不得直接商用分发。
- **P2 历史价格**：provider 接口、price_observations 入库、最早可用记录到最新记录、7D/30D/1Y/ALL 曲线、成交价/挂单价分隔、源/币种切换、数据缺口和更新日期。候选 cs2.sh Steam archive、Steam/其他授权平台；接入前核验最新授权、配额和字段。无 Key 时空数据状态。
- **P3 存世量**：supply_snapshots、批量导入（CSV/JSON）、来源证明和可观测口径、已记录独立物品数/样本库存数/在售数/有依据的总量估算，按日快照及趋势。不得把在售量称为总存世量，也不得反推没有历史快照的旧存世量。
- **P4 展示与上线**：首页、饰品搜索列表、详情图表、来源/方法页面、排行（仅有效样本参与）、性能/安全/接口测试，Compose 一键启动。

## 3. 事实与可信度要求
- 数据中「已发现独立物品实例数」不等于真实总存世量；public_inventory_units 是可见样本，listed_units 是在售数量，estimated_total_units 需要方法、区间与模型版本。
- 价格需标注交易成交/卖盘/买盘、市场、币种、时间粒度、原始起止日期；不可拼接不同价格口径形成假连续线。
- 没有数据 ≠ 数量为零；API 返回 status=unavailable，前端显示「暂无可核实数据」。
- Steam 数据归档最早日期不代表每件饰品从该日有数据；历史存世曲线只能来自有时间戳的可靠历史快照。
- 开发演示 fixture 必须与生产数据隔离，醒目标注，生产默认关闭。

## 4. 数据结构
- items(id UUID, canonical_key UNIQUE, category, name_zh, name_en, market_hash_name, image_url, attributes_json, tradable, marketable, updated_at)
- item_variants(id UUID, item_id FK, variant_key UNIQUE, wear nullable, stattrak nullable, souvenir nullable, paint_index nullable, attributes_json)
- data_sources(id, code UNIQUE, name, homepage, license_status, redistribution_allowed nullable, updated_at)
- source_item_mappings(id, item_id/variant_id, source_id, external_key, verified_at, UNIQUE(source_id,external_key))
- price_observations(id, item_id/variant_id, source_id, observed_at UTC, bucket_duration, price_kind [sale_median/ask_min/bid_max], currency, minor_units BIGINT, volume nullable, source_record_key, ingested_at; UNIQUE(source_id,source_record_key))
- supply_snapshots(id, item_id/variant_id, source_id, measured_at UTC, metric_type [observed_distinct_instances/public_inventory_units/listed_units/estimated_total_units], quantity BIGINT, methodology_version, coverage_note, sampling_method, confidence_low nullable, confidence_high nullable, source_record_key)
- import_jobs(id, provider, job_type, status, cursor, requested_at, started_at, completed_at, error_summary)

对观测时间、item/variant ID、数据源、唯一来源记录键加索引。金额使用整数最小币种单位，避免浮点误差。

## 5. API 规格 v1
- GET /healthz, /readyz
- GET /v1/items?query=&category=&sort=&cursor=&limit=
- GET /v1/items/{id}, GET /v1/items/{id}/variants
- GET /v1/items/{id}/prices?variant_id=&source=&price_kind=&from=&to=&resolution=&currency= → {status, series, earliest_available_at, latest_at, gaps, source, currency, price_kind}
- GET /v1/items/{id}/supply?variant_id=&metric_type=&from=&to= → {status, series, source, metric_definition, coverage, methodology, as_of}
- GET /v1/rankings?metric=&category=&limit=
- GET /v1/sources
- POST /internal/import/catalog, /internal/import/prices, /internal/import/supply（后台认证，不公开裸写）
OpenAPI /docs；分页、请求限制、输入验证、无数据状态和结构化日志。

## 6. UI 结构
- / ：搜索入口、类别、有效行情排行、数据方法提示
- /items ：中英文搜索、分类筛选、分页
- /items/[id] ：物品图、变体选择、最早可用价格曲线、来源标注、最高最低、价格与存世量并列、缺口/无数据说明
- /methodology ：口径定义、数据源、许可/局限、更新日期

## 7. 非功能性约束
- 服务端缓存、导入限速/退避重试、重入安全与幂等；不绕过验证码或平台限制。
- 不保存 Steam 密码；密钥仅放服务端环境变量，禁止提交 .env、密钥、个人隐私数据。
- 单测验证 price_kind 区分、源唯一约束、缺失数值不转 0、异常/空数据、CSV/JSON 导入幂等和 UI 空态。
- 文档必须写明 docker compose up --build、本地迁移、导入命令、测试命令、外部 Key 配置、真实覆盖局限。

## 8. 验收
- Compose 启动 API/Web/DB/Redis 成功，/healthz 与 /docs 可访问。
- 目录及分类/变体查询可用，支持合法来源填充所有可得类别。
- 详情页面支持 ALL 时间范围且仅展示真实时间序列；没有授权数据时明确提示。
- 存世量显示多个独立口径与来源/时间，不将 listed_units 当存世量。
- migrations、lint、typecheck、pytest 和至少一条端到端核心路径通过。

## 9. 待用户/商业决策
- 真实历史价格数据源 API 付费、缓存和二次展示许可。
- 浮点实例/公开库存样本数据的取得与商业使用许可；估计全量存世需有可校准依据。
- 域名、托管服务、费用上限。数据供应受限不应阻碍工程骨架、API、UI、空态开发。
