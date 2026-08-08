import os
import sys
import json
import requests
import feedparser
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Environment Variables
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY")
SITE_HOST = os.environ.get("SITE_HOST") # e.g., "kurtasterita.com"
RSS_FEED_URL = os.environ.get("RSS_FEED_URL")

def get_latest_urls(count=5):
    """Fetches the latest published URLs from the site's RSS feed."""
    print(f"📡 Parsing RSS Feed: {RSS_FEED_URL}")
    feed = feedparser.parse(RSS_FEED_URL)
    urls = [entry.link for entry in feed.entries[:count]]
    return list(set(urls))

def ping_google_indexing(url_list):
    """Pings Google Indexing API for instant crawling."""
    if not GOOGLE_CREDS_JSON:
        print("⚠️ GOOGLE_SERVICE_ACCOUNT_JSON not set. Skipping Google Indexing API.")
        return

    print(f"\n🚀 Sending {len(url_list)} URL(s) to Google Indexing API...")
    
    try:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        scopes = ["https://www.googleapis.com/auth/indexing"]
        credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
        service = build("indexing", "v3", credentials=credentials)

        for url in url_list:
            body = {
                "url": url,
                "type": "URL_UPDATED"
            }
            response = service.urlNotifications().publish(body=body).execute()
            print(f"  ✅ Google Notified: {url} | Response: {response.get('urlNotificationMetadata', {}).get('latestUpdate', {}).get('notifyTime')}")
    except Exception as e:
        print(f"  ❌ Google Indexing Error: {e}")

def ping_indexnow(url_list):
    """Pings the open IndexNow API (Bing, Yandex, Seznam)."""
    if not INDEXNOW_KEY or not SITE_HOST:
        print("⚠️ INDEXNOW_KEY or SITE_HOST not set. Skipping IndexNow API.")
        return

    print(f"\n🚀 Sending {len(url_list)} URL(s) to IndexNow (Bing/Yandex)...")
    
    endpoint = "https://api.indexnow.org/indexnow"
    payload = {
        "host": SITE_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{SITE_HOST}/{INDEXNOW_KEY}.txt",
        "urlList": url_list
    }
    
    headers = {"Content-Type": "application/json; charset=utf-8"}
    
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 202]:
            print(f"  ✅ IndexNow Accepted ({response.status_code}) for host {SITE_HOST}")
        else:
            print(f"  ❌ IndexNow Failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"  ❌ IndexNow Exception: {e}")

def main():
    # Allow target URLs to be passed directly as CLI args, or fallback to RSS
    if len(sys.argv) > 1:
        urls = [sys.argv[1]]
    elif RSS_FEED_URL:
        urls = get_latest_urls(count=3)
    else:
        print("❌ No URLs provided and RSS_FEED_URL not configured.")
        sys.exit(1)

    if not urls:
        print("No URLs found to submit.")
        return

    print(f"Target URLs for Indexing: {urls}")
    ping_google_indexing(urls)
    ping_indexnow(urls)

if __name__ == "__main__":
    main()
