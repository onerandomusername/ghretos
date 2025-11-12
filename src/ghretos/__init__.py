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


def _parse_strict_url(
    parsed_url: yarl.URL,
    *,
    settings: MatcherSettings,
):
    path_and_fragment = list(parsed_url.parts)
    if parsed_url.fragment:
        path_and_fragment.append(f"#{parsed_url.fragment}")
    path_and_fragment.pop(0)
    match path_and_fragment:
        # User
        case [owner]:
            return User(login=owner)
        # Repository
        case [owner, repo]:
            return Repo(name=repo, owner=owner)
        case [owner, repo, "issues", resource_id] if settings.issues:
            if not resource_id.isdigit():
                return None
            return Issue(repo=Repo(name=repo, owner=owner), number=int(resource_id))
        case [
            owner,
            repo,
            "issue" | "pull" as resource_type,
            resource_id,
            fragment,
        ] if settings.issues and fragment.startswith("#issue-"):
            if not resource_id.isdigit():
                return None
            if resource_type == "issue":
                return Issue(repo=Repo(name=repo, owner=owner), number=int(resource_id))
            else:
                return PullRequest(
                    repo=Repo(name=repo, owner=owner), number=int(resource_id)
                )
        case [owner, repo, "pull", resource_id] if settings.pull_requests:
            if not resource_id.isdigit():
                return None
            return PullRequest(
                repo=Repo(name=repo, owner=owner), number=int(resource_id)
            )
        case [owner, repo, "discussions", resource_id] if settings.discussions:
            if not resource_id.isdigit():
                return None
            return Discussion(
                repo=Repo(name=repo, owner=owner), number=int(resource_id)
            )
        case [owner, repo, "discussions", resource_id, fragment] if (
            settings.discussions and fragment.startswith("#discussion-")
        ):
            if not resource_id.isdigit():
                return None
            return Discussion(
                repo=Repo(name=repo, owner=owner), number=int(resource_id)
            )
        # Pull request review comments on specific commit (with SHA) - must come before the pattern without SHA
        case [owner, repo, "pull", resource_id, "commits", sha, fragment] if (
            settings.pull_request_review_comments
            and (fragment := _get_id_from_fragment(parsed_url, "r"))
        ):
            if not resource_id.isdigit():
                return None
            # Validate SHA is hexadecimal
            try:
                int(sha, 16)
            except ValueError:
                return None
            return PullRequestReviewComment(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(fragment),
                sha=sha,
                commit_page=True,
            )
        # Pull request review comments on /files page (no SHA allowed here)
        case [
            owner,
            repo,
            "pull",
            resource_id,
            "files",
            fragment,
        ] if settings.pull_request_review_comments and (
            fragment := _get_id_from_fragment(parsed_url, "r")
        ):
            if not resource_id.isdigit():
                return None
            return PullRequestReviewComment(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(fragment),
                commit_page=False,
                files_page=True,
            )
        # Issue with #issue- fragment
        case [owner, repo, "issues", resource_id, fragment] if (
            settings.issues and fragment.startswith("#issue-")
        ):
            if not resource_id.isdigit():
                return None
            return Issue(repo=Repo(name=repo, owner=owner), number=int(resource_id))
        # Issue comments
        case [owner, repo, "issues", resource_id, fragment] if (
            settings.issue_comments
            and fragment.startswith("#issuecomment-")
        ):
            if not resource_id.isdigit():
                return None
            comment_id = fragment[len("#issuecomment-"):]
            if not comment_id.isdigit():
                return None
            return IssueComment(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(comment_id),
            )
        # Pull request comments
        case [owner, repo, "pull", resource_id, fragment] if (
            settings.pull_request_comments
            and fragment.startswith("#issuecomment-")
        ):
            if not resource_id.isdigit():
                return None
            comment_id = fragment[len("#issuecomment-"):]
            if not comment_id.isdigit():
                return None
            return PullRequestComment(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(comment_id),
            )
        # Issue events
        case [owner, repo, "issues", resource_id, fragment] if (
            settings.issue_events
            and fragment.startswith("#event-")
        ):
            if not resource_id.isdigit():
                return None
            event_id = fragment[len("#event-"):]
            if not event_id.isdigit():
                return None
            return IssueEvent(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                event_id=int(event_id),
            )
        # Pull request events
        case [owner, repo, "pull", resource_id, fragment] if (
            settings.pull_request_events
            and fragment.startswith("#event-")
        ):
            if not resource_id.isdigit():
                return None
            event_id = fragment[len("#event-"):]
            if not event_id.isdigit():
                return None
            return PullRequestEvent(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                event_id=int(event_id),
            )
        # Pull request reviews
        case [owner, repo, "pull", resource_id, fragment] if (
            settings.pull_request_reviews
            and fragment.startswith("#pullrequestreview-")
        ):
            if not resource_id.isdigit():
                return None
            review_id = fragment[len("#pullrequestreview-"):]
            if not review_id.isdigit():
                return None
            return PullRequestReview(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                review_id=int(review_id),
            )
        # Pull request review comments (discussion_r)
        case [owner, repo, "pull", resource_id, fragment] if (
            settings.pull_request_review_comments
            and fragment.startswith("#discussion_r")
        ):
            if not resource_id.isdigit():
                return None
            comment_id = fragment[len("#discussion_r"):]
            if not comment_id.isdigit():
                return None
            return PullRequestReviewComment(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(comment_id),
            )
        # Discussion comments
        case [owner, repo, "discussions", resource_id, fragment] if (
            settings.discussion_comments
            and fragment.startswith("#discussioncomment-")
        ):
            if not resource_id.isdigit():
                return None
            comment_id = fragment[len("#discussioncomment-"):]
            if not comment_id.isdigit():
                return None
            return DiscussionComment(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(comment_id),
            )
        case _:
            return None


