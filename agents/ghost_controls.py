import os
from typing import Dict

TRUTHY = {"1", "true", "yes", "on"}


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY


def ghost_controls() -> Dict[str, bool]:
    ghost_mode = env_flag("GHOST_MODE", False)
    dry_run = env_flag("DRY_RUN", ghost_mode)
    allow_side_effects_default = not (ghost_mode or dry_run)
    allow_side_effects = env_flag("ALLOW_SIDE_EFFECTS", allow_side_effects_default)
    return {
        "ghost_mode": ghost_mode,
        "dry_run": dry_run,
        "allow_side_effects": allow_side_effects,
    }


def side_effects_allowed() -> bool:
    return ghost_controls()["allow_side_effects"]
