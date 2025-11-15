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
    pass


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
    pass


@dataclass_deco
class IssueComment(_Issue):
    comment_id: int
    """The ID of the comment."""


@dataclass_deco
class IssueEvent(_Issue):
    event_id: int
    """The ID of the event."""


## PULL REQUESTS


@dataclass_deco
class _PullRequest(GitHubResource):
    repo: Repo
    number: int
    """The number of the pull request."""


@dataclass_deco
class PullRequest(_PullRequest):
    pass


@dataclass_deco
class PullRequestComment(_PullRequest):
    comment_id: int
    """The ID of the comment."""


@dataclass_deco
class PullRequestReview(_PullRequest):
    review_id: int


@dataclass_deco
class PullRequestReviewComment(_PullRequest):
    comment_id: int

    # these comments are special and can live on multiple pages:
    # pull/<num>/commits/<sha>#r<ID>
    # pull/files#r<ID>
    sha: str | None = None
    commit_page: bool = False
    files_page: bool = False


@dataclass_deco
class PullRequestEvent(_PullRequest):
    event_id: int


### DISCUSSIONS


@dataclass_deco
class _Discussion(GitHubResource):
    repo: Repo
    number: int


@dataclass_deco
class Discussion(_Discussion):
    repo: Repo
    number: int


@dataclass_deco
class DiscussionComment(_Discussion):
    comment_id: int


## COMMITS


@dataclass_deco
class _Commit(GitHubResource):
    repo: Repo
    sha: str


@dataclass_deco
class Commit(_Commit):
    pass


@dataclass_deco
class CommitComment(_Commit):
    comment_id: int


@dataclass_deco
class ReleaseTag(GitHubResource):
    repo: Repo
    tag: str


@dataclasses.dataclass
class MatcherSettings:
    domains: list[str] = dataclasses.field(default_factory=lambda: ["github.com"])
    issues: bool = True
    issue_comments: bool = True
    issue_events: bool = True
    pull_requests: bool = True
    pull_request_comments: bool = True
    pull_request_reviews: bool = True
    pull_request_review_comments: bool = True
    pull_request_events: bool = True
    discussions: bool = True
    discussion_comments: bool = True
    commits: bool = True
    commit_comments: bool = True
    releases: bool = True

    shorthand: bool = True
    short_repo: bool = True
    short_numberables: bool = True
    short_refs: bool = True

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
