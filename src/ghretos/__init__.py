from calendar import c
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

@dataclasses.dataclass
class GitHubResource:
    pass


@dataclasses.dataclass
class User(GitHubResource):
    login: str


@dataclasses.dataclass
class Repo(GitHubResource):
    name: str
    owner: User


## ISSUES
@dataclasses.dataclass
class Issue(GitHubResource):
    repo: Repo
    number: str


@dataclasses.dataclass
class IssueComment(GitHubResource):
    issue: Issue
    comment_id: str


@dataclasses.dataclass
class IssueEvent(GitHubResource):
    issue: Issue
    event_id: str


## PULL REQUESTS


@dataclasses.dataclass
class PullRequest(GitHubResource):
    repo: Repo
    number: str


@dataclasses.dataclass
class PullRequestComment(GitHubResource):
    pull_request: PullRequest
    comment_id: str


@dataclasses.dataclass
class PullRequestReview(GitHubResource):
    pull_request: PullRequest
    comment_id: str


@dataclasses.dataclass
class PullRequestReviewComment(GitHubResource):
    pull_request: PullRequest
    comment_id: str


@dataclasses.dataclass
class PullRequestEvent(GitHubResource):
    pull_request: PullRequest
    event_id: str


### DISCUSSIONS


@dataclasses.dataclass
class Discussion(GitHubResource):
    repo: Repo
    number: str


@dataclasses.dataclass
class DiscussionComment(GitHubResource):
    discussion: Discussion
    comment_id: str


## COMMITS


@dataclasses.dataclass
class Commit(GitHubResource):
    repo: Repo
    sha: str


@dataclasses.dataclass
class CommitComment(GitHubResource):
    commit: Commit
    comment_id: str


@dataclasses.dataclass
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
    owner = User(login=user)
    if not parts:
        return owner
    # parts is now [/, user, repo, ...]
    repo_name = parts.popleft()
    repo = Repo(name=repo_name, owner=owner)
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
            issue = Issue(repo=repo, number=issue_number)
            comment_id = _get_id_from_fragment(parsed_url, "issuecomment-")
            if comment_id is not None:
                return IssueComment(issue=issue, comment_id=comment_id)
            event_id = _get_id_from_fragment(parsed_url, "event-")
            if event_id is not None:
                return IssueEvent(issue=issue, event_id=event_id)
            return issue
        case "pull":
            pull_number = parts.popleft()
            pull = PullRequest(repo=repo, number=pull_number)
            comment_id = _get_id_from_fragment(parsed_url, "issuecomment-")
            if comment_id is not None:
                return PullRequestComment(pull_request=pull, comment_id=comment_id)
            if (
                review_id := _get_id_from_fragment(parsed_url, "pullrequestreview-")
            ) is not None:
                return PullRequestReview(pull_request=pull, comment_id=review_id)
            if review_comment_id := _get_id_from_fragment(parsed_url, "discussion_r"):
                return PullRequestReviewComment(
                    pull_request=pull, comment_id=review_comment_id
                )

            event_id = _get_id_from_fragment(parsed_url, "event-")
            if event_id is not None:
                return PullRequestEvent(pull_request=pull, event_id=event_id)
            return pull
        case "discussions":
            discussion_number = parts.popleft()
            discussion = Discussion(repo=repo, number=discussion_number)
            comment_id = _get_id_from_fragment(parsed_url, "discussioncomment-")
            if comment_id is not None:
                return DiscussionComment(discussion=discussion, comment_id=comment_id)
            return discussion
        case "commit":
            sha = parts.popleft()
            commit = Commit(repo=repo, sha=sha)
            comment_id = _get_id_from_fragment(parsed_url, "commitcomment-")
            if comment_id is not None:
                return CommitComment(commit=commit, comment_id=comment_id)
            return commit


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
