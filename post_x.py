import os
import json
import re
import urllib.request
import feedparser
import tweepy
from datetime import datetime, timezone
import time
import random

# File tracking
SENT_POSTS_FILE = "sent_posts.json"
REPOSTED_POSTS_FILE = "reposted_posts.json"

# 1. Environment Variable Validation
RSS_FEED_URL = os.getenv("RSS_FEED_URL")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

if not all([RSS_FEED_URL, X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
    raise ValueError("Missing one or more required environment variables.")

# 2. Authenticate with X
auth = tweepy.OAuth1UserHandler(
    X_CONSUMER_KEY, X_CONSUMER_SECRET,
    X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
)
api_v1 = tweepy.API(auth)

client = tweepy.Client(
    consumer_key=X_CONSUMER_KEY,
    consumer_secret=X_CONSUMER_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_TOKEN_SECRET
)


# 3. JSON Tracking Helpers
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


# 4. RSS Post Age and Recycling Helpers
def get_post_age_days(entry):
    """Calculates how many days old an RSS entry is."""
    time_struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not time_struct:
        return None

    pub_datetime = datetime.fromtimestamp(time.mktime(time_struct), tz=timezone.utc)
    now_datetime = datetime.now(timezone.utc)
    return (now_datetime - pub_datetime).days


def get_eligible_repost(entries, reposted_ids):
    """Filters articles published between 14 and 30 days ago that haven't been recycled yet."""
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


# 5. Media Extraction Helpers
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
    """Downloads article image or returns None if no image is found."""
    image_url = extract_image_url(entry)
    temp_file = "temp_article_img.jpg"

    if image_url:
        try:
            req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response, open(temp_file, "wb") as out_file:
                out_file.write(response.read())
            return temp_file
        except Exception as e:
            print(f"Failed to download image from feed ({e}). Proceeding without media attachment.")

    return None


# 6. Main Orchestrator
def main():
    sent_ids = load_tracked_posts(SENT_POSTS_FILE)
    reposted_ids = load_tracked_posts(REPOSTED_POSTS_FILE)

    print(f"Fetching feed from: {RSS_FEED_URL}")
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
        print(f"Found new post: {target_entry.title}")
    else:
        # Fallback to 14-30 day old evergreen post
        print("No new posts found. Checking for evergreen posts (14-30 days old)...")
        target_entry = get_eligible_repost(feed.entries, reposted_ids)
        if target_entry:
            is_repost = True
            print(f"Selected evergreen post to recycle: {target_entry.title}")
        else:
            print("No eligible posts in the 14-30 day window available to re-post.")
            return

    post_id = target_entry.get("id") or target_entry.link
    title = target_entry.title
    link = target_entry.link

    if is_repost:
        tweet_text = f"In case you missed it:\n\n{title}\n\n{link}"
    else:
        tweet_text = f"{title}\n\n{link}"

    image_path = prepare_media(target_entry)
    media_ids = []

    if image_path:
        try:
            print(f"Uploading image: {image_path}")
            media = api_v1.media_upload(filename=image_path)
            media_ids.append(media.media_id)
        except Exception as e:
            print(f"Warning: Failed to upload image ({e}). Posting tweet text only.")

    print(f"Posting tweet: {title}")
    if media_ids:
        response = client.create_tweet(text=tweet_text, media_ids=media_ids)
    else:
        response = client.create_tweet(text=tweet_text)

    print(f"Successfully posted! Tweet ID: {response.data['id']}")

    if image_path == "temp_article_img.jpg" and os.path.exists("temp_article_img.jpg"):
        os.remove("temp_article_img.jpg")

    # Save to proper tracking file
    if is_repost:
        reposted_ids.add(post_id)
        save_tracked_posts(REPOSTED_POSTS_FILE, reposted_ids)
    else:
        sent_ids.add(post_id)
        save_tracked_posts(SENT_POSTS_FILE, sent_ids)


if __name__ == "__main__":
    main()
