"""Auth service — JWT-based authentication."""
import hashlib
import hmac
import json
import time

SECRET = "demo-secret-do-not-use-in-production"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": int(time.time()) + 3600}
    # Simplified JWT-like token for demo
    return _encode(payload)


def verify_token(token: str) -> dict | None:
    try:
        payload = _decode(token)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def _encode(payload: dict) -> str:
    data = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{data}.{sig}"


def _decode(token: str) -> dict:
    data, sig = token.rsplit(".", 1)
    expected = hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, expected):
        raise ValueError("invalid signature")
    return json.loads(data)
