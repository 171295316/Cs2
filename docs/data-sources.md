# 数据来源核验与生产开关（P1）

核验日期：2026-10-19。

## ByMykel/CSGO-API

直接核对上游 [LICENSE](https://github.com/ByMykel/CSGO-API/blob/main/LICENSE)（文件 blob SHA `4026f1afd7d11f1bf250c773badb287911f457b9`）：代码采用 MIT，分发副本须保留版权和许可。README（blob SHA `e41e1e5b695080b3384f6e6510d373611d8beeab`）提供 en/zh-CN、all.json 与 skins_not_grouped.json，后者含源 id、skin_id、wear、stattrak、souvenir 和 market_hash_name。

这次实现独立的离线格式适配器，没有复制上游数据或图片。MIT 代码许可不能单独证明其中所有 Valve 商标、图片和游戏资产的商业再分发权。因此生产源不自动登记或批准，图片不由该适配器导入，真实目录尚未导入。正式展示前须保存对**实际数据集和使用范围**的许可核验依据；使用副本时保留上游版权声明。不得因测试通过宣称已覆盖全市场。

按源 ID 连接中英文，按 skin_id 连接变体；不通过饰品名称猜测映射。不同平台的同名物品保持独立，直到以后有人建立经过核实的映射。无交易属性时保留 null；不推断可交易。分组名称暂用首个实际变体的名称，仅为展示标签，不代表跨平台 canonical match。基础项 ID 与变体 ID 不依赖名称或导入顺序。

## 价格、存世量

P1 不启用任何行情数据供应者，不添加价格或供给记录。Steam、BUFF、cs2.sh 等候选源的商业条款、批量历史访问、缓存和二次展示权限留待 P2/P3 独立核验。缺数返回 unavailable，网站显示「暂无可核实数据」。测试数据仅存在 tests 内，使用 TEST ONLY / 测试专用标记，不随应用启动导入。

## 本阶段限制

- 支持规范化导入的类别：skin、knife、glove、case、collection_package、sticker、capsule、agent、music_kit、keychain、graffiti、patch、tool、other；未知上游分类需人工确认，不静默猜测。
- 离线适配器接受单一类别的上游文件；不得把混合文件当作单一类别导入。刀、手套需先按真实上游字段拆分。
- 当前导入是受 2 MiB / 1000 基础项限制的单批原子事务。大目录须分批，单批失败全部回滚；重复提交不产生重复项。没有公开远程下载/回填入口。
- 来源审批为宿主 CLI 操作；HTTP 导入不能自批许可。API 无 IMPORT_TOKEN 时禁用导入。请在管理网络后部署并使用 HTTPS，不向浏览器传入 token。
