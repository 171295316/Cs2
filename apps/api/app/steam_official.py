"""Steam 已文档化的发行商市场接口：只探测并隔离保存，字段未核验不入行情库。"""
import argparse
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.observations import authorized

ENDPOINT = 'https://partner.steam-api.com/ISteamEconomy/GetMarketPrices/v1/'
SOURCE = 'steam_official'
MAX_BYTES = 10 * 1024 * 1024


class SteamUnavailable(RuntimeError):
    def __init__(self, code: str, reason: str, retry_after: int | None = None):
        super().__init__(reason)
        self.code = code
        self.retry_after = retry_after


@dataclass(frozen=True)
class SteamConfig:
    publisher_key: str = field(default='', repr=False)
    enabled: bool = False
    app_permission_confirmed: bool = False

    @classmethod
    def from_env(cls):
        return cls(publisher_key=os.environ.get('STEAM_PUBLISHER_KEY', '').strip(),
                   enabled=os.environ.get('STEAM_MARKET_ENABLED') == '1',
                   app_permission_confirmed=os.environ.get('STEAM_CS2_MARKET_PERMISSION_CONFIRMED') == '1')


def readiness(db: Session, config: SteamConfig) -> dict:
    missing = []
    if not config.enabled:
        missing.append('STEAM_MARKET_ENABLED=1')
    if not config.publisher_key:
        missing.append('有相应权限的 STEAM_PUBLISHER_KEY')
    if not config.app_permission_confirmed:
        missing.append('CS2 应用权限核验：STEAM_CS2_MARKET_PERMISSION_CONFIRMED=1')
    try:
        authorized(db, SOURCE, 'prices')
    except PermissionError:
        missing.append('steam_official 来源及 prices 专项展示许可')
    except SQLAlchemyError:
        db.rollback()
        missing.append('数据库不可用或尚未迁移，无法核验许可')
    return {'status': 'unavailable', 'can_probe': not missing, 'can_import_prices': False,
            'missing': missing, 'source': SOURCE, 'appid': 730, 'endpoint': ENDPOINT,
            'schema_status': 'unverified',
            'reason': '尚未获得并核验官方响应字段、币种和价格口径，不能把原始响应冒充行情'}


def probe(db: Session, config: SteamConfig, transport: httpx.BaseTransport | None = None) -> dict:
    state = readiness(db, config)
    if not state['can_probe']:
        raise SteamUnavailable('configuration_required', '官方市场探测未启用、缺少凭证或相应权限/展示许可')
    # Valve 文档支持 x-webapi-key，密钥不放 URL；不接受任意目标地址或用户 Cookie。
    try:
        with httpx.Client(timeout=httpx.Timeout(10, connect=5), follow_redirects=False, trust_env=False,
                          transport=transport, headers={'x-webapi-key': config.publisher_key,
                                                        'Accept': 'application/json'}) as client:
            with client.stream('GET', ENDPOINT, params={'appid': 730}) as response:
                if response.status_code in (401, 403):
                    raise SteamUnavailable('access_denied', 'Valve 拒绝访问，请核对发行商密钥、CS2 应用权限及 IP 白名单')
                if response.status_code == 429:
                    header = response.headers.get('Retry-After', '')
                    retry = min(int(header), 86400) if header.isdecimal() and len(header) <= 5 else None
                    raise SteamUnavailable('rate_limited', 'Steam 限流，本次停止；不轮换密钥或重试绕过', retry)
                if 300 <= response.status_code < 400:
                    raise SteamUnavailable('redirect_blocked', '官方端点发生重定向，停止并重新核验地址')
                if response.status_code != 200:
                    raise SteamUnavailable('upstream_error', '官方接口暂不可用，不返回伪造价格')
                content_type = response.headers.get('content-type', '').split(';')[0].strip().lower()
                if content_type != 'application/json':
                    raise SteamUnavailable('unexpected_content', '响应不是 JSON，可能是登录/验证码/错误页；停止访问')
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise SteamUnavailable('response_too_large', '响应超出安全大小，未保存且未入库')
    except httpx.HTTPError:
        # 不把包含请求对象、认证头或 URL 的异常向上层打印。
        raise SteamUnavailable('network_error', '官方接口网络或 TLS 请求失败，未取得有效数据') from None
    try:
        text = bytes(body).decode('utf-8')
        def reject_constant(_):
            raise ValueError('非标准 JSON 常量')
        parsed = json.loads(text, parse_constant=reject_constant)
        if not isinstance(parsed, (dict, list)):
            raise ValueError('不是对象或数组')
        # 官方错误响应或认证字段不作为可归档样本；不输出凭证或其 JSON 转义形式。
        if config.publisher_key in text or json.dumps(config.publisher_key)[1:-1] in text:
            raise SteamUnavailable('credential_echo', '响应含凭证，已拒绝保存')
        if isinstance(parsed, dict):
            result = parsed.get('result')
            if parsed.get('success') is False or (isinstance(result, dict) and result.get('success') is False):
                raise SteamUnavailable('upstream_rejected', '官方响应报告失败，未保存为市场数据')
    except (ValueError, UnicodeError, RecursionError):
        raise SteamUnavailable('invalid_json', '官方响应格式异常，未保存且未入库') from None
    return {'status': 'unavailable', 'transport_status': 'received_unverified', 'source': SOURCE,
            'endpoint': ENDPOINT, 'appid': 730, 'received_at': datetime.now(timezone.utc).isoformat(),
            'sha256': hashlib.sha256(body).hexdigest(), 'schema_status': 'unverified',
            'prices_imported': 0, 'reason': '只保存原始证据；字段和授权覆盖经核验后再实现价格解析',
            # 保存原始 JSON 文本，避免解析时将大整数/小数重新序列化而丢失精度。
            'payload_json': text}


def main() -> int:
    parser = argparse.ArgumentParser(description='Steam 官方市场连接配置检查/单次授权探测；不抓取网页')
    parser.add_argument('action', choices=['check', 'probe'])
    parser.add_argument('--out', type=Path, help='新的私有原始响应归档文件；拒绝覆盖已有文件')
    args = parser.parse_args()
    config = SteamConfig.from_env()
    if args.action == 'probe' and (args.out is None or args.out.exists()):
        parser.error('探测必须指定不存在的 --out 文件；不要放入仓库或公开目录')
    try:
        with SessionLocal() as db:
            if args.action == 'check':
                state = readiness(db, config)
                print(json.dumps(state, ensure_ascii=False))
                return 0 if state['can_probe'] else 2
            result = probe(db, config)
            assert args.out is not None
            # O_EXCL 避免意外覆盖，0600 避免其他本地用户读取潜在未核验字段。
            fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as archive:
                json.dump(result, archive, ensure_ascii=False)
            print(json.dumps({k: v for k, v in result.items() if k != 'payload_json'}, ensure_ascii=False))
            return 0
    except SteamUnavailable as exc:
        print(json.dumps({'status': 'unavailable', 'code': exc.code, 'reason': str(exc),
                          'retry_after': exc.retry_after}, ensure_ascii=False))
        return 2
    except OSError:
        print(json.dumps({'status': 'unavailable', 'reason': '私有归档文件写入失败'}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
