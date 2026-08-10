from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from agents.ghost_controls import side_effects_allowed


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class BloggerPublisher:
    def __init__(self) -> None:
        self.name = "Blogger Publisher"
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    def publish_content(self, package: Dict[str, Any]) -> Dict[str, Any]:
        operation = str(package.get("operation") or "create")
        if not side_effects_allowed():
            return {
                "status": "dry_run_blocked",
                "operation": operation,
                "title": package.get("title"),
                "url_slug": package.get("url_slug"),
            }

        try:
            service = self._build_service()
            if operation == "refresh":
                return self._refresh_existing_post(service, package)
            return self._create_post(service, package)
        except Exception as exc:
            self.logger.error("Blogger publish failed: %s", exc)
            return {
                "status": "error",
                "operation": operation,
                "message": str(exc),
                "title": package.get("title"),
                "url_slug": package.get("url_slug"),
            }

    def _create_post(self, service: Any, package: Dict[str, Any]) -> Dict[str, Any]:
        blog_id = os.environ["BLOG_ID"]
        body = {
            "kind": "blogger#post",
            "title": package["title"],
            "content": package["html"],
            "labels": package.get("labels", []),
            "customMetaData": package.get("content_id") or package.get("approval_reference", ""),
        }
        created = service.posts().insert(
            blogId=blog_id,
            isDraft=False,
            body=body,
        ).execute()
        return {
            "status": "published",
            "operation": "create",
            "post_id": created.get("id"),
            "url": created.get("url"),
            "published": created.get("published"),
            "title": created.get("title"),
        }

    def _refresh_existing_post(self, service: Any, package: Dict[str, Any]) -> Dict[str, Any]:
        blog_id = os.environ["BLOG_ID"]
        existing = self._find_post_by_slug(service, blog_id, package["url_slug"])
        if not existing:
            raise ValueError(f"Unable to find existing Blogger post for slug '{package['url_slug']}'")

        patch_body = {
            "title": package["title"],
            "content": package["html"],
            "labels": package.get("labels", []),
            "published": datetime.now(timezone.utc).isoformat(),
        }
        updated = service.posts().patch(
            blogId=blog_id,
            postId=existing["id"],
            body=patch_body,
        ).execute()
        return {
            "status": "published",
            "operation": "refresh",
            "post_id": updated.get("id"),
            "url": updated.get("url"),
            "published": updated.get("published"),
            "title": updated.get("title"),
        }

    def _find_post_by_slug(self, service: Any, blog_id: str, slug: str) -> Optional[Dict[str, Any]]:
        page_token: Optional[str] = None
        target_slug = slug.strip("/").lower()
        while True:
            response = service.posts().list(
                blogId=blog_id,
                fetchBodies=False,
                maxResults=100,
                status="LIVE",
                pageToken=page_token,
            ).execute()
            for item in response.get("items", []):
                post_slug = self._slug_from_url(item.get("url", ""))
                if post_slug == target_slug:
                    return item
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return None

    @staticmethod
    def _slug_from_url(url: str) -> str:
        parsed = urlparse(url or "")
        return parsed.path.strip("/").split("/")[-1].lower()

    @staticmethod
    def _build_service() -> Any:
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
        return build("blogger", "v3", credentials=creds)
