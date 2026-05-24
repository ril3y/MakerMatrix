"""
Credential Encryption Utility
=============================

Symmetric encryption helpers for sensitive supplier credentials at rest.

The key is read from the MAKERMATRIX_ENCRYPTION_KEY environment variable.
The value can be either:
  * A valid Fernet key (32 url-safe base64-encoded bytes), or
  * Any other string, which is run through SHA-256 and base64-encoded to
    produce a deterministic Fernet key (so operators can pick a passphrase
    instead of generating a Fernet key).

If the key is missing, empty, or equal to the .env.example placeholder
``your_encryption_key_here``, the helpers raise ``RuntimeError`` at the
moment of use. This is intentional: silently degrading to plaintext is how
operators ship unencrypted credentials. Fail loud.

The only carve-out is the test suite, which sets ``PYTEST_CURRENT_TEST``
or ``MAKERMATRIX_TESTING=1`` and bootstraps its own ephemeral key via the
shared conftest. Production code paths always require a real key.

A migration shim is provided so that pre-existing plaintext rows in the
database keep working: callers attempt to decrypt and fall back to the
stored value if decryption fails. The next write will then re-encrypt the
value.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Encrypted ciphertext from Fernet always begins with "gAAAAA" (base64 of the
# version byte 0x80 plus the first few bytes of the timestamp). We use this
# as a cheap sentinel to detect whether a stored value is already encrypted.
_FERNET_PREFIX = "gAAAAA"

# Placeholder value shipped in .env.example. Treat as "not configured" so
# operators who copy the template verbatim get a loud error instead of
# silently-unencrypted credentials.
_PLACEHOLDER_KEY = "your_encryption_key_here"

_MISSING_KEY_MESSAGE = (
    "MAKERMATRIX_ENCRYPTION_KEY is missing or unset. "
    "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
    "and set it in your environment or .env file. "
    "The application refuses to handle supplier credentials without a valid key."
)


def _is_test_env() -> bool:
    """True if we are running under pytest or explicit test mode.

    Used solely to allow ``_get_fernet`` to skip the hard-error path when no
    key is configured. The pytest conftest bootstraps a real Fernet key, so
    in practice this branch should never be hit when the suite is run with
    the project's conftest in place; it exists as a defence-in-depth so a
    misconfigured test environment fails the test instead of going boom in
    library code.
    """
    return bool(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv("MAKERMATRIX_TESTING") == "1"


def _derive_key(raw: str) -> bytes:
    """Turn an arbitrary string into a valid Fernet key.

    If the input already looks like a valid 32-byte url-safe base64 key we use
    it directly; otherwise we hash with SHA-256 and base64-encode the digest.
    """
    raw_bytes = raw.encode("utf-8")
    try:
        decoded = base64.urlsafe_b64decode(raw_bytes)
        if len(decoded) == 32:
            return raw_bytes
    except Exception:
        pass

    digest = hashlib.sha256(raw_bytes).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    """Return a Fernet instance, or raise RuntimeError if the key is unusable.

    Raises:
        RuntimeError: when ``MAKERMATRIX_ENCRYPTION_KEY`` is missing, empty,
            or equal to the .env.example placeholder. This is the fail-loud
            behaviour required by the security review.
    """
    raw_key = os.getenv("MAKERMATRIX_ENCRYPTION_KEY")
    if not raw_key or raw_key == _PLACEHOLDER_KEY:
        raise RuntimeError(_MISSING_KEY_MESSAGE)

    try:
        return Fernet(_derive_key(raw_key))
    except Exception as exc:
        raise RuntimeError(
            f"MAKERMATRIX_ENCRYPTION_KEY is set but invalid: {exc}. "
            "Use a Fernet key generated with cryptography.fernet.Fernet.generate_key()."
        ) from exc


def validate_encryption_key() -> None:
    """Startup-time validation hook.

    Call from the FastAPI lifespan so the application refuses to start
    when no usable key is configured. The test environment is exempt
    (see :func:`_is_test_env`).
    """
    if _is_test_env():
        # The shared conftest bootstraps a key; if it didn't, individual
        # tests that actually use encryption will still fail at the moment
        # of use via _get_fernet. We don't want to block test collection.
        try:
            _get_fernet()
        except RuntimeError as exc:
            logger.warning(
                "Test environment is missing MAKERMATRIX_ENCRYPTION_KEY: %s", exc
            )
        return

    # Production / dev: raising here will bubble out of lifespan and prevent
    # the server from coming up with an invalid key.
    _get_fernet()


def encrypt_value(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt a string. Returns None for None/empty input.

    If the value already looks encrypted (Fernet prefix), it is returned
    untouched so we don't double-encrypt.

    Raises:
        RuntimeError: when no encryption key is configured.
    """
    if plaintext is None or plaintext == "":
        return plaintext
    if isinstance(plaintext, str) and plaintext.startswith(_FERNET_PREFIX):
        # Already encrypted
        return plaintext

    fernet = _get_fernet()
    token = fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(ciphertext: Optional[str]) -> Optional[str]:
    """Decrypt a value previously produced by :func:`encrypt_value`.

    Migration shim: if the stored value is not valid ciphertext (e.g. a
    legacy plaintext row from before this fix), the original value is
    returned unchanged so reads keep working.

    Raises:
        RuntimeError: when no encryption key is configured.
    """
    if ciphertext is None or ciphertext == "":
        return ciphertext

    fernet = _get_fernet()

    if not isinstance(ciphertext, str) or not ciphertext.startswith(_FERNET_PREFIX):
        # Looks like a legacy plaintext value; pass through.
        return ciphertext

    try:
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        # Not actually encrypted with this key. Fall back to the stored
        # value so we never blow up reads from older databases.
        logger.warning(
            "Failed to decrypt supplier credential value; returning stored value as plaintext fallback"
        )
        return ciphertext


def is_encrypted(value: Optional[str]) -> bool:
    """Return True if the value looks like Fernet ciphertext."""
    return isinstance(value, str) and value.startswith(_FERNET_PREFIX)
