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
