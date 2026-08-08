import os
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Environment variables supplied by GitHub Secrets
CLIENT_ID = os.environ["BLOGGER_CLIENT_ID"]
CLIENT_SECRET = os.environ["BLOGGER_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["BLOGGER_REFRESH_TOKEN"]
BLOG_ID = os.environ["BLOG_ID"]

# Authenticate with Google
creds = Credentials(
    token=None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/blogger"]
)

service = build('blogger', 'v3', credentials=creds)

# Fetch published posts (up to 50, minimal payload)
response = service.posts().list(
    blogId=BLOG_ID, 
    fetchBodies=False, 
    maxResults=50, 
    status=['LIVE']
).execute()

posts = response.get('items', [])

if not posts:
    print("No published posts found.")
    exit(0)

# Sort posts by published date (oldest first)
posts_sorted = sorted(posts, key=lambda x: x['published'])
oldest_post = posts_sorted[0]

print(f"Selected oldest post: '{oldest_post['title']}' (Originally Published: {oldest_post['published']})")

# Update publication date to right now (ISO 8601 UTC format)
now_iso = datetime.now(timezone.utc).isoformat()

updated_post = service.posts().patch(
    blogId=BLOG_ID,
    postId=oldest_post['id'],
    body={'published': now_iso}
).execute()

print(f"Successfully republished '{updated_post['title']}' at {updated_post['published']}")
