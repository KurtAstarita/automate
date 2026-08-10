import json
import logging
import os
import sys
import time

import feedparser
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Environment Variables
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY")
SITE_HOST = os.environ.get("SITE_HOST")  # e.g., "kurtastarita.com"
RSS_FEED_URL = os.environ.get("RSS_FEED_URL")

# Rate-limiting: max 1 request per _GOOGLE_DELAY_SECONDS to Google Indexing API
_GOOGLE_DELAY_SECONDS = 0.5


def get_latest_urls(count=5):
    """Fetches the latest published URLs from the site's RSS feed."""
    logger.info("Parsing RSS Feed: %s", RSS_FEED_URL)
    try:
        feed = feedparser.parse(RSS_FEED_URL)
        urls = [entry.link for entry in feed.entries[:count]]
        return list(set(urls))
    except Exception as exc:
        logger.error("Failed to parse RSS feed: %s", type(exc).__name__)
        return []


def ping_google_indexing(url_list):
    """Pings Google Indexing API for instant crawling."""
    if not GOOGLE_CREDS_JSON:
        logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON not set. Skipping Google Indexing API.")
        return

    logger.info("Sending %d URL(s) to Google Indexing API...", len(url_list))

    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: %s", exc)
        return

    try:
        scopes = ["https://www.googleapis.com/auth/indexing"]
        credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build("indexing", "v3", credentials=credentials)
    except Exception as exc:
        logger.error("Failed to build Google Indexing service: %s", type(exc).__name__)
        return

    for i, url in enumerate(url_list):
        if i > 0:
            time.sleep(_GOOGLE_DELAY_SECONDS)
        body = {"url": url, "type": "URL_UPDATED"}
        try:
            response = service.urlNotifications().publish(body=body).execute()
            notify_time = (
                response.get("urlNotificationMetadata", {})
                .get("latestUpdate", {})
                .get("notifyTime")
            )
            logger.info("Google notified: %s | notifyTime: %s", url, notify_time)
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "rateLimitExceeded" in msg.lower():
                logger.warning("Google Indexing API rate limited for %s — backing off 10s", url)
                time.sleep(10)
            else:
                logger.error("Google Indexing failed for %s: %s", url, type(exc).__name__)


def ping_indexnow(url_list):
    """Pings the open IndexNow API (Bing, Yandex, Seznam)."""
    if not INDEXNOW_KEY or not SITE_HOST:
        logger.warning("INDEXNOW_KEY or SITE_HOST not set. Skipping IndexNow API.")
        return

    logger.info("Sending %d URL(s) to IndexNow (Bing/Yandex)...", len(url_list))

    endpoint = "https://api.indexnow.org/indexnow"
    payload = {
        "host": SITE_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{SITE_HOST}/{INDEXNOW_KEY}.txt",
        "urlList": url_list,
    }
    headers = {"Content-Type": "application/json; charset=utf-8"}

    try:
        with requests.Session() as session:
            response = session.post(endpoint, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 202]:
            logger.info("IndexNow accepted (%d) for host %s", response.status_code, SITE_HOST)
        else:
            logger.error("IndexNow failed (%d): %s", response.status_code, response.text[:200])
    except requests.RequestException as exc:
        logger.error("IndexNow request error: %s", type(exc).__name__)


def main():
    # Allow target URLs to be passed directly as CLI args, or fallback to RSS
    if len(sys.argv) > 1:
        urls = [sys.argv[1]]
    elif RSS_FEED_URL:
        urls = get_latest_urls(count=3)
    else:
        logger.error("No URLs provided and RSS_FEED_URL not configured.")
        sys.exit(1)

    if not urls:
        logger.info("No URLs found to submit.")
        return

    logger.info("Target URLs for indexing: %s", urls)
    ping_google_indexing(urls)
    ping_indexnow(urls)


if __name__ == "__main__":
    main()
