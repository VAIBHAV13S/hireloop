# Unit Tests for Authentication & Password Security

from datetime import datetime, timezone
from jose import jwt
from hireloop.apps.api.app.services.auth import hash_password, verify_password, create_access_token
from hireloop.apps.api.app.core.settings import settings

def test_password_hashing():
    pw = "superSecretPassword123!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("wrongPassword", hashed) is False

def test_jwt_token_expiration_validity():
    payload = {"sub": "candidate@example.com", "role": "candidate"}
    token = create_access_token(payload)

    # Decode and verify claims
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == "candidate@example.com"
    assert decoded["role"] == "candidate"

    # Verify exp is in the future (not in 1970!)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    assert decoded["exp"] > now_ts
    assert decoded["exp"] <= now_ts + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60) + 10
