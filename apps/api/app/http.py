"""进程内请求保护与无凭证结构化日志；部署入口另配置全局限流。"""
import json
import logging
import time
from collections import OrderedDict
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger('cs2.requests')


class RequestProtection:
    def __init__(self, app: ASGIApp, max_requests: int = 600, window: int = 60):
        self.app = app
        self.max_requests = max_requests
        self.window = window
        self.windows: OrderedDict[str, tuple[float, int]] = OrderedDict()

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        path = scope['path']
        # 不信任未经验证的转发头，防止伪造 IP 绕过进程内保护。
        client = (scope.get('client') or ('unknown', 0))[0]
        now = time.monotonic()
        start, count = self.windows.get(client, (now, 0))
        if now - start >= self.window:
            start, count = now, 0
        self.windows[client] = (start, count + 1)
        self.windows.move_to_end(client)
        while len(self.windows) > 4096:
            self.windows.popitem(last=False)
        request_id = str(uuid4())
        async def send_headers(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                headers.extend([(b'x-content-type-options', b'nosniff'), (b'x-frame-options', b'DENY'),
                                (b'x-request-id', request_id.encode())])
                message['headers'] = headers
                logger.info(json.dumps({'request_id': request_id, 'method': scope['method'],
                                       'path': path, 'status': message['status']}, ensure_ascii=False))
            await send(message)
        if count >= self.max_requests and path not in ['/healthz', '/readyz']:
            return await JSONResponse({'detail': '请求过于频繁，请稍后重试'}, status_code=429,
                                      headers={'Retry-After': str(self.window)})(scope, receive, send_headers)
        return await self.app(scope, receive, send_headers)
