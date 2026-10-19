# P2 历史价格阶段

代码：迁移 0003、observations.py/prices.py/providers.py、PricePanel/HistoryChart。

- 来源需同时通过基础审批和 prices 专项授权，不能以目录许可代替行情许可。
- 导入按来源 external_key 映射到已有 item/variant；原始记录不可变，相同记录重复提交幂等，冲突整批回滚。
- 严格整数最小货币单位；UTC 原始时间、粒度、币种、成交/挂单口径、来源证明、覆盖和方法齐全。
- 查询支持 7D/30D/1Y/ALL、自定义 from/to、原始 1h/1d 粒度。没有数据不转为零。多来源不自动拼接；未选择时只有唯一候选源才自动展示。
- Lightweight Charts 绘制实际观测曲线，不从中位成交价捏造 OHLC；缺口分段，不插值。精确金额表保留整数精度，超过 JS 安全整数范围时只展示原始表。
- 本地后端 34 通过、1 个 PostgreSQL 专项跳过；Ruff/mypy 通过。前端/迁移最终结果在 PR 汇总。
- 供应商远程接口保留禁用适配器；未配置经过核验的访问和再分发许可/API Key，不能宣称已回填真实历史。
