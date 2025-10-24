import pytest

import ghretos


@pytest.mark.parametrize(
    ("url", "expected_type"),
    [
        ("https://github.com/owner/repo/issues/123#event-456", ghretos.IssueEvent),
        (
            "https://github.com/owner/repo/pull/123#pullrequestreview-456",
            ghretos.PullRequestReview,
        ),
        (
            "https://github.com/owner/repo/discussions/123#discussioncomment-456",
            ghretos.DiscussionComment,
        ),
    ],
)
def test_parse_github_url_type(url: str, expected_type: type[ghretos.GitHubResource]):
    resource = ghretos.parse_url(url)
    assert isinstance(resource, expected_type)


@pytest.mark.parametrize(
    ("url", "expected_type"),
    [
        ("https://github.com/owner", ghretos.User),
        ("https://github.com/owner/repo", ghretos.Repo),
        ("https://github.com/owner/repo/issues/123", ghretos.Issue),
        (
            "https://github.com/owner/repo/issues/123#issuecomment-789",
            ghretos.IssueComment,
        ),
        ("https://github.com/owner/repo/pull/123", ghretos.PullRequest),
        (
            "https://github.com/owner/repo/pull/123#issuecomment-789",
            ghretos.PullRequestComment,
        ),
        (
            "https://github.com/owner/repo/pull/123#discussion_r2269233870",
            ghretos.PullRequestReviewComment,
        ),
        ("https://github.com/owner/repo/pull/123#event-999", ghretos.PullRequestEvent),
        ("https://github.com/owner/repo/discussions/12", ghretos.Discussion),
        ("https://github.com/owner/repo/commit/abcdef1234", ghretos.Commit),
        (
            "https://github.com/owner/repo/commit/abcdef1234#commitcomment-111",
            ghretos.CommitComment,
        ),
        ("https://github.com/owner/repo/releases/tag/v1.2.3", ghretos.ReleaseTag),
        # unsupported domain should return None
        ("https://gitlab.com/owner/repo/issues/1", None),
        # unsupported resource path should return None (e.g. tree is not implemented)
        ("https://github.com/owner/repo/tree/main", None),
    ],
)
def test_parse_github_url_various(
    url: str, expected_type: type[ghretos.GitHubResource] | None
):
    resource = ghretos.parse_url(url)
    if expected_type is None:
        assert resource is None
    else:
        assert isinstance(resource, expected_type)
