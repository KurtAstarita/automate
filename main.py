import os
import json
import feedparser
from requests_oauthlib import OAuth1Session

# Load environment variables
RSS_URL = os.environ.get("RSS_FEED_URL")
SENT_FILE = "sent_posts.json"

# X / Twitter API Credentials
CONSUMER_KEY = os.environ.get("X_CONSUMER_KEY")
CONSUMER_SECRET = os.environ.get("X_CONSUMER_SECRET")
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET")

def load_sent_posts():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            return json.load(f)
    return []

def save_sent_posts(sent_posts):
    with open(SENT_FILE, "w") as f:
        json.dump(sent_posts, f, indent=2)

def post_to_x(title, link):
    """Posts a tweet using X API v2."""
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=ACCESS_TOKEN,
        resource_owner_secret=ACCESS_TOKEN_SECRET,
    )
    
    payload = {"text": f"{title}\n\n{link}"}
    response = oauth.post("https://api.twitter.com/2/tweets", json=payload)
    
    if response.status_code != 201:
        raise Exception(f"Request failed: {response.status_code} {response.text}")
    print(f"Successfully posted: {title}")

def main():
    if not RSS_URL:
        raise ValueError("RSS_FEED_URL environment variable is missing.")

    sent_posts = load_sent_posts()
    feed = feedparser.parse(RSS_URL)
    
    # Process entries from oldest to newest
    new_entries = []
    for entry in reversed(feed.entries):
        post_id = entry.get("id", entry.link)
        if post_id not in sent_posts:
            new_entries.append((post_id, entry.title, entry.link))

    if not new_entries:
        print("No new RSS entries found.")
        return

    for post_id, title, link in new_entries:
        try:
            post_to_x(title, link)
            sent_posts.append(post_id)
        except Exception as e:
            print(f"Error posting '{title}': {e}")
            break  # Stop processing remaining posts if API fails

    save_sent_posts(sent_posts)

if __name__ == "__main__":
    main()
