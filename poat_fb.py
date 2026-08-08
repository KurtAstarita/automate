import os
import json
import re
import urllib.request
import feedparser
import requests
from datetime import datetime, timezone
import time
import random

# Isolated File Tracking for Facebook
SENT_POSTS_FILE = "sent_posts_fb.json"
REPOSTED_POSTS_FILE = "reposted_posts_fb.json"
FALLBACK_IMAGE = "fallback.jpg"

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


# 4. Media Extraction Helpers
def extract_image_url(entry):
    """Extracts an image URL from RSS media tags, enclosures, or HTML content."""
    if hasattr(entry, "media_content") and entry.media_content:
        for media in entry.media_content:
            if "url" in media and media.get("type", "").startswith("image"):
                return media["url"]

    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image") and "href" in enc:
                return enc["href"]

    content_html = ""
    if "content" in entry:
        content_html = entry.content[0].value
    elif "summary" in entry:
        content_html = entry.summary

    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_html)
    if img_match:
        return img_match.group(1)

    return None


def prepare_media(entry):
    """Downloads article image or falls back to local fallback.jpg."""
    image_url = extract_image_url(entry)
    temp_file = "temp_article_img_fb.jpg"

    if image_url:
        try:
            req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response, open(temp_file, "wb") as out_file:
                out_file.write(response.read())
            return temp_file
        except Exception as e:
            print(f"Failed to download image from feed ({e}). Using fallback image.")

    if os.path.exists(FALLBACK_IMAGE):
        return FALLBACK_IMAGE

    return None


# 5. Facebook API Publisher
def publish_to_facebook(caption, image_path):
    """Posts image and caption to Facebook Page via Graph API."""
    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
    
    payload = {
        "caption": caption,
        "access_token": FB_PAGE_ACCESS_TOKEN
    }

    if image_path and os.path.exists(image_path):
        print(f"Uploading image to Facebook: {image_path}")
        with open(image_path, "rb") as img_file:
            files = {"source": img_file}
            response = requests.post(url, data=payload, files=files)
    else:
        # Fallback to feed link post if no image is available
        feed_url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
        print("No image found. Posting text link to Facebook feed...")
        response = requests.post(feed_url, data={"message": caption, "access_token": FB_PAGE_ACCESS_TOKEN})

    if response.status_code == 200:
        res_data = response.json()
        print(f"Successfully posted to Facebook! Post ID: {res_data.get('id', 'N/A')}")
        return True
    else:
        raise Exception(f"Facebook Graph API Error ({response.status_code}): {response.text}")


# 6. Main Orchestrator
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
        caption_text = f"In case you missed it:\n\n{title}\n\nRead more: {link}"
    else:
        caption_text = f"{title}\n\nRead more: {link}"

    image_path = prepare_media(target_entry)

    # Publish to Facebook
    publish_to_facebook(caption=caption_text, image_path=image_path)

    # Clean up temporary image
    if image_path == "temp_article_img_fb.jpg" and os.path.exists("temp_article_img_fb.jpg"):
        os.remove("temp_article_img_fb.jpg")

    # Update history tracking files
    if is_repost:
        reposted_ids.add(post_id)
        save_tracked_posts(REPOSTED_POSTS_FILE, reposted_ids)
    else:
        sent_ids.add(post_id)
        save_tracked_posts(SENT_POSTS_FILE, sent_ids)


if __name__ == "__main__":
    main()