def _parse_unstrict_url(parsed_url: yarl.URL, *, settings: MatcherSettings):
    ...

    path_and_fragment = list(parsed_url.parts)
    if parsed_url.fragment:
        path_and_fragment.append(f"#{parsed_url.fragment}")
    path_and_fragment.pop(0)
    match path_and_fragment:
        # User
        case [owner]:
            return User(login=owner)
        # Repository
        case [owner, repo]:
            return Repo(name=repo, owner=owner)
        case [
            owner,
            repo,
            "issues" | "pull" | "discussions" as resource_type,
            resource_id,
        ]:
            if not resource_id.isdigit():
                return None
            if resource_type == "issues":
                if settings.issues:
                    return Issue(
                        repo=Repo(name=repo, owner=owner), number=int(resource_id)
                    )
            elif resource_type == "pull":
                if settings.pull_requests:
                    return PullRequest(
                        repo=Repo(name=repo, owner=owner), number=int(resource_id)
                    )
            elif resource_type == "discussions":
                if settings.discussions:
                    return Discussion(
                        repo=Repo(name=repo, owner=owner), number=int(resource_id)
                    )
            return None
        case [
            owner,
            repo,
            "issue" | "pull" | "discussions" as resource_type,
            resource_id,
            fragment,
        ] if settings.issues and fragment.startswith(("#issue-", "#discussion-")):
            if not resource_id.isdigit():
                return None
            if fragment.startswith("#issue-"):
                if resource_type == "pull":
                    return PullRequest(
                        repo=Repo(name=repo, owner=owner), number=int(resource_id)
                    )
                return Issue(repo=Repo(name=repo, owner=owner), number=int(resource_id))
            elif fragment.startswith("#discussion-"):
                return Discussion(
                    repo=Repo(name=repo, owner=owner), number=int(resource_id)
                )
            return None
        case [
            owner,
            repo,
            "issues" | "pull" | "discussions" as resource_type,
            resource_id,
            fragment,
        ] if settings.pull_request_review_comments and (
            fragment.startswith(("pullrequestreview-", "discussion_r"))
        ):
            if not resource_id.isdigit():
                return None
            return PullRequestReviewComment(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(fragment),
            )
        # Pull request review comments on commits page with SHA (allow /issues/ URLs)
        case [owner, repo, "issues" | "pull", resource_id, "commits", sha, fragment] if (
            settings.pull_request_review_comments
            and (fragment := _get_id_from_fragment(parsed_url, "r"))
        ):
            if not resource_id.isdigit():
                return None
            # Validate SHA is hexadecimal
            try:
                int(sha, 16)
            except ValueError:
                return None
            return PullRequestReviewComment(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(fragment),
                sha=sha,
                commit_page=True,
            )
        # Pull request review comments on files page (allow /issues/ URLs)
        case [owner, repo, "issues" | "pull", resource_id, "files", fragment] if (
            settings.pull_request_review_comments
            and (fragment := _get_id_from_fragment(parsed_url, "r"))
        ):
            if not resource_id.isdigit():
                return None
            return PullRequestReviewComment(
                repo=Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(fragment),
                commit_page=False,
                files_page=True,
            )
        case _:
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

    if not isinstance(url, yarl.URL):
        parsed_url = yarl.URL(url)
    else:
        parsed_url = url
    if (
        not parsed_url.absolute
        or parsed_url.host_port_subcomponent not in settings.domains
    ):
        return None
    path_and_fragment = list(parsed_url.parts)
    if parsed_url.fragment:
        path_and_fragment.append(f"#{parsed_url.fragment}")
    path_and_fragment.pop(0)

    if settings.require_strict_type:
        result = _parse_strict_url(parsed_url, settings=settings)
    else:
        result = _parse_unstrict_url(parsed_url, settings=settings)
    if result is not None:
        return result
    # Case normalisation is not performed on GitHub's end, so we do not do it here either.
    match path_and_fragment:
        case [] | [""]:
            return None
        case [owner]:
            return User(login=owner)
        case [owner, repo]:
            return Repo(name=repo, owner=owner)
        case [owner, repo, "commit", sha] if settings.commits:
            return Commit(repo=Repo(name=repo, owner=owner), sha=sha)
        case [owner, repo, "commit", sha, fragment] if (
            settings.commit_comments and fragment.startswith("#commitcomment-")
        ):
            comment_id = fragment[len("#commitcomment-") :]
            if not comment_id.isdigit():
                return None
            return CommitComment(
                repo=Repo(name=repo, owner=owner),
                sha=sha,
                comment_id=int(comment_id),
            )
        case [owner, repo, "releases", "tag", tag] if settings.releases:
            return ReleaseTag(repo=Repo(name=repo, owner=owner), tag=tag)
        case [owner, repo, "commit", sha] if settings.commits:
            return Commit(repo=Repo(name=repo, owner=owner), sha=sha)
        case [owner, repo, "commit", sha, fragment] if (
            settings.commit_comments and fragment.startswith("#commitcomment-")
        ):
            comment_id = fragment[len("#commitcomment-") :]
            if not comment_id.isdigit():
                return None
            return CommitComment(
                repo=Repo(name=repo, owner=owner),
                sha=sha,
                comment_id=int(comment_id),
            )
        case [owner, repo, "releases", "tag", tag] if settings.releases:
            return ReleaseTag(repo=Repo(name=repo, owner=owner), tag=tag)


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
