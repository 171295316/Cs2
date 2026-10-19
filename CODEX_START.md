# Codex 立即执行任务

请直接在当前仓库开始编码实现 CS2 Market Intelligence，而不是停留在讨论架构。读取 AGENTS.md、PLAN.md，使用中文深色响应式 UI。

按顺序落实：
1. P0 初始化 apps/web (Next.js/TS/Tailwind), apps/api (FastAPI/Python), apps/worker, PostgreSQL, Redis, docker-compose.yml, .env.example, README, CI，建立基本 lint/test/healthcheck。
2. P1 创建全品类饰品 item 与 variant 数据模型、迁移、搜索/目录/详情接口、导入 adapter；研究 ByMykel/CSGO-API 的许可，不能确认时保留 adapter 和合法样例。
3. P2 创建历史价格表、来源与时间/币种/成交或挂单口径字段、导入接口、最早可用历史 K 线图、数据缺失提示。研究 cs2.sh Steam archive 等合法接口；无授权 Key 时不伪造历史价格。
4. P3 建立供应量 snapshot 模型及 CSV/JSON 可重复导入，支持 observed_distinct_instances, public_inventory_units, listed_units, estimated_total_units；只有真实来源和可复核方法才能显示值。
5. P4 首页、/items、/items/[id]、/methodology、API /docs、基础排行榜、测试、Docker Compose 启动与文档。

每阶段报告代码文件、命令、测试结果和未满足条件。重点验收：docker compose up --build 可以启动；输入查询可检索全品类目录；详情页有历史价格与供应面板；真实数据缺失时严谨显示 unavailable。禁止自动交易。
