import logging
import time
from uuid import uuid4
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("sentriq.middleware")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique Request ID (x-request-id) to every incoming HTTP request,
    tracks processing execution time, injects request correlation headers, and emits structured logs.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        # Extract or generate unique request ID for distributed tracing
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Attach tracing header to client response
            response.headers["x-request-id"] = request_id
            response.headers["x-response-time-ms"] = str(execution_time_ms)

            # Emit structured request log
            logger.info(
                f"HTTP {request.method} {request.url.path} completed with {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "execution_time_ms": execution_time_ms
                }
            )
            return response

        except Exception as exc:
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled exception during HTTP {request.method} {request.url.path}: {exc}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "execution_time_ms": execution_time_ms
                }
            )
            raise exc
