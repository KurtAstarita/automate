"""Shared contract and regression-gate constants for ghost testing."""

CONTRACT_VERSION = "2.0"

# Stable, checked-in baseline location for snapshot + metrics goldens.
GOLDEN_ROOT = "tests/golden/ghost"

# Easy-to-tune regression thresholds for PR quality gates.
MAX_FALLBACK_RATE_REGRESSION = 0.0
MAX_MISSING_REQUIRED_FIELD_RATE_REGRESSION = 0.0

