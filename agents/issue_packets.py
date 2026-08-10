import base64
import json
import re
from typing import Any, Dict, Optional


PACKET_PATTERN = re.compile(
    r"<!--\s*AUTOMATE_PACKET:(?P<encoded>[^>]+):AUTOMATE_PACKET\s*-->",
    re.DOTALL,
)


def embed_packet(body: str, packet_type: str, payload: Dict[str, Any]) -> str:
    envelope = {
        "packet_type": packet_type,
        "payload": payload,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    return f"{body.rstrip()}\n\n<!-- AUTOMATE_PACKET:{encoded}:AUTOMATE_PACKET -->\n"


def extract_packet(text: str, expected_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    match = PACKET_PATTERN.search(text or "")
    if not match:
        return None

    encoded = match.group("encoded").strip()
    padding = "=" * (-len(encoded) % 4)
    try:
        raw = base64.urlsafe_b64decode(f"{encoded}{padding}".encode("ascii")).decode("utf-8")
        envelope = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None

    if expected_type and envelope.get("packet_type") != expected_type:
        return None
    return envelope
