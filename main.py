import os
import json
import re
import urllib.request
import feedparser
import tweepy

# 1. Load and validate Environment Variables
RSS_FEED_URL = os.getenv("RSS_FEED_URL")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

if not all([RSS_FEED_URL, X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
    raise ValueError("Missing one or more required environment variables.")

# 2. Authenticate with X (v1.1 for media upload, v2 for tweeting)
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

SENT_POSTS_FILE = "sent_posts.json"
FALLBACK_IMAGE = "fallback.jpg"


def load_sent_posts():
    """Loads previously posted RSS IDs from local JSON tracking file."""
    if os.path.exists(SENT_POSTS_FILE):
        try:
            with open(SENT_POSTS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_sent_posts(sent_ids):
    """Saves updated list of posted RSS IDs back to file."""
    with open(SENT_POSTS_FILE, "w") as f:
        json.dump(list(sent_ids), f, indent=2)


def extract_image_url(entry):
    """Extracts an image URL from RSS media tags, enclosures, or HTML content."""
    # Check media enclosures
    if hasattr(entry, "media_content") and entry.media_content:
        for media in entry.media_content:
            if "url" in media and media.get("type", "").startswith("image"):
                return media["url"]

    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image") and "href" in enc:
                return enc["href"]

    # Check HTML body for <img> tags
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
    temp_file = "temp_article_img.jpg"

    if image_url:
        try:
            # Set a standard User-Agent so website security doesn't block python
            req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response, open(temp_file, "wb") as out_file:
                out_file.write(response.read())
            return temp_file
        except Exception as e:
            print(f"Failed to download image from feed ({e}). Using fallback image.")

    # Use fallback if download failed or no image was found in RSS
    if os.path.exists(FALLBACK_IMAGE):
        return FALLBACK_IMAGE

    return None


def main():
    sent_ids = load_sent_posts()

    print(f"Fetching feed from: {RSS_FEED_URL}")
    feed = feedparser.parse(RSS_FEED_URL)

    if not feed.entries:
        print("No entries found in RSS feed.")
        return

    # Process items from oldest to newest among unposted items
    entries_to_process = [e for e in reversed(feed.entries) if (e.get("id") or e.link) not in sent_ids]

    if not entries_to_process:
        print("No new posts to publish.")
        return

    # Post only the single latest unposted item per run to avoid spamming
    entry = entries_to_process[-1]
    post_id = entry.get("id") or entry.link
    title = entry.title
    link = entry.link

    tweet_text = f"{title}\n\n{link}"

    image_path = prepare_media(entry)
    media_ids = []

    if image_path:
        try:
            print(f"Uploading image: {image_path}")
            media = api_v1.media_upload(filename=image_path)
            media_ids.append(media.media_id)
        except Exception as e:
            print(f"Warning: Failed to upload image to X ({e}). Posting tweet text only.")

    print(f"Posting tweet: {title}")
    
    if media_ids:
        response = client.create_tweet(text=tweet_text, media_ids=media_ids)
    else:
        response = client.create_tweet(text=tweet_text)

    print(f"Successfully posted! Tweet ID: {response.data['id']}")

    # Clean up temporary downloaded image
    if image_path == "temp_article_img.jpg" and os.path.exists("temp_article_img.jpg"):
        os.remove("temp_article_img.jpg")

    # Mark as posted and save
    sent_ids.add(post_id)
    save_sent_posts(sent_ids)


if __name__ == "__main__":
    main()
