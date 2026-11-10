import base64
import hashlib
import hmac
import os
import time

SECRET_KEY = os.environ.get("CAMPUSSPACE_SECRET", "dev-secret-change-me").encode()
TOKEN_TTL = 7 * 24 * 3600  # токен живёт 7 дней
ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), ITERATIONS)
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _sign(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()


def create_token(user_id: int) -> str:
    payload = f"{user_id}:{int(time.time()) + TOKEN_TTL}"
    return base64.urlsafe_b64encode(f"{payload}:{_sign(payload)}".encode()).decode()


def read_token(token: str) -> int | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        user_id, expires, signature = raw.split(":")
        if not hmac.compare_digest(signature, _sign(f"{user_id}:{expires}")):
            return None
        if int(expires) < time.time():
            return None
        return int(user_id)
    except Exception:
        return None