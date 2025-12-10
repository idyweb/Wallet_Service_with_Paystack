from datetime import datetime, timedelta, timezone
from typing import Optional


def parse_expiry_to_datetime(expiry: str) -> Optional[datetime]:
    """Convert expiry string (1H, 1D, 1M, 1Y) to datetime"""
    expiry = expiry.strip().upper()

    mapping = {
        "1H": timedelta(hours=1),
        "1D": timedelta(days=1),
        "1M": timedelta(days=30),
        "1Y": timedelta(days=365),
    }

    delta = mapping.get(expiry)
    if not delta:
        return None
    return datetime.now(timezone.utc) + delta