import logging
import os
import sys
import threading
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thread-safe lazy service initialisation
# ---------------------------------------------------------------------------
_service_lock = threading.Lock()
_service = None


def _get_service():
    global _service
    with _service_lock:
        if _service is None:
            _required = ("BLOGGER_CLIENT_ID", "BLOGGER_CLIENT_SECRET", "BLOGGER_REFRESH_TOKEN", "BLOG_ID")
            missing = [v for v in _required if not os.environ.get(v)]
            if missing:
                raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            creds = Credentials(
                token=None,
                refresh_token=os.environ["BLOGGER_REFRESH_TOKEN"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.environ["BLOGGER_CLIENT_ID"],
                client_secret=os.environ["BLOGGER_CLIENT_SECRET"],
                scopes=["https://www.googleapis.com/auth/blogger"],
            )
            _service = build("blogger", "v3", credentials=creds)
    return _service


def list_live_posts():
    service = _get_service()
    blog_id = os.environ["BLOG_ID"]
    posts = []
    page_token = None
    while True:
        try:
            response = service.posts().list(
                blogId=blog_id,
                fetchBodies=False,
                maxResults=50,
                status=["LIVE"],
                pageToken=page_token,
            ).execute()
        except Exception as exc:
            logger.error("Failed to list Blogger posts: %s", exc)
            raise
        posts.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return posts


def main() -> int:
    try:
        posts = list_live_posts()
    except Exception:
        return 1

    if not posts:
        logger.info("No published posts found.")
        return 0

    # Sort posts by published date (oldest first)
    posts_sorted = sorted(posts, key=lambda x: x.get("published", ""))
    oldest_post = posts_sorted[0]

    logger.info(
        "Selected oldest post: '%s' (Originally Published: %s)",
        oldest_post.get("title", "Untitled"),
        oldest_post.get("published", "unknown"),
    )

    # Update publication date to right now (ISO 8601 UTC format)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        service = _get_service()
        blog_id = os.environ["BLOG_ID"]
        updated_post = service.posts().patch(
            blogId=blog_id,
            postId=oldest_post["id"],
            body={"published": now_iso},
        ).execute()
    except Exception as exc:
        logger.error("Failed to patch Blogger post: %s", exc)
        return 1

    logger.info(
        "Successfully republished '%s' at %s",
        updated_post.get("title", ""),
        updated_post.get("published", ""),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
