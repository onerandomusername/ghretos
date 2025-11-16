import string
import unittest.mock
from collections.abc import Callable

import hypothesis
import pytest
import yarl
from hypothesis import given, settings
from hypothesis import strategies as st

import ghretos
from ghretos import parsing
from ghretos.parsing import (
    _parse_loose_numberable_url as parse_unstrict_url,  # pyright: ignore[reportPrivateUsage]
)
from ghretos.parsing import (
    _parse_strict_numberable_url as parse_strict_url,  # pyright: ignore[reportPrivateUsage]
)
from ghretos.parsing import (
    _validate_ref as validate_ref,  # pyright: ignore[reportPrivateUsage]
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
REF = st.text(string.ascii_letters + string.digits + "-._/", min_size=1).filter(
    lambda s: not s.endswith(("/", "."))
    and not s.startswith(("/", "."))
    and ".." not in s
    and "//" not in s
)
COMMENT_ID = st.integers(min_value=1)


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


class TestLooseNumberableUrl:
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

    # --- Commits and Files Pages on Pull Requests ---
    @pytest.mark.parametrize(
        ("url", "expected_sha", "expected_commit_page", "expected_files_page"),
        [
            (
                "https://github.com/owner/repo/pull/123/commits/def456#r789",
                "def456",
                True,
                False,
            ),
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

    @settings(suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    @given(number=st.integers(min_value=1), fragment_number=st.integers(min_value=1))
    @pytest.mark.parametrize("resource_type", ["issues", "pull", "discussions"])
    @pytest.mark.parametrize(
        ("fragment_front", "expected_callable"),
        [
            (
                "issue-",
                lambda resource_type: ghretos.Issue  # pyright: ignore[reportUnknownLambdaType]
                if resource_type != "pull"
                else ghretos.PullRequest,
            ),
            ("discussion-", lambda _: ghretos.Discussion),  # pyright: ignore[reportUnknownLambdaType]
            ("pullrequestreview-", lambda _: ghretos.PullRequestReview),  # pyright: ignore[reportUnknownLambdaType]
            ("discussion_r", lambda _: ghretos.PullRequestReviewComment),  # pyright: ignore[reportUnknownLambdaType]
            (
                "issuecomment-",
                lambda resource_type: ghretos.IssueComment  # pyright: ignore[reportUnknownLambdaType]
                if resource_type != "pull"
                else ghretos.PullRequestComment,
            ),
            ("discussioncomment-", lambda _: ghretos.DiscussionComment),  # pyright: ignore[reportUnknownLambdaType]
        ],  # type: ignore
    )
    def test_fragment_priority(
        self,
        resource_type: str,
        number: str,
        fragment_front: str,
        fragment_number: int,
        expected_callable: Callable[[str], type[ghretos.GitHubResource]],
        unstrict_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test that fragments take priority over the main resource type."""
        url = f"https://github.com/owner/repo/{resource_type}/{number}#{fragment_front}{fragment_number}"
        parsed_url = yarl.URL(url)
        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)
        expected_type = expected_callable(resource_type)
        assert isinstance(result, expected_type)

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/owner/repo/tree/main",
            "https://github.com/owner/repo/blob/main/file.py",
            "https://github.com/owner/repo/wiki",
            "https://github.com/owner/repo/issues/123/something/invalid",
        ],
    )
    def test_fallback_to_none_for_unsupported_patterns(
        self, url: str, unstrict_settings: ghretos.MatcherSettings
    ) -> None:
        """Test that unsupported URL patterns return None."""
        result = parse_unstrict_url(yarl.URL(url), settings=unstrict_settings)
        assert result is None

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

    @pytest.mark.parametrize("number", ["hi", "234h", "!!", "0x3", "3f"])
    @pytest.mark.parametrize(
        "fragment",
        ["issuecomment-", "discussioncomment-", "pullrequestreview-", "discussion_r", "event-"],
    )
    @pytest.mark.parametrize("resource_type", ["issues", "pull", "discussions"])
    @pytest.mark.parametrize(
        ("owner", "repo"),
        [
            ("owner", "repo"),
            ("hi", "bob"),
        ],
    )
    def test_invalid_resource_id(
        self,
        owner: str,
        repo: str,
        resource_type: str,
        number: str,
        fragment: str,
        unstrict_settings: ghretos.MatcherSettings,
    ) -> None:
        """Test that invalid resource IDs return None."""
        url = f"https://github.com/{owner}/{repo}/{resource_type}/{number}"
        parsed_url = yarl.URL(url)
        result = parse_unstrict_url(parsed_url, settings=unstrict_settings)
        assert result is None


class TestParseUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "h",
            "https://notgithub.com/owner/repo/issues/1",
            "http://example.com/../owner/repo",
            "https://api.github.com/owner/repo",
            "/../owner/repo",
            "../owner/repo",
            yarl.URL("/"),
        ],
    )
    def test_parse_github_url_empty(self, url: str | yarl.URL) -> None:
        resource = ghretos.parse_url(url)
        assert resource is None

    @given(owner=USER)
    def test_parse_github_url_user(
        self,
        owner: str,
    ) -> None:
        url = f"https://github.com/{owner}"
        original = parsing._valid_user  # pyright: ignore[reportPrivateUsage]
        with unittest.mock.patch.object(
            parsing, "_valid_user", unittest.mock.Mock(side_effect=original)
        ) as mock:
            resource = ghretos.parse_url(url)
            mock.assert_called_once_with(owner)
        assert isinstance(resource, ghretos.User)

    @given(repo=REPO_NAME)
    @pytest.mark.parametrize("owner", ["github", "octocat", "0x", "0"])
    def test_parse_github_url_repo(
        self,
        owner: str,
        repo: str,
    ) -> None:
        url = f"https://github.com/{owner}/{repo}"
        resource = ghretos.parse_url(url)
        original_user = parsing._valid_user  # pyright: ignore[reportPrivateUsage]
        original_repo = parsing._valid_repository  # pyright: ignore[reportPrivateUsage]
        with (
            unittest.mock.patch.object(
                parsing, "_valid_user", unittest.mock.Mock(side_effect=original_user)
            ) as user_mock,
            unittest.mock.patch.object(
                parsing, "_valid_repository", unittest.mock.Mock(side_effect=original_repo)
            ) as repo_mock,
        ):
            resource = ghretos.parse_url(url)
            user_mock.assert_called_once_with(owner)
            repo_mock.assert_called_once_with(repo)
        assert isinstance(resource, ghretos.Repo)

    @given(owner=USER, repo=REPO_NAME, number=NUMBERABLE)
    @pytest.mark.parametrize(
        ("resource_type", "expected_type"),
        [
            ("issues", ghretos.Issue),
            ("pull", ghretos.PullRequest),
            ("discussions", ghretos.Discussion),
        ],
    )
    def test_parse_github_url_numberables(
        self,
        owner: str,
        repo: str,
        number: int,
        resource_type: str,
        expected_type: type[ghretos.GitHubResource],
    ) -> None:
        url = f"https://github.com/{owner}/{repo}/{resource_type}/{number}"
        resource = ghretos.parse_url(url)
        assert isinstance(resource, expected_type)

    @given(owner=USER, repo=REPO_NAME, number=NUMBERABLE, fragment_id=COMMENT_ID)
    @pytest.mark.parametrize("resource_type", ["issues", "pull", "discussions"])
    @pytest.mark.parametrize(
        ("fragment_front", "expected_callable"),
        [
            (
                "issue-",
                lambda resource_type: ghretos.Issue
                if resource_type != "pull"
                else ghretos.PullRequest,  # pyright: ignore[reportUnknownLambdaType]
            ),
            ("discussion-", lambda _: ghretos.Discussion),  # pyright: ignore[reportUnknownLambdaType]
            ("pullrequestreview-", lambda _: ghretos.PullRequestReview),  # pyright: ignore[reportUnknownLambdaType]
            ("discussion_r", lambda _: ghretos.PullRequestReviewComment),  # pyright: ignore[reportUnknownLambdaType]
            (
                "issuecomment-",
                lambda resource_type: ghretos.IssueComment  # pyright: ignore[reportUnknownLambdaType]
                if resource_type != "pull"
                else ghretos.PullRequestComment,
            ),
            ("discussioncomment-", lambda _: ghretos.DiscussionComment),  # pyright: ignore[reportUnknownLambdaType]
            pytest.param(
                "event-",
                lambda resource_type: ghretos.IssueEvent
                if resource_type != "pull"
                else ghretos.PullRequestEvent,
                marks=pytest.mark.xfail(reason="event parsing is not implemented yet"),
            ),
            pytest.param(
                "issue-asdfj", lambda _: None, marks=pytest.mark.skip("Not implemented yet")
            ),  # pyright: ignore[reportUnknownLambdaType]
            ("unfetteredcomment-", lambda _: None),  # pyright: ignore[reportUnknownLambdaType]
        ],  # type: ignore
    )
    def test_parse_github_url_fragments(
        self,
        owner: str,
        repo: str,
        number: int,
        resource_type: str,
        fragment_front: str,
        fragment_id: int,
        expected_callable: Callable[[str], type[ghretos.GitHubResource] | None],
    ) -> None:
        settings = ghretos.MatcherSettings(require_strict_type=False)
        url = f"https://github.com/{owner}/{repo}/{resource_type}/{number}#{fragment_front}{fragment_id}"
        resource = ghretos.parse_url(url, settings=settings)
        expected_model = expected_callable(resource_type)
        if expected_model is None:
            assert resource is None
        else:
            assert isinstance(resource, expected_model)

    @given(
        owner=USER,
        repo=REPO_NAME,
        number=st.text(),
        fragment_id=st.text().filter(lambda s: all(c not in string.digits for c in s)),
    )
    @pytest.mark.parametrize("resource_type", ["issues", "pull", "discussions"])
    @pytest.mark.parametrize(
        ("fragment_front"),
        [
            "pullrequestreview-",
            "discussion_r",
            "issuecomment-",
            "discussioncomment-",
            "event-",
        ],
    )
    def test_parse_github_url_fragment_non_number(
        self,
        owner: str,
        repo: str,
        number: int,
        resource_type: str,
        fragment_front: str,
        fragment_id: str,
    ) -> None:
        settings = ghretos.MatcherSettings(require_strict_type=False)
        url = f"https://github.com/{owner}/{repo}/{resource_type}/{number}#{fragment_front}{fragment_id}"
        resource = ghretos.parse_url(url, settings=settings)
        assert resource is None

    @given(
        owner=USER,
        repo=REPO_NAME,
        numberable=NUMBERABLE,
        fragment_value=st.text().filter(lambda s: all(c not in string.digits for c in s)),
    )
    @pytest.mark.parametrize("resource_type", ["issues", "pull", "discussions"])
    @pytest.mark.parametrize(
        "fragment",
        [
            "issuecomment-",
            "pullrequestreview-",
            "discussioncomment-",
            "discussion_r",
            "r",
            "whatever",
        ],
    )
    def test_invalid_fragments(
        self,
        owner: str,
        repo: str,
        numberable: int,
        resource_type: str,
        fragment: str,
        fragment_value: str,
    ) -> None:
        """Test that invalid fragments return None."""
        url = f"https://github.com/{owner}/{repo}/{resource_type}/{numberable}#{fragment}{fragment_value}"
        result = ghretos.parse_url(url)
        assert result is None


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

    @given(owner=USER, repo_name=REPO_NAME)
    def test_shorthand_repo(self, owner: str, repo_name: str) -> None:
        """Test parsing shorthand repo notation."""
        shorthand = f"{owner}/{repo_name}"
        result = ghretos.parse_shorthand(shorthand)

        assert isinstance(result, ghretos.Repo)
        assert result.name == repo_name
        assert result.owner == owner

    @pytest.mark.parametrize(
        "shorthand",
        [
            "ownerrepo#123",
            "ownerrepo#",
            "owner/repo#",
            "owner/repo@",
            "owner/repo#abc",
            "justastring",
        ],
    )
    def test_invalid_shorthand(self, shorthand: str) -> None:
        """Test invalid shorthand notations return None."""
        result = ghretos.parse_shorthand(shorthand)
        assert result is None

    @given(
        owner=USER,
        repo=REPO_NAME,
        number=st.one_of(
            st.text(min_size=1).filter(lambda s: all(c not in string.digits for c in s)),
            st.just(""),
            st.just("@"),
            st.just("0"),
        ),
    )
    def test_invalid_numberable(self, owner: str, repo: str, number: str) -> None:
        """Test invalid numberable shorthand return None."""
        shorthand = f"{owner}/{repo}#{number}"
        result = ghretos.parse_shorthand(shorthand)
        assert result is None

    @given(
        ref=st.one_of(
            st.just(""),
            st.text(min_size=1).filter(lambda x: " " in x),
            *[st.just(x) for x in ["~", "^", "?", "..", ":", "//", "\\"]],
            st.just("@"),
            st.just("fix/hi./test"),
            st.just("fix/h i/test"),
            st.just("fix//double"),
            st.just("fix/tests.lock"),
            st.just("fix/rip.lock/testing"),
            st.just("fix/.keep/testing"),
            st.just(".lock"),
        ),
    )
    def test_invalid_ref(self, ref: str) -> None:
        """Test invalid ref return None."""
        result = validate_ref(ref)
        assert result is False
