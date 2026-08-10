"""
GSC Fetcher – Google Search Console Data Puller

Pulls page-level performance metrics from the Search Console API for all
pages on the site and writes them to gsc_data.json for use by the weekly
refresh workflow.

Environment variables consumed:
    GOOGLE_SERVICE_ACCOUNT_JSON  – Service account key JSON string
    GSC_SITE_URL                 – Property URL, e.g. "https://kurtastarita.com/"
    GSC_LOOKBACK_DAYS            – Optional; defaults to 28

Usage (CI):
    python scripts/gsc_fetcher.py
    # Writes gsc_data.json
"""

import json
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DEFAULT_LOOKBACK_DAYS: int = 28
MAX_ROWS: int = 200


def _normalise_slug(path: str) -> str:
    """Convert a URL path to a slug string for downstream matching."""
    path = path.strip("/")
    # Remove year/month prefix patterns like 2024/01/
    path = re.sub(r"^\d{4}/\d{2}/", "", path)
    return path.lower().strip("/")


def fetch_gsc_data(
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Pull page-level GSC metrics using the Search Console API.

    Returns:
        (rows, error_string) — error_string is None on success.
    """
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    site_url = os.environ.get("GSC_SITE_URL", "https://kurtastarita.com/").strip()

    if not creds_json:
        return [], "GOOGLE_SERVICE_ACCOUNT_JSON not set"

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        try:
            creds_info = json.loads(creds_json)
        except json.JSONDecodeError as exc:
            return [], f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {exc}"

        scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=scopes
        )
        service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        return [], f"GSC auth failed: {exc}"

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=lookback_days)

    request_body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": ["page"],
        "rowLimit": MAX_ROWS,
        "startRow": 0,
    }

    try:
        response = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=request_body)
            .execute()
        )
    except Exception as exc:
        msg = str(exc)
        if "429" in msg or "rateLimitExceeded" in msg.lower() or "quota" in msg.lower():
            return [], f"GSC API rate limited: {exc}"
        return [], f"GSC API query failed: {exc}"

    rows: List[Dict[str, Any]] = []
    for row in response.get("rows", []):
        page_url = row.get("keys", [""])[0]
        slug = _normalise_slug(page_url.replace(site_url.rstrip("/"), ""))
        rows.append(
            {
                "url_slug": slug,
                "title": slug.replace("-", " ").title(),
                "published_date": "",
                "position": round(row.get("position", 0), 1),
                "impressions": int(row.get("impressions", 0)),
                "clicks": int(row.get("clicks", 0)),
                "ctr": round(row.get("ctr", 0.0), 4),
            }
        )

    # Sort by opportunity: high impressions + poor position
    rows.sort(key=lambda r: (r["impressions"] * max(1, r["position"] - 5)), reverse=True)
    logger.info("GSC fetched %d page rows for %s", len(rows), site_url)
    return rows, None


def main() -> int:
    lookback = int(os.environ.get("GSC_LOOKBACK_DAYS", str(DEFAULT_LOOKBACK_DAYS)))
    rows, error = fetch_gsc_data(lookback_days=lookback)

    if error:
        logger.warning("GSC fetch failed (%s). Writing empty output.", error)
        rows = []

    output_path = "gsc_data.json"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, suffix=".json", dir="."
    ) as tmp:
        json.dump(rows, tmp, indent=2)
        tmp_name = tmp.name
    os.replace(tmp_name, output_path)

    logger.info("Wrote %d rows to gsc_data.json", len(rows))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
