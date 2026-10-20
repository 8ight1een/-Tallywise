import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

from logging_config import request_id_ctx

logger = logging.getLogger("tallywise")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            logger.info(f"{request.method} {request.url.path} -> {status}")
            request_id_ctx.reset(token)
