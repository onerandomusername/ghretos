import dataclasses
import functools
from typing import TYPE_CHECKING, Literal


__all__ = (
    "Commit",
    "CommitComment",
    "Discussion",
    "DiscussionComment",
    "GitHubResource",
    "Issue",
    "IssueComment",
    "IssueEvent",
    "MatcherSettings",
    "NumberedResource",
    "PullRequest",
    "PullRequestComment",
    "PullRequestEvent",
    "PullRequestReview",
    "PullRequestReviewComment",
    "ReleaseTag",
    "Repo",
    "User",
)

if TYPE_CHECKING:
    from typing_extensions import Self


if TYPE_CHECKING:
    dataclass_deco = dataclasses.dataclass
else:
    dataclass_deco = functools.partial(
        dataclasses.dataclass,
        order=True,
        kw_only=True,
        frozen=True,
    )


class GitHubResource:
    """Base class for all GitHub resources."""


@dataclass_deco
class User(GitHubResource):
    """Represents a GitHub user."""

    login: str
    """The username/login of the GitHub user."""


@dataclass_deco
class Repo(GitHubResource):
    name: str
    """The name of the repository."""

    # flattened user
    owner: str
    """The owner of the repository."""

    @property
    def full_name(self) -> str:
        """Return the full name of the repository in the format 'owner/name'."""
        return f"{self.owner}/{self.name}"

    @property
    def html_url(self) -> str:
        """Return the HTML URL of the repository. Note this only supports GitHub.com for now."""
        return f"https://github.com/{self.full_name}"


@dataclass_deco
class NumberedResource(GitHubResource):
    """Special base class for resources with numbers.

    This is used for shorthand parsing for numbered resources, where the specific type is not known.

    This can represent either a :py:class:`Issue`, :py:class:`PullRequest`, or
    :py:class:`Discussion`.
    """

    repo: Repo
    """The repository the resource belongs to."""
    number: int
    """The number of the resource."""


## ISSUES
@dataclass_deco
class _Issue(GitHubResource):
    repo: Repo
    """The repository the issue belongs to."""
    number: int
    """The number of the issue."""


@dataclass_deco
class Issue(_Issue):
    """Represents a GitHub issue."""

    repo: Repo
    number: int


@dataclass_deco
class IssueComment(_Issue):
    repo: Repo
    number: int

    comment_id: int
    """The ID of the comment."""


@dataclass_deco
class IssueEvent(_Issue):
    repo: Repo
    number: int

    event_id: int
    """The ID of the event."""


## PULL REQUESTS


@dataclass_deco
class _PullRequest(GitHubResource):
    repo: Repo
    """The repository the pull request belongs to."""
    number: int
    """The number of the pull request."""


@dataclass_deco
class PullRequest(_PullRequest):
    """Represents a GitHub pull request."""

    repo: Repo
    number: int


@dataclass_deco
class PullRequestComment(_PullRequest):
    """Represents a comment on a GitHub pull request."""

    repo: Repo
    number: int

    comment_id: int
    """The ID of the comment."""


@dataclass_deco
class PullRequestReview(_PullRequest):
    """Represents a review on a GitHub pull request."""

    repo: Repo
    number: int

    review_id: int
    """The ID of the review."""


@dataclass_deco
class PullRequestReviewComment(_PullRequest):
    """Represents a review comment on a GitHub pull request."""

    repo: Repo
    number: int

    comment_id: int
    """The ID of the review comment."""

    # these comments are special and can live on multiple pages:
    # pull/<num>/commits/<sha>#r<ID>
    # pull/files#r<ID>
    sha: str | None = None
    """The SHA of the commit the comment is on, if applicable."""
    commit_page: bool = False
    """Whether the comment was found on a commit page."""
    files_page: bool = False
    """Whether the comment was found on the files page."""


@dataclass_deco
class PullRequestEvent(_PullRequest):
    """Represents an event on a GitHub pull request."""

    repo: Repo
    number: int

    event_id: int
    """The ID of the event."""


### DISCUSSIONS


@dataclass_deco
class _Discussion(GitHubResource):
    repo: Repo
    """The repository the discussion belongs to."""
    number: int
    """The number of the discussion."""


@dataclass_deco
class Discussion(_Discussion):
    """Represents a GitHub discussion."""

    repo: Repo
    number: int


@dataclass_deco
class DiscussionComment(_Discussion):
    """Represents a comment on a GitHub discussion."""

    repo: Repo
    number: int

    comment_id: int
    """The ID of the comment."""


