import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Set


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("create_github_issue")


def _coerce_labels(raw_labels: Any) -> List[str]:
    if not raw_labels:
        return []
    if isinstance(raw_labels, str):
        return [raw_labels]
    return [label for label in raw_labels if isinstance(label, str) and label]


def filter_existing_labels(requested_labels: Iterable[str], existing_labels: Iterable[str]) -> List[str]:
    available = {label for label in existing_labels if label}
    return [label for label in requested_labels if label in available]


def list_existing_labels(repo: str) -> Set[str]:
    try:
        result = subprocess.run(
            ["gh", "label", "list", "--limit", "1000", "--json", "name", "--repo", repo],
            check=True,
            capture_output=True,
            text=True,
        )
        labels = json.loads(result.stdout or "[]")
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        LOG.warning("Unable to list repository labels; proceeding without labels. %s", exc)
        return set()

    return {item.get("name") for item in labels if item.get("name")}


def build_issue_create_command(issue: Dict[str, Any], repo: str, existing_labels: Iterable[str]) -> List[str]:
    cmd = [
        "gh",
        "issue",
        "create",
        "--title",
        issue["title"],
        "--body",
        issue["body"],
        "--repo",
        repo,
    ]

    requested_labels = _coerce_labels(issue.get("labels"))
    matched_labels = filter_existing_labels(requested_labels, existing_labels)
    missing_labels = [label for label in requested_labels if label not in matched_labels]
    if missing_labels:
        LOG.warning("Skipping missing labels: %s", ", ".join(missing_labels))
    if matched_labels:
        cmd.extend(["--label", ",".join(matched_labels)])

    assignee = issue.get("assignee")
    if assignee:
        cmd.extend(["--assignee", assignee])

    return cmd


def main(argv: List[str]) -> int:
    path = argv[1] if len(argv) > 1 else "refresh_result.json"
    repo = os.environ["GITHUB_REPOSITORY"]

    try:
        with open(path, encoding="utf-8") as file_obj:
            data = json.load(file_obj)
    except (OSError, json.JSONDecodeError) as exc:
        LOG.error("Unable to read issue payload from %s. %s", path, exc)
        return 1

    issue = data["issue_payload"]
    cmd = build_issue_create_command(issue, repo, list_existing_labels(repo))
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        LOG.error("GitHub CLI not found. Install `gh` before running this script. %s", exc)
        return 1
    except subprocess.CalledProcessError as exc:
        LOG.error("Issue creation command failed. %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
