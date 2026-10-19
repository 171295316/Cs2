"""Bound JSON import bodies before parsing, including chunked uploads."""
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class ImportBodyLimit:
    def __init__(self, app: ASGIApp, max_bytes: int = 2 * 1024 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope['type'] != 'http' or not scope['path'].startswith('/internal/import/'):
            return await self.app(scope, receive, send)
        chunks = []
        total = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            total += len(message.get('body', b''))
            if total > self.max_bytes:
                return await JSONResponse({'detail': 'Import body exceeds 2 MiB'}, status_code=413)(scope, receive, send)
            chunks.append(message)
            if not message.get('more_body', False):
                break
        async def replay():
            return chunks.pop(0) if chunks else await receive()
        return await self.app(scope, replay, send)
