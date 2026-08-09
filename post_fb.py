import os
import json
import feedparser
import requests
from datetime import datetime, timezone
import time
import random

# Isolated File Tracking for Facebook
SENT_POSTS_FILE = "sent_posts_fb.json"
REPOSTED_POSTS_FILE = "reposted_posts_fb.json"

# 1. Environment Variable Validation
RSS_FEED_URL = os.getenv("RSS_FEED_URL")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")

if not all([RSS_FEED_URL, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN]):
    raise ValueError("Missing one or more required environment variables for Facebook (RSS_FEED_URL, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN).")


# 2. JSON Tracking Helpers
def load_tracked_posts(file_path):
    """Loads IDs from a local JSON tracking file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_tracked_posts(file_path, id_set):
    """Saves updated set of IDs back to JSON."""
    with open(file_path, "w") as f:
        json.dump(list(id_set), f, indent=2)


# 3. RSS Post Age and Recycling Helpers
def get_post_age_days(entry):
    """Calculates how many days old an RSS entry is."""
    time_struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not time_struct:
        return None

    pub_datetime = datetime.fromtimestamp(time.mktime(time_struct), tz=timezone.utc)
    now_datetime = datetime.now(timezone.utc)
    return (now_datetime - pub_datetime).days


def get_eligible_repost(entries, reposted_ids):
    """Filters articles published between 14 and 30 days ago that haven't been recycled on FB yet."""
    eligible = []

    for entry in entries:
        post_id = entry.get("id") or entry.link
        
        if post_id in reposted_ids:
            continue

        age_days = get_post_age_days(entry)
        if age_days is not None and 14 <= age_days <= 30:
            eligible.append(entry)

    if not eligible:
        return None

    return random.choice(eligible)


# 4. Facebook API Publisher (Open Graph Link Card)
def publish_to_facebook(message, link):
    """Posts a link to Facebook Page feed to generate an Open Graph preview card."""
    url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
    
    payload = {
        "message": message,
        "link": link,
        "access_token": FB_PAGE_ACCESS_TOKEN
    }

    print(f"Publishing link card to Facebook Page feed for: {link}")
    response = requests.post(url, data=payload)

    if response.status_code == 200:
        res_data = response.json()
        print(f"Successfully posted to Facebook! Post ID: {res_data.get('id', 'N/A')}")
        return True
    else:
        raise Exception(f"Facebook Graph API Error ({response.status_code}): {response.text}")


# 5. Main Orchestrator
def main():
    sent_ids = load_tracked_posts(SENT_POSTS_FILE)
    reposted_ids = load_tracked_posts(REPOSTED_POSTS_FILE)

    print(f"Fetching feed for Facebook from: {RSS_FEED_URL}")
    feed = feedparser.parse(RSS_FEED_URL)

    if not feed.entries:
        print("No entries found in RSS feed.")
        return

    # Check for brand new posts first
    new_entries = [e for e in reversed(feed.entries) if (e.get("id") or e.link) not in sent_ids]

    target_entry = None
    is_repost = False

    if new_entries:
        target_entry = new_entries[-1]
        print(f"Found new post for Facebook: {target_entry.title}")
    else:
        # Fallback to 14-30 day old evergreen post
        print("No new posts found. Checking for evergreen posts (14-30 days old)...")
        target_entry = get_eligible_repost(feed.entries, reposted_ids)
        if target_entry:
            is_repost = True
            print(f"Selected evergreen post to recycle on Facebook: {target_entry.title}")
        else:
            print("No eligible posts in the 14-30 day window available to re-post on Facebook.")
            return

    post_id = target_entry.get("id") or target_entry.link
    title = target_entry.title
    link = target_entry.link

    if is_repost:
        message_text = f"In case you missed it:\n\n{title}"
    else:
        message_text = title

    # Publish link card directly to Facebook
    publish_to_facebook(message=message_text, link=link)

    # Update history tracking files
    if is_repost:
        reposted_ids.add(post_id)
        save_tracked_posts(REPOSTED_POSTS_FILE, reposted_ids)
    else:
        sent_ids.add(post_id)
        save_tracked_posts(SENT_POSTS_FILE, sent_ids)


if __name__ == "__main__":
    main()
