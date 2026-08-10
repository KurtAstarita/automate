import json
import os
import sys

sys.path.insert(0, ".")

from agents.approval_agent import ApprovalAgent
from agents.blogger_publisher import BloggerPublisher
from agents.issue_packets import extract_packet


def main() -> int:
    comment_body = os.environ["COMMENT_BODY"]
    issue_body = os.environ["ISSUE_BODY"]
    issue_number = int(os.environ["ISSUE_NUMBER"])
    issue_url = os.environ["ISSUE_URL"]
    issue_title = os.environ.get("ISSUE_TITLE", "Untitled")
    comment_author = os.environ["COMMENT_AUTHOR"]
    authorized_users = {
        item.strip()
        for item in os.environ.get("AUTHORIZED_USERS", "").split(",")
        if item.strip()
    }

    result = {
        "status": "ignored",
        "message": "No actionable approval command found.",
        "published": False,
        "issue_number": issue_number,
        "issue_title": issue_title,
    }

    if authorized_users and comment_author not in authorized_users:
        result["message"] = f"User '{comment_author}' is not authorized to publish content."
        _write_result(result)
        return 0

    agent = ApprovalAgent()
    command, argument = agent.parse_approval_comment(comment_body)
    if command is None:
        _write_result(result)
        return 0

    packet = extract_packet(issue_body)
    if not packet:
        result["status"] = "error"
        result["message"] = "Approval packet missing from issue body."
        _write_result(result)
        return 1

    status_map = {
        "approve": "approved",
        "publish": "approved",
        "revision": "revision_requested",
        "reject": "rejected",
    }
    approval_status = status_map.get(command, "pending")
    payload = packet.get("payload", {}) if isinstance(packet, dict) else {}
    briefing_id = (
        payload.get("briefing_id")
        or payload.get("brief_id")
        or payload.get("content_id")
        or f"issue-{issue_number}"
    )

    decision = agent.process_approval_decision(
        briefing_id=briefing_id,
        github_issue_number=issue_number,
        github_issue_url=issue_url,
        approval_status=approval_status,
        approved_by=comment_author,
        approval_method="comment",
        approval_comment=comment_body,
    )

    result.update(
        {
            "status": approval_status,
            "decision_id": decision.decision_id,
            "message": argument or f"Approval command '/{command}' processed.",
        }
    )

    if approval_status == "approved":
        publisher = BloggerPublisher()
        publish_result = publisher.publish_content(payload)
        result["publish_result"] = publish_result
        result["published"] = publish_result.get("status") == "published"
        action_text = "Published" if result["published"] else "Prepared"
        result["message"] = (
            f"{action_text} '{publish_result.get('title', payload.get('title', 'content'))}' "
            f"via {packet.get('packet_type', 'unknown')} flow."
        )

    _write_result(result)
    return 0


def _write_result(result: dict) -> None:
    with open("approval_result.json", "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
