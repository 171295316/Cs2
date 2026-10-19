"""供应商契约；没有授权证明和 API Key 时禁用远程调用。"""
from typing import Protocol

from app.observations import PriceBatch


class PriceProvider(Protocol):
    def fetch(self, external_keys: list[str], cursor: str | None = None) -> PriceBatch: ...


class ProviderUnavailable(RuntimeError):
    pass


class Cs2ArchiveProvider:
    def fetch(self, external_keys: list[str], cursor: str | None = None) -> PriceBatch:
        # 仅有网站 API 文档不等于拥有缓存和商业再分发许可。
        raise ProviderUnavailable('尚未配置经过核验的 cs2.sh 授权及接口密钥；远程回填默认禁用')
