import string

import hypothesis
import pytest
import yarl
from hypothesis import given, settings
from hypothesis import strategies as st

import ghretos
from ghretos.parsing import (
    _parse_strict_url as parse_strict_url,  # pyright: ignore[reportPrivateUsage]
)
from ghretos.parsing import (
    _parse_unstrict_url as parse_unstrict_url,  # pyright: ignore[reportPrivateUsage]
)


USER = st.from_regex(r"^[a-zA-Z0-9-]{1,39}$", fullmatch=True).filter(
    lambda s: not s.startswith("-") and not s.endswith("-")
)
REPO_NAME = st.from_regex(r"^[0-9._-]{1,100}$", fullmatch=True).filter(
    lambda s: s not in (".", "..")
)
NUMBERABLE = st.integers(min_value=1)
ID = st.integers(min_value=1, max_value=2**31 - 1)
SHA = st.text("0123456789abcdefABCDEF", min_size=6, max_size=40)
REF = st.text(string.ascii_letters + string.digits + "-._/", min_size=1)
COMMENT_ID = st.integers(min_value=1)


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
) -> None:
    resource = ghretos.parse_url(url)
    if expected_type is None:
        assert resource is None
    else:
        assert isinstance(resource, expected_type)


# Test cases for _parse_strict_url and _parse_unstrict_url
@pytest.fixture
def default_settings() -> ghretos.MatcherSettings:
    """Fixture providing default settings with all features enabled."""
    return ghretos.MatcherSettings()


