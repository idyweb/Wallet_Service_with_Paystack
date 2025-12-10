import secrets
import hashlib


def generate_api_key() -> str:
    """Generate a random API key with prefix"""
    random_part = secrets.token_urlsafe(32)
    return f"sk_live__{random_part}"

def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage using SHA256"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify API key against hashed version"""
    return hashlib.sha256(plain_key.encode()).hexdigest() == hashed_key