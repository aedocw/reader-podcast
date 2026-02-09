"""Authentication helpers: API key validation and admin key check."""

import functools

from bottle import request, abort

from app.config import ADMIN_KEY
from app.db import get_user_by_api_key


def _get_api_key():
    """Extract API key from ?key= query param or X-API-Key header."""
    return request.query.get("key") or request.headers.get("X-API-Key")


def require_user(fn):
    """Decorator: resolve user from API key, pass as first arg after self/route params."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = _get_api_key()
        if not api_key:
            abort(401, "API key required (?key= or X-API-Key header)")
        user = get_user_by_api_key(api_key)
        if not user:
            abort(403, "Invalid API key")
        kwargs["user"] = user
        return fn(*args, **kwargs)
    return wrapper


def require_admin(fn):
    """Decorator: require ADMIN_KEY for admin endpoints."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = _get_api_key()
        if not api_key or api_key != ADMIN_KEY:
            abort(403, "Admin key required")
        return fn(*args, **kwargs)
    return wrapper