class TestParseNumberableUrl:
    """Test suite for the _parse_strict_url and _parse_unstrict_url functions."""

    # --- Basic Issues ---
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
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

    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        fragment=COMMENT_ID,
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
        url = f"https://github.com/{owner}/{repo_name}/issues/{number}#issue-{fragment}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.Issue)
        assert result.number == number

    # --- Basic Pull Requests ---
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
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
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
    )
    def test_basic_discussion(
        self,
        owner: str,
        repo_name: str,
        number: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing basic discussion URLs without strict type checking."""
        # With require_strict_type=False, discussions without fragments are supported
        url = f"https://github.com/{owner}/{repo_name}/discussions/{number}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.Discussion)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number

    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        fragment=COMMENT_ID,
    )
    def test_discussion_with_discussion_fragment(
        self,
        owner: str,
        repo_name: str,
        number: int,
        fragment: int,
        default_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing discussion URLs with #discussion-XXX fragments."""
        url = f"https://github.com/{owner}/{repo_name}/discussions/{number}#discussion-{fragment}"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert isinstance(result, ghretos.Discussion)
        assert result.number == number

    # --- Issue Comments ---
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        comment_id=COMMENT_ID,
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
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        comment_id=COMMENT_ID,
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
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        event_id=COMMENT_ID,
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
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        event_id=COMMENT_ID,
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
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        review_id=COMMENT_ID,
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
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        comment_id=COMMENT_ID,
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
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        sha=SHA,
        comment_id=COMMENT_ID,
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
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        comment_id=COMMENT_ID,
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
        url = f"https://github.com/{owner}/{repo_name}/pull/{number}/files#r{comment_id}"
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
    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(
        owner=USER,
        repo_name=REPO_NAME,
        number=NUMBERABLE,
        comment_id=COMMENT_ID,
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
    def test_invalid_number_not_digit(self, default_settings: ghretos.MatcherSettings) -> None:
        """Test that non-numeric issue numbers return None."""
        url = "https://github.com/owner/repo/issues/abc"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_invalid_comment_id_not_digit(self, default_settings: ghretos.MatcherSettings) -> None:
        """Test that non-numeric comment IDs return None."""
        url = "https://github.com/owner/repo/issues/123#issuecomment-abc"
        parsed_url = yarl.URL(url)

        result = parse_strict_url(parsed_url, settings=default_settings)

        assert result is None

    def test_invalid_sha_non_hex(self, default_settings: ghretos.MatcherSettings) -> None:
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

    def test_invalid_commits_without_sha(self, default_settings: ghretos.MatcherSettings) -> None:
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


class TestParseUnstrictUrl:
    """Test suite for the _parse_unstrict_url function with require_strict_type=False."""

    @pytest.fixture
    def unstrict_settings(self) -> ghretos.MatcherSettings:
        """Fixture providing settings with strict type checking disabled."""
        return ghretos.MatcherSettings(require_strict_type=False)

    # --- Basic Numberable Resources ---
    @pytest.mark.parametrize(
        ("url", "expected_type"),
        [
            ("https://github.com/owner/repo/issues/123", ghretos.Issue),
            ("https://github.com/owner/repo/pull/456", ghretos.PullRequest),
            ("https://github.com/owner/repo/discussions/789", ghretos.Discussion),
        ],
    )
    def test_basic_numberable_resources(
        self, url: str, expected_type: type, unstrict_settings: ghretos.MatcherSettings
    ) -> None:
        """Test parsing basic numberable resources without fragments."""
        parsed_url = yarl.URL(url)
        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)
        assert isinstance(result, expected_type)

    # --- User and Repo ---
    @pytest.mark.parametrize(
        ("url", "expected_type"),
        [
            ("https://github.com/owner", ghretos.User),
            ("https://github.com/owner/repo", ghretos.Repo),
        ],
    )
    def test_user_and_repo(
        self, url: str, expected_type: type, unstrict_settings: ghretos.MatcherSettings
    ) -> None:
        """Test parsing user and repo URLs."""
        parsed_url = yarl.URL(url)
        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)
        assert isinstance(result, expected_type)

    # --- Issue and Discussion Fragments on Different Resource Types ---
    @pytest.mark.parametrize(
        ("url", "expected_type"),
        [
            # #issue- fragments
            ("https://github.com/owner/repo/issues/123#issue-123", ghretos.Issue),
            ("https://github.com/owner/repo/pull/456#issue-456", ghretos.PullRequest),
            # #discussion- fragments
            (
                "https://github.com/owner/repo/discussions/789#discussion-789",
                ghretos.Discussion,
            ),
            (
                "https://github.com/owner/repo/issues/111#discussion-111",
                ghretos.Discussion,
            ),
            (
                "https://github.com/owner/repo/pull/222#discussion-222",
                ghretos.Discussion,
            ),
        ],
    )
    def test_issue_and_discussion_fragments(
        self, url: str, expected_type: type, unstrict_settings: ghretos.MatcherSettings
    ) -> None:
        """Test parsing URLs with #issue- and #discussion- fragments on various resource types."""
        parsed_url = yarl.URL(url)
        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)
        assert isinstance(result, expected_type)

    # --- Pull Request Reviews with Different Prefixes ---
    @pytest.mark.parametrize(
        ("url", "expected_type"),
        [
            (
                "https://github.com/owner/repo/issues/123#pullrequestreview-456",
                ghretos.PullRequestReview,
            ),
            (
                "https://github.com/owner/repo/pull/123#pullrequestreview-456",
                ghretos.PullRequestReview,
            ),
            (
                "https://github.com/owner/repo/discussions/123#pullrequestreview-456",
                ghretos.PullRequestReview,
            ),
            (
                "https://github.com/owner/repo/issues/123#discussion_r456",
                ghretos.PullRequestReviewComment,
            ),
            (
                "https://github.com/owner/repo/pull/123#discussion_r456",
                ghretos.PullRequestReviewComment,
            ),
            (
                "https://github.com/owner/repo/discussions/123#discussion_r456",
                ghretos.PullRequestReviewComment,
            ),
        ],
    )
    def test_pull_request_review_comment_fragments(
        self,
        url: str,
        expected_type: type,
        unstrict_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing PR review comments on various resource types."""
        parsed_url = yarl.URL(url)
        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)
        assert isinstance(result, expected_type)

    # --- Commits and Files Pages with /issues/ URLs ---
    @pytest.mark.parametrize(
        ("url", "expected_sha", "expected_commit_page", "expected_files_page"),
        [
            (
                "https://github.com/owner/repo/issues/123/commits/abc123#r456",
                "abc123",
                True,
                False,
            ),
            (
                "https://github.com/owner/repo/pull/123/commits/def456#r789",
                "def456",
                True,
                False,
            ),
            ("https://github.com/owner/repo/issues/123/files#r456", None, False, True),
            ("https://github.com/owner/repo/pull/123/files#r789", None, False, True),
        ],
    )
    def test_commits_and_files_pages(
        self,
        url: str,
        expected_sha: str | None,
        expected_commit_page: bool,
        expected_files_page: bool,
        unstrict_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing commits and files pages, including /issues/ URLs converted to PR type."""
        parsed_url = yarl.URL(url)
        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)

        assert isinstance(result, ghretos.PullRequestReviewComment)
        assert result.sha == expected_sha
        assert result.commit_page == expected_commit_page
        assert result.files_page == expected_files_page

    # --- Invalid Inputs ---
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/owner/repo/issues/abc",  # Non-numeric number
            "https://github.com/owner/repo/issues/123/commits/xyz#r456",  # Non-hex SHA
            "https://github.com/owner/repo/issues/123#unknown-fragment",  # Unknown fragment
        ],
    )
    def test_invalid_inputs(self, url: str, unstrict_settings: ghretos.MatcherSettings) -> None:
        """Test that invalid inputs return None."""
        parsed_url = yarl.URL(url)
        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)
        assert result is None

    # --- Settings Tests ---
    def test_disabled_issues(self) -> None:
        """Test that issues are not parsed when disabled."""
        settings = ghretos.MatcherSettings(require_strict_type=False, issues=False)
        url = "https://github.com/owner/repo/issues/123"
        parsed_url = yarl.URL(url)

        result = parse_unstrict_url(parsed_url, settings=settings)

        assert result is None

    def test_disabled_pull_requests(self) -> None:
        """Test that pull requests are not parsed when disabled."""
        settings = ghretos.MatcherSettings(require_strict_type=False, pull_requests=False)
        url = "https://github.com/owner/repo/pull/123"
        parsed_url = yarl.URL(url)

        result = parse_unstrict_url(parsed_url, settings=settings)

        assert result is None

    def test_disabled_discussions(self) -> None:
        """Test that discussions are not parsed when disabled."""
        settings = ghretos.MatcherSettings(require_strict_type=False, discussions=False)
        url = "https://github.com/owner/repo/discussions/123"
        parsed_url = yarl.URL(url)

        result = parse_unstrict_url(parsed_url, settings=settings)

        assert result is None

    def test_disabled_pull_request_review_comments(self) -> None:
        """Test that PR review comments are not parsed when disabled."""
        settings = ghretos.MatcherSettings(
            require_strict_type=False, pull_request_review_comments=False
        )
        url = "https://github.com/owner/repo/issues/123/files#r456"
        parsed_url = yarl.URL(url)

        result = parse_unstrict_url(parsed_url, settings=settings)

        assert result is None

    # --- Cross-Type Fragment Support ---
    def test_issue_fragment_on_pull_url(self, unstrict_settings: ghretos.MatcherSettings) -> None:
        """Test that #issue- fragment on /pull/ URL returns PullRequest."""
        url = "https://github.com/owner/repo/pull/123#issue-123"
        parsed_url = yarl.URL(url)

        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)

        assert isinstance(result, ghretos.PullRequest)
        assert result.number == 123

    def test_discussion_fragment_on_issue_url(
        self, unstrict_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that #discussion- fragment on /issues/ URL returns Discussion."""
        url = "https://github.com/owner/repo/issues/456#discussion-456"
        parsed_url = yarl.URL(url)

        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)

        assert isinstance(result, ghretos.Discussion)
        assert result.number == 456

    # --- Edge Cases ---
    def test_multiple_resource_types_with_same_number(
        self, unstrict_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that different URL patterns for same number return appropriate types."""
        number = 42

        # Issue
        url_issue = f"https://github.com/owner/repo/issues/{number}"
        result_issue = parse_unstrict_url(yarl.URL(url_issue), settings=unstrict_settings)
        assert isinstance(result_issue, ghretos.Issue)
        assert result_issue.number == number

        # Pull Request
        url_pr = f"https://github.com/owner/repo/pull/{number}"
        result_pr = parse_unstrict_url(yarl.URL(url_pr), settings=unstrict_settings)
        assert isinstance(result_pr, ghretos.PullRequest)
        assert result_pr.number == number

        # Discussion
        url_disc = f"https://github.com/owner/repo/discussions/{number}"
        result_disc = parse_unstrict_url(yarl.URL(url_disc), settings=unstrict_settings)
        assert isinstance(result_disc, ghretos.Discussion)
        assert result_disc.number == number

    def test_fallback_to_none_for_unsupported_patterns(
        self, unstrict_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that unsupported URL patterns return None."""
        unsupported_urls = [
            "https://github.com/owner/repo/tree/main",
            "https://github.com/owner/repo/blob/main/file.py",
            "https://github.com/owner/repo/wiki",
            "https://github.com/owner/repo/issues/123/something/invalid",
        ]

        for url in unsupported_urls:
            result = parse_unstrict_url(yarl.URL(url), settings=unstrict_settings)
            assert result is None, f"Expected None for {url}"

    # --- Issue and Discussion Comments ---
    @pytest.mark.parametrize(
        ("url", "expected_type", "expected_comment_id"),
        [
            (
                "https://github.com/owner/repo/issues/123#issuecomment-789",
                ghretos.IssueComment,
                789,
            ),
            (
                "https://github.com/owner/repo/pull/123#issuecomment-456",
                ghretos.PullRequestComment,
                456,
            ),
            (
                "https://github.com/owner/repo/discussions/123#discussioncomment-555",
                ghretos.DiscussionComment,
                555,
            ),
            (
                "https://github.com/owner/repo/pull/123#discussioncomment-789",
                ghretos.DiscussionComment,
                789,
            ),
            (
                "https://github.com/owner/repo/pull/123#discussioncomment-456",
                ghretos.DiscussionComment,
                456,
            ),
            (
                "https://github.com/owner/repo/discussions/123#issuecomment-555",
                ghretos.IssueComment,
                555,
            ),
        ],
    )
    def test_issue_and_discussion_comments(
        self,
        url: str,
        expected_type: type[ghretos.IssueComment]
        | type[ghretos.PullRequestComment]
        | type[ghretos.DiscussionComment],
        expected_comment_id: int,
        unstrict_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test parsing issue, pull request, and discussion comments in unstrict mode."""
        parsed_url = yarl.URL(url)
        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)
        assert result is not None
        assert isinstance(result, expected_type)
        assert result.comment_id == expected_comment_id


class TestShorthand:
    @given(owner=USER, repo_name=REPO_NAME, number=NUMBERABLE)
    def test_shorthand_numberable(self, owner: str, repo_name: str, number: int) -> None:
        """Test parsing shorthand issue notation."""
        shorthand = f"{owner}/{repo_name}#{number}"
        result = ghretos.parse_shorthand(shorthand)

        assert isinstance(result, ghretos.NumberedResource)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.number == number

    @given(owner=USER, repo_name=REPO_NAME, ref=REF)
    def test_shorthand_ref(self, owner: str, repo_name: str, ref: str) -> None:
        """Test parsing shorthand issue notation."""
        shorthand = f"{owner}/{repo_name}@{ref}"
        result = ghretos.parse_shorthand(shorthand)

        assert isinstance(result, ghretos.Ref)
        assert result.repo == ghretos.Repo(name=repo_name, owner=owner)
        assert result.ref == ref
