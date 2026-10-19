# Steam 官方市场连接（2026-10-19）

本阶段完成配置诊断、发行商接口传输、原始响应隔离与自动化测试。**尚未取得有 CS2 访问权限的发行商密钥，也未取得和核验真实响应；没有接通生产行情，没有导入任何真实价格。**

## 官方依据与边界

- [ISteamEconomy/GetMarketPrices](https://partner.steamgames.com/doc/webapi/ISteamEconomy#GetMarketPrices) 使用发行商密钥，必须在服务器调用。普通个人 Steam Web API Key 不能替代发行商密钥。
- [认证文档](https://partner.steamgames.com/doc/webapi_overview/auth) 说明发行商密钥的应用权限，以及可通过 `x-webapi-key` 请求头传递密钥。拥有其他游戏的发行商密钥不代表能访问 CS2（appid 730）；需要向 Valve 核实。不要为此盲目注册或付费，不能保证获得权限。
- [Steam Web API 条款](https://steamcommunity.com/dev/apiterms) 与具体接口文档须共同核对；获得凭证不自动代表取得本站所需的缓存和公开展示许可。
- 当前该接口文档列出请求参数，但没有可直接采用的响应字段契约。代码不猜测金额、币种、成交/挂单口径或平台物品 ID。
- `GetAssetPrices` 描述可购买资产价格，不能擅自当成 CS2 社区市场价格。常见 `priceoverview` 网页端点未取得本项目所需的正式开放和再展示依据，本连接器不使用它，也不使用登录 Cookie 或网页抓取作为后备。

## 配置及检查

保持默认关闭。取得对应 CS2 接口权限并核验用途后，在服务器私有环境变量中设置；不要把密钥发在聊天、提交到 Git 或放入前端变量：

```dotenv
STEAM_MARKET_ENABLED=1
STEAM_PUBLISHER_KEY=<服务器私有发行商密钥>
STEAM_CS2_MARKET_PERMISSION_CONFIRMED=1
```

独立记录来源和 `prices` 范围许可。下列命令只能在核实后执行，许可引用必须替换成实际证明，不能把示例当成已获授权：

```bash
docker compose exec api python -m app.admin \
  --code steam_official --name 'Steam 官方市场' \
  --homepage https://steamcommunity.com/market/ \
  --scope prices --license-reference '<实际许可证明的引用>' \
  --confirm-redistribution-rights
```

先完成数据库迁移，再检查配置；修改 Compose 环境变量后重建 API 容器：

```bash
docker compose up -d --build api
docker compose exec api python -m app.steam_official check
```

`check` 不发网络请求。缺少任一前提返回退出码 2 和 `can_probe=false`；配置齐全只表示可以发起探测，不代表密钥已通过 Valve 验证，更不代表价格可用。`can_import_prices` 始终为 false，直到实现经过核验的解析契约。

## 单次探测与证据隔离

具备上述条件后，指定容器内已存在的私有目录和不存在的文件：

```bash
docker compose exec api python -m app.steam_official probe \
  --out /tmp/steam-response.steam-evidence.json
```

仅调用固定官方 HTTPS 地址，appid 固定 730；密钥仅放请求头。请求超时，401/403、429、重定向、非 JSON、异常 JSON、超大响应或回显凭证均停止；无自动重试，不绕过限制。网络异常输出不含底层请求和认证信息。

成功收到 JSON 只保存 `received_unverified` 原始证据：实际接收 UTC 时间、来源、地址、原始内容 SHA256，以及保留数字精度的 JSON 文本。文件权限 0600，拒绝覆盖；控制台不打印正文。归档不写行情表，不发布给网站，文件在容器重建时可能丢失，需由有权限的操作者安全保管。Git 忽略 `*.steam-evidence.json` 和 `provider-evidence/`，勿公开归档。

后续仍需：取得有权限的真实响应，核实完整字段/金额单位/币种/口径/观测时间及许可覆盖；用稳定 ID 映射物品；编写解析与幂等导入测试；完成一次真实采集核验后才开启价格展示。当前报价只能从实际采集时刻开始积累，不能补造旧历史，也不能据此推算总存世量。

## 验证

本阶段测试使用明确标记的模拟 HTTP 响应，不作为真实行情或官方响应结构示例。覆盖禁用与撤权不联网、请求头认证、敏感信息不进入 URL/输出、异常及限流停止、响应上限、原始数字文本保留、行情库不写入、私有归档权限和拒绝覆盖。
