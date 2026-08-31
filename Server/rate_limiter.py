from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple

from fastapi import Request

try:
    from Server.redis_client import redis_client
except Exception:
    redis_client = None


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class LimitRule:
    requests: int
    window_seconds: int
    body_bytes: int


DEFAULT_LIMIT = LimitRule(
    requests=_env_int("DEFAULT_RATE_LIMIT_REQUESTS", 60),
    window_seconds=_env_int("DEFAULT_RATE_LIMIT_WINDOW_SECONDS", 60),
    body_bytes=_env_int("DEFAULT_REQUEST_BODY_LIMIT_BYTES", 1_048_576),
)

PATH_LIMITS = {
    "/api/chat": LimitRule(
        requests=_env_int("CHAT_RATE_LIMIT_REQUESTS", 20),
        window_seconds=_env_int("CHAT_RATE_LIMIT_WINDOW_SECONDS", 60),
        body_bytes=_env_int("CHAT_REQUEST_BODY_LIMIT_BYTES", 8_192),
    ),
    "/api/chat-stream": LimitRule(
        requests=_env_int("CHAT_STREAM_RATE_LIMIT_REQUESTS", 15),
        window_seconds=_env_int("CHAT_STREAM_RATE_LIMIT_WINDOW_SECONDS", 60),
        body_bytes=_env_int("CHAT_STREAM_REQUEST_BODY_LIMIT_BYTES", 8_192),
    ),
    "/api/send-otp": LimitRule(
        requests=_env_int("OTP_RATE_LIMIT_REQUESTS", 5),
        window_seconds=_env_int("OTP_RATE_LIMIT_WINDOW_SECONDS", 60),
        body_bytes=_env_int("OTP_REQUEST_BODY_LIMIT_BYTES", 4_096),
    ),
    "/api/verify-otp": LimitRule(
        requests=_env_int("OTP_RATE_LIMIT_REQUESTS", 5),
        window_seconds=_env_int("OTP_RATE_LIMIT_WINDOW_SECONDS", 60),
        body_bytes=_env_int("OTP_REQUEST_BODY_LIMIT_BYTES", 4_096),
    ),
    "/api/reindex": LimitRule(
        requests=_env_int("REINDEX_RATE_LIMIT_REQUESTS", 2),
        window_seconds=_env_int("REINDEX_RATE_LIMIT_WINDOW_SECONDS", 3600),
        body_bytes=_env_int("REINDEX_REQUEST_BODY_LIMIT_BYTES", 4_096),
    ),
    "/api/conversations": LimitRule(
        requests=_env_int("CONVERSATION_RATE_LIMIT_REQUESTS", 30),
        window_seconds=_env_int("CONVERSATION_RATE_LIMIT_WINDOW_SECONDS", 60),
        body_bytes=_env_int("CONVERSATION_REQUEST_BODY_LIMIT_BYTES", 262_144),
    ),
}

_memory_store: Dict[str, Deque[float]] = defaultdict(deque)
_memory_lock = threading.Lock()


def get_rate_limit_rule(path: str) -> LimitRule:
    if path.startswith("/api/conversations/"):
        return PATH_LIMITS["/api/conversations"]
    return PATH_LIMITS.get(path, DEFAULT_LIMIT)


def get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def get_request_body_limit(path: str) -> int:
    return get_rate_limit_rule(path).body_bytes


def check_rate_limit(path: str, client_id: str) -> Tuple[bool, int, int]:
    """
    Return (allowed, retry_after_seconds, remaining_requests).
    """
    rule = get_rate_limit_rule(path)
    now = time.time()
    key = f"rate_limit:{path}:{client_id}"

    if redis_client is not None:
        try:
            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, rule.window_seconds)
            ttl = redis_client.ttl(key)
            remaining = max(rule.requests - count, 0)
            if count > rule.requests:
                return False, max(int(ttl) if ttl and ttl > 0 else rule.window_seconds, 1), remaining
            return True, max(int(ttl) if ttl and ttl > 0 else rule.window_seconds, 1), remaining
        except Exception:
            pass

    with _memory_lock:
        bucket = _memory_store[key]
        cutoff = now - rule.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= rule.requests:
            retry_after = max(int(rule.window_seconds - (now - bucket[0])), 1)
            return False, retry_after, 0
        bucket.append(now)
        return True, rule.window_seconds, max(rule.requests - len(bucket), 0)


def get_content_length(request: Request) -> Optional[int]:
    header_value = request.headers.get("content-length")
    if not header_value:
        return None
    try:
        return int(header_value)
    except ValueError:
        return None

