"""
GA4 Data API Fetcher – v1

Pulls page-level metrics (sessions/active users, engagement rate, conversions)
for a list of candidate URL slugs from a GA4 property.

Returns a dict keyed by normalised path so callers can merge with GSC data.
Falls back gracefully if the GA4 API is unavailable or misconfigured.

Environment variables consumed:
    GOOGLE_SERVICE_ACCOUNT_JSON  – Service account key JSON string (reused from GSC)
    GA4_PROPERTY_ID              – GA4 numeric property id (e.g. "123456789")
    GA4_LOOKBACK_DAYS            – Optional; defaults to 28

Usage:
    from scripts.ga4_fetcher import fetch_ga4_metrics
    metrics, error = fetch_ga4_metrics(["my-post-slug", "another-post"])
    if error:
        # GA4 unavailable – use GSC-only path
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / tunables
# ---------------------------------------------------------------------------
DEFAULT_LOOKBACK_DAYS: int = 28
GA4_DIMENSIONS = ["pagePath"]
GA4_METRICS = ["sessions", "activeUsers", "engagementRate", "conversions"]


def _normalise_path(raw: str) -> str:
    """Return a normalised URL path for matching (lowercase, no trailing slash, path only)."""
    raw = raw.strip()
    # Strip scheme + host if present
    raw = re.sub(r"^https?://[^/]+", "", raw)
    # Ensure leading slash
    if not raw.startswith("/"):
        raw = "/" + raw
    # Remove trailing slash (unless root)
    if len(raw) > 1 and raw.endswith("/"):
        raw = raw.rstrip("/")
    return raw.lower()


def _slug_to_path_variants(slug: str) -> List[str]:
    """Return candidate path strings for a slug so we can match GA4 pagePath rows."""
    slug = slug.strip("/")
    variants = [
        f"/{slug}",
        f"/{slug}/",
    ]
    return [_normalise_path(v) for v in variants]


def fetch_ga4_metrics(
    candidate_slugs: List[str],
    lookback_days: Optional[int] = None,
) -> Tuple[Dict[str, Dict], Optional[str]]:
    """
    Fetch GA4 page metrics for *candidate_slugs*.

    Returns
    -------
    (metrics_dict, error_message)
        metrics_dict  – {normalised_slug: {sessions, engagement_rate, conversions}}
                        Empty dict on failure.
        error_message – None on success, human-readable string on any failure.
    """
    # ------------------------------------------------------------------
    # 1. Resolve configuration
    # ------------------------------------------------------------------
    property_id = os.environ.get("GA4_PROPERTY_ID", "").strip()
    sa_json_raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    days = lookback_days or int(os.environ.get("GA4_LOOKBACK_DAYS", DEFAULT_LOOKBACK_DAYS))

    if not property_id:
        return {}, "GA4_PROPERTY_ID is not set – skipping GA4 fetch"
    if not sa_json_raw:
        return {}, "GOOGLE_SERVICE_ACCOUNT_JSON is not set – skipping GA4 fetch"

    # ------------------------------------------------------------------
    # 2. Attempt imports (library may not be installed in all envs)
    # ------------------------------------------------------------------
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )
        from google.oauth2 import service_account
    except ImportError as exc:
        return {}, f"google-analytics-data library not installed: {exc}"

    # ------------------------------------------------------------------
    # 3. Build credentials
    # ------------------------------------------------------------------
    try:
        sa_info = json.loads(sa_json_raw)
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
    except Exception as exc:
        return {}, f"Failed to build GA4 service account credentials: {exc}"

    # ------------------------------------------------------------------
    # 4. Build and run the report request
    # ------------------------------------------------------------------
    try:
        client = BetaAnalyticsDataClient(credentials=credentials)

        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=d) for d in GA4_DIMENSIONS],
            metrics=[Metric(name=m) for m in GA4_METRICS],
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            limit=10000,
        )

        response = client.run_report(request)
    except Exception as exc:
        return {}, f"GA4 API request failed: {exc}"

    # ------------------------------------------------------------------
    # 5. Parse response into a slug-keyed dict
    # ------------------------------------------------------------------
    # Build a lookup from every normalised path returned by GA4
    path_to_metrics: Dict[str, Dict] = {}
    metric_headers = [h.name for h in response.metric_headers]

    for row in response.rows:
        page_path = _normalise_path(row.dimension_values[0].value)
        row_vals = {metric_headers[i]: row.metric_values[i].value for i in range(len(metric_headers))}

        sessions_raw = row_vals.get("sessions") or row_vals.get("activeUsers") or "0"
        engagement_raw = row_vals.get("engagementRate") or "0"
        conversions_raw = row_vals.get("conversions") or "0"

        path_to_metrics[page_path] = {
            "sessions": _safe_int(sessions_raw),
            "engagement_rate": round(_safe_float(engagement_raw), 4),
            "conversions": _safe_float(conversions_raw),
        }

    # ------------------------------------------------------------------
    # 6. Match slugs to GA4 rows
    # ------------------------------------------------------------------
    slug_metrics: Dict[str, Dict] = {}
    unmatched: List[str] = []

    for slug in candidate_slugs:
        matched = False
        for variant in _slug_to_path_variants(slug):
            if variant in path_to_metrics:
                slug_metrics[slug] = path_to_metrics[variant]
                matched = True
                break
        if not matched:
            unmatched.append(slug)

    if unmatched:
        logger.info(
            "GA4: no data found for %d slug(s): %s",
            len(unmatched),
            ", ".join(unmatched[:5]),
        )

    logger.info(
        "GA4 fetch complete – %d/%d slugs matched (lookback %d days)",
        len(slug_metrics),
        len(candidate_slugs),
        days,
    )
    return slug_metrics, None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(val: str) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _safe_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
