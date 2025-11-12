import collections
import dataclasses
import functools
import string
from typing import TYPE_CHECKING, Literal

import yarl

if TYPE_CHECKING:
    from typing_extensions import Self


__all__ = (
    "GitHubResource",
    "User",
    "Repo",
    "Issue",
    "IssueComment",
    "IssueEvent",
    "PullRequest",
    "PullRequestComment",
    "PullRequestReview",
    "PullRequestReviewComment",
    "PullRequestEvent",
    "Discussion",
    "DiscussionComment",
    "Commit",
    "CommitComment",
    "ReleaseTag",
    "MatcherSettings",
    "parse_url",
    "parse_shorthand",
)

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
    login: str


@dataclass_deco
class Repo(GitHubResource):
    name: str

    # flattened user
    owner: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def html_url(self) -> str:
        return f"https://github.com/{self.full_name}"


@dataclass_deco
class NumberedResource(GitHubResource):
    """Special base class for resources with numbers.

    This is used for shorthand parsing for numbered resources, where the specific type is not known."""

    repo: Repo
    number: int


## ISSUES
@dataclass_deco
class _Issue(GitHubResource):
    repo: Repo
    number: int


@dataclass_deco
class Issue(_Issue):
    pass


@dataclass_deco
class IssueComment(_Issue):
    comment_id: int


@dataclass_deco
class IssueEvent(_Issue):
    event_id: int


## PULL REQUESTS


@dataclass_deco
class _PullRequest(GitHubResource):
    repo: Repo
    number: int


@dataclass_deco
class PullRequest(_PullRequest):
    pass


