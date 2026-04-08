import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)


def _get_fernet():
    """Return a Fernet instance using ENCRYPTION_KEY env var, or None if not set/invalid."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        logger.warning(f"Invalid ENCRYPTION_KEY — cookie encryption disabled: {exc}")
        return None


def encrypt_cookies(cookies: List[dict]) -> List[dict]:
    """
    Encrypt cookie values before persisting to the database.
    If ENCRYPTION_KEY is not set, stores plaintext and emits a warning.
    """
    fernet = _get_fernet()
    if not fernet:
        logger.warning("ENCRYPTION_KEY not set — storing cookies as plaintext")
        return [dict(c) for c in cookies]

    result = []
    for cookie in cookies:
        encrypted = dict(cookie)
        if encrypted.get("value"):
            encrypted["value"] = fernet.encrypt(encrypted["value"].encode()).decode()
            encrypted["_encrypted"] = True
        result.append(encrypted)
    return result


def decrypt_cookies(cookies: List[dict]) -> List[dict]:
    """
    Decrypt cookie values retrieved from the database.
    Cookies without the _encrypted flag are returned unchanged.
    """
    fernet = _get_fernet()
    result = []
    for cookie in cookies:
        decrypted = dict(cookie)
        if decrypted.pop("_encrypted", False):
            if fernet and decrypted.get("value"):
                try:
                    decrypted["value"] = fernet.decrypt(
                        decrypted["value"].encode()
                    ).decode()
                except Exception as exc:
                    logger.warning(f"Failed to decrypt cookie value: {exc}")
        result.append(decrypted)
    return result