## COMMITS


@dataclass_deco
class _Commit(GitHubResource):
    repo: Repo
    """The repository the commit belongs to."""
    sha: str
    """The SHA of the commit."""


@dataclass_deco
class Commit(_Commit):
    """Represents a GitHub commit."""

    repo: Repo
    sha: str


@dataclass_deco
class CommitComment(_Commit):
    """Represents a comment on a GitHub commit."""

    repo: Repo
    sha: str

    comment_id: int
    """The ID of the comment."""


@dataclass_deco
class ReleaseTag(GitHubResource):
    """Represents a GitHub release tag."""

    repo: Repo
    """The repository the release belongs to."""
    tag: str
    """The tag name of the release."""


@dataclasses.dataclass
class MatcherSettings:
    """Settings for matching GitHub URLs and shorthands.

    Each of these settings are completely seperate: disabling one does not affect the others.
    For example, disabling `issues` will not disable `issue_comments`.
    """

    domains: list[str] = dataclasses.field(default_factory=lambda: ["github.com"])
    """List of domains to consider as GitHub domains."""
    issues: bool = True
    """Whether to match ``/owner/repo/issues/{number}`` URLs."""
    issue_comments: bool = True
    """Whether to match ``/owner/repo/issues/{number}#issuecomment-{number}`` issue comment URLs."""
    issue_events: bool = True
    """Whether to match ``/owner/repo/issues/{number}#event-{number}`` issue event URLs."""
    pull_requests: bool = True
    """Whether to match ``/owner/repo/pull/{number}`` URLs."""
    pull_request_comments: bool = True
    """Whether to match ``/owner/repo/pull/{number}#issuecomment-{number}``
    pull request comment URLs."""
    pull_request_reviews: bool = True
    """Whether to match ``/owner/repo/pull/{number}#review-{number}`` pull request review URLs."""
    pull_request_review_comments: bool = True
    """Whether to match ``/owner/repo/pull/{number}#pullrequestreviewcomment-{number}``
    pull request review comment URLs."""
    pull_request_events: bool = True
    """Whether to match ``/owner/repo/pull/{number}#event-{number}`` pull request event URLs."""
    discussions: bool = True
    """Whether to match ``/owner/repo/discussions/{number}`` URLs."""
    discussion_comments: bool = True
    """Whether to match ``/owner/repo/discussions/{number}#discussioncomment-{number}``
    discussion comment URLs."""
    commits: bool = True
    """Whether to match ``/owner/repo/commit/{sha}`` URLs."""
    commit_comments: bool = True
    """Whether to match ``/owner/repo/commit/{sha}#commitcomment-{number}`` commit comment URLs."""
    releases: bool = True
    """Whether to match ``/owner/repo/releases/tag/{tag}`` URLs."""

    shorthand: bool = True
    """Whether to match shorthand notations like `owner/repo#number`.
    UNLIKE other setting, this is required to enable shorthand parsing."""
    short_repo: bool = True
    """Whether to support short repository names in shorthands (e.g., `repo#number`)."""
    short_numberables: bool = True
    """Whether to support shorthand notations such as ``owner/repo#number``."""
    short_refs: bool = True
    """Whether to support shorthand notations such as ``owner/repo@ref``."""

    require_strict_type: bool = True
    """Whether to support /issues/, /pulls/, and /discussions/ only for their respective types.
    If this is False, issues, pulls, and discussions will be ignored if the fragment indicates a
    type only supported by another resource.
    """

    @classmethod
    def none(cls) -> "Self":
        """Return a MatcherSettings instance with all resource types disabled."""
        return cls(
            issues=False,
            issue_comments=False,
            issue_events=False,
            pull_requests=False,
            pull_request_comments=False,
            pull_request_reviews=False,
            pull_request_review_comments=False,
            pull_request_events=False,
            discussions=False,
            discussion_comments=False,
            commits=False,
            commit_comments=False,
            releases=False,
            shorthand=False,
            short_repo=False,
            short_numberables=False,
            short_refs=False,
        )

    def _supported_resource_types(
        self,
    ) -> set[Literal["issues", "pull", "discussions", "commit", "releases"]]:
        types: set[Literal["issues", "pull", "discussions", "commit", "releases"]] = set()
        if self.issues:
            types.add("issues")
        if self.pull_requests:
            types.add("pull")
        if self.discussions:
            types.add("discussions")
        if self.commits:
            types.add("commit")
        if self.releases:
            types.add("releases")
        return types