@dataclass_deco
class PullRequestComment(_PullRequest):
    comment_id: int


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
    If this is False, issues, pulls, and discussions will be ignored if the fragment indicates a type only supported by another resource.
    """

    @classmethod
    def none(cls) -> "Self":
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
        types: set[Literal["issues", "pull", "discussions", "commit", "releases"]] = (
            set()
        )
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


_DEFAULT_MATCHER_SETTINGS = MatcherSettings()


def _get_id_from_fragment(url: yarl.URL, prefix: str) -> str | None:
    fragment = url.fragment
    if fragment.startswith(prefix):
        return fragment[len(prefix) :]
    return None


def _parse_numberable_url(
    *,
    parsed_url: yarl.URL,
    parts: collections.deque[str],
    repo: Repo,
    settings: MatcherSettings,
    resource_type: Literal["issues", "pull", "discussions"],
) -> GitHubResource | None:
    """Parses a numbered resource URL into its corresponding resource.

    This is used for shorthand parsing for numbered resources, where the specific type is not known.
    """
    path_number = parts.popleft()
    if not path_number.isdigit():
        return None
    number = int(path_number)
    if parts:
        # parts doesn't properly redirect to other resource types, but the fragment may indicate a different type
        # Importantly, additional parts are only supported on pull requests, and GitHub frontend does not redirect additional parts
        next_part = parts.popleft()
        if next_part not in ("commits", "files"):
            return None
        if resource_type != "pull" and settings.require_strict_type:
            return None
        resource_type = "pull"
        # The only thing that works on these pages is pull request review comments
        settings = dataclasses.replace(
            settings,
            require_strict_type=True,
        )
    else:
        next_part = None

    fragment = None
    if not parsed_url.fragment or parsed_url.fragment.startswith(
        ("issue-", "discussion-")
    ):
        if fragment:
            if fragment.startswith("issue-"):
                # must be a pull or issue
                if resource_type == "issues":
                    return Issue(repo=repo, number=number) if settings.issues else None
                elif resource_type == "pull":
                    return (
                        PullRequest(repo=repo, number=number)
                        if settings.pull_requests
                        else None
                    )
            if fragment.startswith("discussion-"):
                if resource_type != "discussions" and settings.require_strict_type:
                    return None
                return (
                    Discussion(repo=repo, number=number)
                    if settings.discussions
                    else None
                )
        elif resource_type == "pull":
            return (
                PullRequest(repo=repo, number=number)
                if settings.pull_requests
                else None
            )
        elif resource_type == "issues":
            return Issue(repo=repo, number=number) if settings.issues else None
        elif resource_type == "discussions":
            return (
                Discussion(repo=repo, number=number)
                if settings.discussions
                else None
            )
        elif settings.require_strict_type:
            return None
        return Issue(repo=repo, number=number) if settings.issues else None

    if next_part in ("commits", "files"):
        if not settings.pull_request_review_comments:
            return None
        comment_id = _get_id_from_fragment(parsed_url, "r")
        sha: str | None = None
        commit_page = False
        files_page = False
        if not comment_id or not comment_id.isdigit():
            return None

        if next_part == "commits":
            # pull/<num>/commits/<sha>#r<ID>
            if not parts:
                return None
            sha = parts.popleft()
            for char in sha:
                if char not in string.hexdigits:
                    return None
            if parts:
                return None
            commit_page = True
        elif next_part == "files":
            if parts:
                return None
            files_page = True
        else:
            raise NotImplementedError("Unreachable code reached in parse_url")

        return PullRequestReviewComment(
            repo=repo,
            number=number,
            comment_id=int(comment_id),
            sha=sha,
            commit_page=commit_page,
            files_page=files_page,
        )

    # Checking settings is lazy as it would be bad to match a comment link to an issue when issue comments are disabled
    if (
        comment_id := _get_id_from_fragment(parsed_url, "issuecomment-")
    ) and comment_id.isdigit():
        if settings.require_strict_type:
            if resource_type == "issues" and settings.issue_comments:
                comment_type = IssueComment
            elif resource_type == "pull" and settings.pull_request_comments:
                comment_type = PullRequestComment
            else:
                return None
        else:
            comment_type = IssueComment
        return comment_type(repo=repo, number=number, comment_id=int(comment_id))
    if (
        event_id := _get_id_from_fragment(parsed_url, "event-")
    ) is not None and event_id.isdigit():
        if settings.require_strict_type:
            if resource_type == "issues" and settings.issue_events:
                event_type = IssueEvent
            elif resource_type == "pull" and settings.pull_request_events:
                event_type = PullRequestEvent
            else:
                return None
        else:
            event_type = IssueEvent
        return event_type(repo=repo, number=number, event_id=int(event_id))

    if (
        review_id := _get_id_from_fragment(parsed_url, "pullrequestreview-")
    ) and review_id.isdigit():
        if resource_type != "pull" and settings.require_strict_type:
            return None
        return (
            PullRequestReview(repo=repo, number=number, review_id=int(review_id))
            if settings.pull_request_reviews
            else None
        )
    if (
        review_comment_id := _get_id_from_fragment(parsed_url, "discussion_r")
    ) and review_comment_id.isdigit():
        if resource_type != "pull" and settings.require_strict_type:
            return None
        return (
            PullRequestReviewComment(
                repo=repo, number=number, comment_id=int(review_comment_id)
            )
            if settings.pull_request_review_comments
            else None
        )
    if (
        discussion_comment_id := _get_id_from_fragment(parsed_url, "discussioncomment-")
    ) and discussion_comment_id.isdigit():
        if resource_type != "discussions" and settings.require_strict_type:
            return None
        return (
            DiscussionComment(
                repo=repo, number=number, comment_id=int(discussion_comment_id)
            )
            if settings.discussion_comments
            else None
        )
    return None


# TODO: check yarl documentation regarding encoded or decoded values
def parse_url(
    url: str | yarl.URL,
    *,
    settings: MatcherSettings = _DEFAULT_MATCHER_SETTINGS,
) -> GitHubResource | None:
    """Parses a GitHub URL into its corresponding resource.

    This parses the following URL types:
    - User profile: https://github.com/{username}
    - Repository: https://github.com/{username}/{repo}
    - Issue: https://github.com/{username}/{repo}/issues/{issue_number}
    - Pull Request: https://github.com/{username}/{repo}/pull/{pr_number}
    - Issue Comment: https://github.com/{username}/{repo}/issues/{issue_number}#issuecomment-{comment_id}

    Please note that PullRequests are a type of Issue in GitHub's data model, and are represented as such in the API.
    This method still distinguishes them for clarity.

    .. note::
        Unlike :py:obj:`parse_shorthand`, this method returns a separate PullRequest type for pull requests.
        However, since pull requests are represented as issues in GitHub's data model and API, this distinction is primarily for clarity.
        In addition, unsanitized input URLs may lead to unexpected results. Do not assume a PullRequest actually refers to a pull request.

    Args:
        url: The URL to parse.
        settings: Settings for the URL matcher.
    Returns:
        A ParsedResource instance if the URL corresponds to a known GitHub resource,
        None otherwise.
    """
    if not isinstance(url, yarl.URL):
        parsed_url = yarl.URL(url)
    else:
        parsed_url = url
    if (
        not parsed_url.absolute
        or parsed_url.host_port_subcomponent not in settings.domains
    ):
        return None
    # parts consists of a slash at the front plus each path segments
    parts = collections.deque(parsed_url.parts)
    if not parts:
        return None
    _ = parts.popleft()  # remove leading slash
    user = parts.popleft()
    if not parts:
        return User(login=user)
    # parts is now [/, user, repo, ...]
    repo_name = parts.popleft()
    repo = Repo(name=repo_name, owner=user)
    if not parts:
        return repo
    # GitHub's api schema for (supported) types are the following:
    # Issue: /{owner}/{repo}/issues/{issue_number}
    # Pull Request: /{owner}/{repo}/pull/{pr_number}
    # Branch/Tag/Commit: /{owner}/{repo}/tree/{ref}
    # Discussion: /{owner}/{repo}/discussions/{discussion_number}
    # Tag: https://github.com/{owner}/{repo}/releases/tag/{tag}

    # in addition, issues, pull requests, and commits support comments
    # Issue Comment: /{owner}/{repo}/issues/{issue_number}#issuecomment-{comment_id}
    # Pull Request Comment: /{owner}/{repo}/pull/{pr_number}#issuecomment-{comment_id}
    # Discussion Comment: /{owner}/{repo}/discussions/{discussion_number}#discussioncomment-{comment_id}
    # Commit Comment: /{owner}/{repo}/commit/{commit_sha}#commitcomment-{comment_id}

    # issues and pull requests also support events
    # Issue Event: /{owner}/{repo}/issues/{issue_number}#event-{event_id}
    # Pull Request Event: /{owner}/{repo}/pull/{pr_number}#event-{event_id}

    # Pull Requests support reviews and review comments:
    # /{owner}/{repo}/pull/{pr_number}#pullrequestreview-3373902296
    # /{owner}/{repo}/pull/{pr_number}#discussion_r2269233870

    # TODO: add support for:
    # compare/diff between two refs
    # blame

    # Case normalisation is not performed on GitHub's end, so we do not do it here either.
    resource_type = parts.popleft()
    # Set supported resource types based on settings
    if resource_type not in settings._supported_resource_types():  # pyright: ignore[reportPrivateUsage]
        return None
    if resource_type == "releases":
        # only tag subresource is supported
        if not parts or parts.popleft() != "tag":
            return None
        if not parts:
            return None
        tag = parts.popleft()
        return ReleaseTag(repo=repo, tag=tag)

    if resource_type in ("issues", "pull", "discussions"):
        return _parse_numberable_url(
            parsed_url=parsed_url,
            parts=parts,
            repo=repo,
            settings=settings,
            resource_type=resource_type,
        )

    if resource_type == "commit":
        sha = parts.popleft()
        comment_id = _get_id_from_fragment(parsed_url, "commitcomment-")
        if comment_id is not None and comment_id.isdigit():
            return (
                CommitComment(repo=repo, sha=sha, comment_id=int(comment_id))
                if settings.commit_comments
                else None
            )
        return Commit(repo=repo, sha=sha) if settings.commits else None


def parse_shorthand(
    shorthand: str,
    *,
    default_user: str | None = None,
    settings: MatcherSettings = _DEFAULT_MATCHER_SETTINGS,
) -> GitHubResource | None:
    """
    Parses a shorthand notation for a GitHub resource.

    Examples of supported shorthand:
    - user/repo
    - user/repo#issue_number
    - user/repo@ref (can be sha, branch, or tag)

    If the user is omitted, `default_user` is used if
    provided to enable the following shorthand:
    - repo#issue_number
    - repo@ref (can be sha, branch, or tag)

    No requests are made to GitHub; this is purely syntactic parsing.
    No validation is performed on the parsed values, they are simply returned as-is.
    """
    if not settings.shorthand:
        return None
    # Iterate once.
    user: str = ""
    repo: str = ""
    ref_type: str = ""

    if "/" in shorthand:
        user, shorthand = shorthand.split("/", 1)
    elif default_user is None:
        return None
    else:
        user = default_user

    # validate the user
    for char in user:
        if char not in string.ascii_letters + string.digits + "-._":
            return None

    for char in shorthand:
        if char in ("#", "@"):
            ref_type = char
            break
        if char not in string.ascii_letters + string.digits + "-._":
            return None
        repo += char
    else:
        return Repo(name=repo, owner=user) if settings.short_repo else None

    ref = shorthand[len(repo) + 1 :]
    if ref_type == "#":
        if not ref.isdigit():
            return None
        return (
            NumberedResource(repo=Repo(name=repo, owner=user), number=int(ref))
            if settings.short_numberables
            else None
        )
    elif ref_type == "@":
        return (
            ReleaseTag(repo=Repo(name=repo, owner=user), tag=ref)
            if settings.short_refs
            else None
        )
    return None
