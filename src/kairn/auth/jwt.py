"""JWT token creation and validation for Kairn authentication."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import jwt

logger = logging.getLogger(__name__)


class TokenExpiredError(Exception):
    """Raised when a JWT token has expired."""


class TokenInvalidError(Exception):
    """Raised when a JWT token is invalid."""


def create_token(user_id: str, org_id: str, exp_minutes: int = 60) -> str:
    """Create a JWT token for a user."""
    secret = os.environ.get("KAIRN_JWT_SECRET", "test-secret-key-do-not-use")
    now = int(time.time())
    payload = {
        "sub": user_id,
        "org": org_id,
        "exp": now + (exp_minutes * 60),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str, secret: str) -> dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.warning("Token expired: %s", e)
        raise TokenExpiredError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token: %s", e)
        raise TokenInvalidError("Token is invalid") from e
