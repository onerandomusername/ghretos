import collections
import dataclasses

import yarl

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


class GitHubResource:
    pass


@dataclasses.dataclass(unsafe_hash=True)
class User(GitHubResource):
    login: str


@dataclasses.dataclass(unsafe_hash=True)
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


## ISSUES
@dataclasses.dataclass(unsafe_hash=True)
class _Issue(GitHubResource):
    repo: Repo
    number: int


@dataclasses.dataclass(unsafe_hash=True)
class Issue(_Issue):
    pass


@dataclasses.dataclass(unsafe_hash=True)
class IssueComment(_Issue):
    comment_id: int


@dataclasses.dataclass(unsafe_hash=True)
class IssueEvent(_Issue):
    event_id: int


## PULL REQUESTS


@dataclasses.dataclass(unsafe_hash=True)
class _PullRequest(GitHubResource):
    repo: Repo
    number: int


@dataclasses.dataclass(unsafe_hash=True)
class PullRequest(_PullRequest):
    pass


@dataclasses.dataclass(unsafe_hash=True)
class PullRequestComment(_PullRequest):
    comment_id: int


@dataclasses.dataclass(unsafe_hash=True)
class PullRequestReview(_PullRequest):
    review_id: int


@dataclasses.dataclass(unsafe_hash=True)
class PullRequestReviewComment(_PullRequest):
    comment_id: int


@dataclasses.dataclass(unsafe_hash=True)
class PullRequestEvent(_PullRequest):
    event_id: int


### DISCUSSIONS


@dataclasses.dataclass(unsafe_hash=True)
class _Discussion(GitHubResource):
    repo: Repo
    number: int


@dataclasses.dataclass(unsafe_hash=True)
class Discussion(_Discussion):
    repo: Repo
    number: int


@dataclasses.dataclass(unsafe_hash=True)
class DiscussionComment(_Discussion):
    comment_id: int


## COMMITS


@dataclasses.dataclass(unsafe_hash=True)
class _Commit(GitHubResource):
    repo: Repo
    sha: str


@dataclasses.dataclass(unsafe_hash=True)
class Commit(_Commit):
    pass


@dataclasses.dataclass(unsafe_hash=True)
class CommitComment(_Commit):
    comment_id: int


@dataclasses.dataclass(unsafe_hash=True)
class ReleaseTag(GitHubResource):
    repo: Repo
    tag: str


@dataclasses.dataclass
class MatcherSettings:
    domains: list[str] = dataclasses.field(default_factory=lambda: ["github.com"])


_DEFAULT_MATCHER_SETTINGS = MatcherSettings()


def _get_id_from_fragment(url: yarl.URL, prefix: str) -> str | None:
    fragment = url.fragment
    if fragment.startswith(prefix):
        return fragment[len(prefix) :]
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
    if resource_type not in (
        "issues",
        "pull",
        "discussions",
        "commit",
        "releases",
    ):
        return None
    if resource_type == "releases":
        # only tag subresource is supported
        if not parts or parts.popleft() != "tag":
            return None
        if not parts:
            return None
        tag = parts.popleft()
        return ReleaseTag(repo=repo, tag=tag)

    match resource_type:
        case "issues":
            issue_number = parts.popleft()
            if not issue_number.isdigit():
                return None
            issue_number = int(issue_number)
            if (
                comment_id := _get_id_from_fragment(parsed_url, "issuecomment-")
            ) and comment_id.isdigit():
                return IssueComment(
                    repo=repo, number=issue_number, comment_id=int(comment_id)
                )
            event_id = _get_id_from_fragment(parsed_url, "event-")
            if event_id is not None and event_id.isdigit():
                return IssueEvent(
                    repo=repo, number=issue_number, event_id=int(event_id)
                )
            return Issue(repo=repo, number=issue_number)
        case "pull":
            pull_number = parts.popleft()
            if not pull_number.isdigit():
                return None
            pull_number = int(pull_number)
            if (
                comment_id := _get_id_from_fragment(parsed_url, "issuecomment-")
            ) and comment_id.isdigit():
                return PullRequestComment(
                    repo=repo, number=pull_number, comment_id=int(comment_id)
                )
            if (
                review_id := _get_id_from_fragment(parsed_url, "pullrequestreview-")
            ) and review_id.isdigit():
                return PullRequestReview(
                    repo=repo, number=pull_number, review_id=int(review_id)
                )
            if (
                review_comment_id := _get_id_from_fragment(parsed_url, "discussion_r")
            ) and review_comment_id.isdigit():
                return PullRequestReviewComment(
                    repo=repo, number=pull_number, comment_id=int(review_comment_id)
                )

            event_id = _get_id_from_fragment(parsed_url, "event-")
            if event_id is not None and event_id.isdigit():
                return PullRequestEvent(
                    repo=repo, number=pull_number, event_id=int(event_id)
                )
            return PullRequest(repo=repo, number=pull_number)
        case "discussions":
            discussion_number = parts.popleft()
            if not discussion_number.isdigit():
                return None
            discussion_number = int(discussion_number)
            comment_id = _get_id_from_fragment(parsed_url, "discussioncomment-")
            if comment_id is not None and comment_id.isdigit():
                return DiscussionComment(
                    repo=repo, number=discussion_number, comment_id=int(comment_id)
                )
            return Discussion(repo=repo, number=discussion_number)
        case "commit":
            sha = parts.popleft()
            comment_id = _get_id_from_fragment(parsed_url, "commitcomment-")
            if comment_id is not None and comment_id.isdigit():
                return CommitComment(repo=repo, sha=sha, comment_id=int(comment_id))
            return Commit(repo=repo, sha=sha)


def parse_shorthand(
    shorthand: str,
    *,
    default_user: str | None = None,
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
        return Repo(name=repo, owner=user)

    ref = shorthand[len(repo) + 1 :]
    if ref_type == "#":
        if not ref.isdigit():
            return None
        return Issue(repo=Repo(name=repo, owner=user), number=int(ref))
    elif ref_type == "@":
        return ReleaseTag(repo=Repo(name=repo, owner=user), tag=ref)
    return None
