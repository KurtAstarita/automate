import unittest

from scripts.create_github_issue import build_issue_create_command


class BuildIssueCreateCommandTests(unittest.TestCase):
    def test_omits_missing_labels(self):
        issue = {
            "title": "Refresh title",
            "body": "Refresh body",
            "labels": ["post-refresh", "automated", "bug"],
            "assignee": "KurtAstarita",
        }

        cmd = build_issue_create_command(issue, "KurtAstarita/automate", {"bug"})

        self.assertEqual(
            cmd,
            [
                "gh",
                "issue",
                "create",
                "--title",
                "Refresh title",
                "--body",
                "Refresh body",
                "--repo",
                "KurtAstarita/automate",
                "--label",
                "bug",
                "--assignee",
                "KurtAstarita",
            ],
        )

    def test_skips_label_flag_when_no_requested_labels_exist(self):
        issue = {
            "title": "Refresh title",
            "body": "Refresh body",
            "labels": ["post-refresh", "automated"],
        }

        cmd = build_issue_create_command(issue, "KurtAstarita/automate", {"bug"})

        self.assertEqual(
            cmd,
            [
                "gh",
                "issue",
                "create",
                "--title",
                "Refresh title",
                "--body",
                "Refresh body",
                "--repo",
                "KurtAstarita/automate",
            ],
        )


if __name__ == "__main__":
    unittest.main()
