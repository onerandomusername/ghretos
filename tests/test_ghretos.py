import pytest
import yarl

import ghretos
from ghretos.parsing import (
    _parse_strict_url as parse_strict_url,  # pyright: ignore[reportPrivateUsage]
    _parse_unstrict_url as parse_unstrict_url,  # pyright: ignore[reportPrivateUsage]
)


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


# Test cases for _parse_strict_url and _parse_unstrict_url
@pytest.fixture
def default_settings():
    """Fixture providing default settings with all features enabled."""
    return ghretos.MatcherSettings()


class TestParseNumberableUrl:
    """Test suite for the _parse_strict_url and _parse_unstrict_url functions."""

    # --- Basic Issues ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number"),
        [
            ("owner", "repo", 1),
            ("owner", "repo", 123),
            ("owner", "repo", 999999),
            ("my-org", "my-project", 42),
            ("User123", "Repo_Name", 7),
            ("a", "b", 1),
            ("very-long-owner-name-123", "very-long-repo-name-456", 12345),
        ],
    )
    def test_basic_issue(
        self,
        owner: str,
        repo_name: str,
        number: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing basic issue URLs with various owner/repo/number combinations."""
        url = f"https://github.com/{owner}/{repo_name}/issues/{number}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.Issue)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number

    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "fragment"),
        [
            ("owner", "repo", 1, "issue-1"),
            ("owner", "repo", 123, "issue-123"),
            ("my-org", "my-project", 42, "issue-42"),
        ],
    )
    def test_issue_with_issue_fragment(
        self,
        owner: str,
        repo_name: str,
        number: int,
        fragment: str,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing issue URLs with #issue-XXX fragments."""
        url = f"https://github.com/{owner}/{repo_name}/issues/{number}#{fragment}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.Issue)
        assert result.number == number

    # --- Basic Pull Requests ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number"),
        [
            ("owner", "repo", 1),
            ("owner", "repo", 456),
            ("org-name", "repo-name", 9999),
            ("a", "b", 1),
        ],
    )
    def test_basic_pull_request(
        self,
        owner: str,
        repo_name: str,
        number: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing basic pull request URLs."""
        url = f"https://github.com/{owner}/{repo_name}/pull/{number}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.PullRequest)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number

    # --- Basic Discussions ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number"),
        [
            ("owner", "repo", 1),
            ("owner", "repo", 789),
            ("my-org", "discussions", 123),
        ],
    )
    def test_basic_discussion(
        self, owner, repo_name, number, default_settings: ghretos.MatcherSettings
    ):
        """Test parsing basic discussion URLs without strict type checking."""
        # With require_strict_type=False, discussions without fragments are supported
        url = f"https://github.com/{owner}/{repo_name}/discussions/{number}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.Discussion)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number

    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "fragment"),
        [
            ("owner", "repo", 1, "discussion-1"),
            ("owner", "repo", 123, "discussion-123"),
        ],
    )
    def test_discussion_with_discussion_fragment(
        self,
        owner: str,
        repo_name: str,
        number: int,
        fragment: str,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing discussion URLs with #discussion-XXX fragments."""
        url = f"https://github.com/{owner}/{repo_name}/discussions/{number}#{fragment}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.Discussion)
        assert result.number == number

    # --- Issue Comments ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "comment_id"),
        [
            ("owner", "repo", 1, 100),
            ("owner", "repo", 123, 456789),
            ("my-org", "my-repo", 999, 1),
            ("test-user", "test-repo", 42, 9876543210),
        ],
    )
    def test_issue_comment(
        self,
        owner: str,
        repo_name: str,
        number: int,
        comment_id: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing issue comment URLs with #issuecomment-XXX."""
        url = f"https://github.com/{owner}/{repo_name}/issues/{number}#issuecomment-{comment_id}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.IssueComment)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number
        assert result.comment_id == comment_id

    # --- Pull Request Comments ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "comment_id"),
        [
            ("owner", "repo", 1, 100),
            ("owner", "repo", 456, 789),
            ("org", "project", 999, 123456),
        ],
    )
    def test_pull_request_comment(
        self,
        owner: str,
        repo_name: str,
        number: int,
        comment_id: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing pull request comment URLs with #issuecomment-XXX."""
        url = f"https://github.com/{owner}/{repo_name}/pull/{number}#issuecomment-{comment_id}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.PullRequestComment)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number
        assert result.comment_id == comment_id

    # --- Issue Events ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "event_id"),
        [
            ("owner", "repo", 1, 100),
            ("owner", "repo", 123, 456),
            ("test-org", "test-repo", 999, 9999999),
        ],
    )
    def test_issue_event(
        self,
        owner: str,
        repo_name: str,
        number: int,
        event_id: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing issue event URLs with #event-XXX."""
        url = f"https://github.com/{owner}/{repo_name}/issues/{number}#event-{event_id}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.IssueEvent)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number
        assert result.event_id == event_id

    # --- Pull Request Events ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "event_id"),
        [
            ("owner", "repo", 1, 100),
            ("owner", "repo", 456, 789),
            ("org", "project", 12, 34567),
        ],
    )
    def test_pull_request_event(
        self,
        owner: str,
        repo_name: str,
        number: int,
        event_id: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing pull request event URLs with #event-XXX."""
        url = f"https://github.com/{owner}/{repo_name}/pull/{number}#event-{event_id}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.PullRequestEvent)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number
        assert result.event_id == event_id

    # --- Pull Request Reviews ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "review_id"),
        [
            ("owner", "repo", 1, 100),
            ("owner", "repo", 123, 3373902296),
            ("test-org", "test-repo", 999, 12345),
        ],
    )
    def test_pull_request_review(
        self,
        owner: str,
        repo_name: str,
        number: int,
        review_id: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing pull request review URLs with #pullrequestreview-XXX."""
        url = f"https://github.com/{owner}/{repo_name}/pull/{number}#pullrequestreview-{review_id}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.PullRequestReview)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number
        assert result.review_id == review_id

    # --- Pull Request Review Comments (discussion_r) ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "comment_id"),
        [
            ("owner", "repo", 1, 100),
            ("owner", "repo", 123, 2269233870),
            ("test-org", "test-repo", 456, 98765),
        ],
    )
    def test_pull_request_review_comment_discussion_r(
        self,
        owner: str,
        repo_name: str,
        number: int,
        comment_id: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing pull request review comment URLs with #discussion_rXXX."""
        url = f"https://github.com/{owner}/{repo_name}/pull/{number}#discussion_r{comment_id}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.PullRequestReviewComment)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number
        assert result.comment_id == comment_id
        assert result.sha is None
        assert result.commit_page is False
        assert result.files_page is False

    # --- Pull Request Review Comments on commits page ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "sha", "comment_id"),
        [
            ("owner", "repo", 1, "abc123", 100),
            ("owner", "repo", 123, "deadbeef", 456),
            ("test-org", "test-repo", 456, "1234567890abcdef", 789),
            ("org", "project", 999, "a1b2c3d4e5f6", 12345),
        ],
    )
    def test_pull_request_review_comment_commits_page(
        self,
        owner: str,
        repo_name: str,
        number: int,
        sha: str,
        comment_id: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing pull request review comments on commits page."""
        url = f"https://github.com/{owner}/{repo_name}/pull/{number}/commits/{sha}#r{comment_id}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.PullRequestReviewComment)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number
        assert result.comment_id == comment_id
        assert result.sha == sha
        assert result.commit_page is True
        assert result.files_page is False

    # --- Pull Request Review Comments on files page ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "comment_id"),
        [
            ("owner", "repo", 1, 100),
            ("owner", "repo", 123, 456),
            ("test-org", "test-repo", 456, 789012),
        ],
    )
    def test_pull_request_review_comment_files_page(
        self,
        owner: str,
        repo_name: str,
        number: int,
        comment_id: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing pull request review comments on files page."""
        url = (
            f"https://github.com/{owner}/{repo_name}/pull/{number}/files#r{comment_id}"
        )
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.PullRequestReviewComment)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number
        assert result.comment_id == comment_id
        assert result.sha is None
        assert result.commit_page is False
        assert result.files_page is True

    # --- Discussion Comments ---
    @pytest.mark.parametrize(
        ("owner", "repo_name", "number", "comment_id"),
        [
            ("owner", "repo", 1, 100),
            ("owner", "repo", 123, 456789),
            ("test-org", "test-repo", 999, 98765432),
        ],
    )
    def test_discussion_comment(
        self,
        owner: str,
        repo_name: str,
        number: int,
        comment_id: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing discussion comment URLs with #discussioncomment-XXX."""
        url = f"https://github.com/{owner}/{repo_name}/discussions/{number}#discussioncomment-{comment_id}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.DiscussionComment)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number
        assert result.comment_id == comment_id

    # --- Edge Cases: Invalid inputs ---
    def test_invalid_number_not_digit(
        self, default_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that non-numeric issue numbers return None."""
        url = "https://github.com/owner/repo/issues/abc"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_invalid_comment_id_not_digit(
        self, default_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that non-numeric comment IDs return None."""
        url = "https://github.com/owner/repo/issues/123#issuecomment-abc"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_invalid_sha_non_hex(
        self, default_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that non-hexadecimal SHAs in commits page return None."""
        url = "https://github.com/owner/repo/pull/123/commits/xyz123#r456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_invalid_extra_parts_after_files(
        self, default_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that extra parts after /files return None."""
        url = "https://github.com/owner/repo/pull/123/files/extra#r456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_invalid_commits_without_sha(
        self, default_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that /commits without a SHA returns None."""
        url = "https://github.com/owner/repo/pull/123/commits#r456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_invalid_subpath(self, default_settings: ghretos.MatcherSettings) -> None:
        """Test that invalid subpaths return None."""
        url = "https://github.com/owner/repo/issues/123/invalid"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    # --- Strict Type Testing ---
    def test_strict_type_discussion_fragment_on_issue(
        self, default_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that discussion fragment on /issues/ returns None with strict type."""
        url = "https://github.com/owner/repo/issues/123#discussioncomment-456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_strict_type_pull_review_on_issue(
        self, default_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that pull request review fragment on /issues/ returns None with strict type."""
        url = "https://github.com/owner/repo/issues/123#pullrequestreview-456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_strict_type_discussion_fragment_on_pull(
        self, default_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that discussion fragment on /pull/ returns None with strict type."""
        url = "https://github.com/owner/repo/pull/123#discussioncomment-456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_commits_page_converts_to_pull_type(self) -> None:
        """Test that /issues/123/commits redirects to pull request type (strict type disabled)."""
        # When require_strict_type=False, /issues/123/commits can be treated as pull request
        settings = ghretos.MatcherSettings(require_strict_type=False)
        url = "https://github.com/owner/repo/issues/123/commits/abc123#r456"
        parsed_url = yarl.URL(url)

        result = parse_unstrict_url(parsed_url, settings=settings)

        assert isinstance(result, ghretos.PullRequestReviewComment)

    def test_files_page_converts_to_pull_type(self) -> None:
        """Test that /issues/123/files redirects to pull request type (strict type disabled)."""
        # When require_strict_type=False, /issues/123/files can be treated as pull request
        settings = ghretos.MatcherSettings(require_strict_type=False)
        url = "https://github.com/owner/repo/issues/123/files#r456"
        parsed_url = yarl.URL(url)

        result = parse_unstrict_url(parsed_url, settings=settings)

        assert isinstance(result, ghretos.PullRequestReviewComment)

    # --- Settings Tests ---
    def test_disabled_issues(self) -> None:
        """Test that issues are not parsed when disabled in settings."""
        settings = ghretos.MatcherSettings(issues=False)
        url = "https://github.com/owner/repo/issues/123"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=settings)

        assert result is None

    def test_disabled_pull_requests(self) -> None:
        """Test that pull requests are not parsed when disabled in settings."""
        settings = ghretos.MatcherSettings(pull_requests=False)
        url = "https://github.com/owner/repo/pull/123"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=settings)

        assert result is None

    def test_disabled_discussions(self) -> None:
        """Test that discussions are not parsed when disabled in settings."""
        settings = ghretos.MatcherSettings(discussions=False)
        url = "https://github.com/owner/repo/discussions/123"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=settings)

        assert result is None

    def test_disabled_issue_comments(self) -> None:
        """Test that issue comments are not parsed when disabled in settings."""
        settings = ghretos.MatcherSettings(issue_comments=False)
        url = "https://github.com/owner/repo/issues/123#issuecomment-456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=settings)

        assert result is None

    def test_disabled_pull_request_reviews(self) -> None:
        """Test that pull request reviews are not parsed when disabled in settings."""
        settings = ghretos.MatcherSettings(pull_request_reviews=False)
        url = "https://github.com/owner/repo/pull/123#pullrequestreview-456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=settings)

        assert result is None

    def test_disabled_pull_request_review_comments(self) -> None:
        """Test that pull request review comments are not parsed when disabled in settings."""
        settings = ghretos.MatcherSettings(pull_request_review_comments=False)
        url = "https://github.com/owner/repo/pull/123#discussion_r456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=settings)

        assert result is None

    def test_disabled_discussion_comments(self) -> None:
        """Test that discussion comments are not parsed when disabled in settings."""
        settings = ghretos.MatcherSettings(discussion_comments=False)
        url = "https://github.com/owner/repo/discussions/123#discussioncomment-456"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=settings)

        assert result is None
