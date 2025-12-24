import hashlib
import hmac
import secrets
from base64 import b64decode, b64encode

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 16


def api_key_fingerprint(secret: str) -> str:
    """Короткий идентификатор ключа."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]


def _prehash_secret(secret: str) -> str:
    """Нормализовать ключ."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def hash_api_key(secret: str) -> str:
    """Хэшировать ключ API."""
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        _prehash_secret(secret).encode(),
        salt,
        ITERATIONS,
    )
    return f"{b64encode(salt).decode()}${b64encode(dk).decode()}"


def verify_api_key(secret: str, secret_hash: str) -> bool:
    """Проверить ключ API."""
    try:
        parts = secret_hash.split("$")
        if len(parts) == 4 and parts[0] == ALGORITHM:
            _, iterations, salt_b64, hash_b64 = parts
            iterations_int = int(iterations)
            salt = b64decode(salt_b64)
            expected = b64decode(hash_b64)
        elif len(parts) == 2:
            salt = b64decode(parts[0])
            expected = b64decode(parts[1])
            iterations_int = ITERATIONS
        else:
            return False
    except (TypeError, ValueError):
        return False

    computed = hashlib.pbkdf2_hmac(
        "sha256",
        _prehash_secret(secret).encode(),
        salt,
        iterations_int,
    )
    return hmac.compare_digest(expected, computed)
