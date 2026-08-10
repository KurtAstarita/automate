import base64
import hashlib
import hmac
import json
import os
import re
from typing import Any, Dict, Optional


PACKET_PATTERN = re.compile(
    r"<!--\s*AUTOMATE_PACKET:(?P<encoded>[A-Za-z0-9\-_=]+):(?P<sig>[A-Za-z0-9\-_=]+):AUTOMATE_PACKET\s*-->",
)

# Legacy pattern (no signature) for graceful detection only — not trusted.
_LEGACY_PACKET_PATTERN = re.compile(
    r"<!--\s*AUTOMATE_PACKET:(?P<encoded>[A-Za-z0-9\-_=]+):AUTOMATE_PACKET\s*-->",
)

_ENV_KEY = "PACKET_SIGNING_KEY"


def _get_signing_key() -> Optional[bytes]:
    """Return the HMAC signing key from the environment, or None if not set."""
    key = os.environ.get(_ENV_KEY, "").strip()
    return key.encode("utf-8") if key else None


def _compute_sig(encoded: str, key: bytes) -> str:
    return base64.urlsafe_b64encode(
        hmac.new(key, encoded.encode("ascii"), hashlib.sha256).digest()
    ).decode("ascii").rstrip("=")


def embed_packet(body: str, packet_type: str, payload: Dict[str, Any]) -> str:
    envelope = {
        "packet_type": packet_type,
        "payload": payload,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).decode("ascii").rstrip("=")

    key = _get_signing_key()
    sig = _compute_sig(encoded, key) if key else "unsigned"

    return f"{body.rstrip()}\n\n<!-- AUTOMATE_PACKET:{encoded}:{sig}:AUTOMATE_PACKET -->\n"


def extract_packet(text: str, expected_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    match = PACKET_PATTERN.search(text or "")
    if not match:
        # Reject legacy unsigned packets outright when a signing key is configured.
        if _get_signing_key() and _LEGACY_PACKET_PATTERN.search(text or ""):
            return None
        return None

    encoded = match.group("encoded").strip()
    sig = match.group("sig").strip()

    key = _get_signing_key()
    if key:
        expected_sig = _compute_sig(encoded, key)
        if not hmac.compare_digest(sig, expected_sig):
            return None
    elif sig != "unsigned":
        # Key not configured but packet carries a signature — accept with no verification.
        pass

    padding = "=" * (-len(encoded) % 4)
    try:
        raw = base64.urlsafe_b64decode(f"{encoded}{padding}".encode("ascii")).decode("utf-8")
        envelope = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None

    if expected_type and envelope.get("packet_type") != expected_type:
        return None
    return envelope
