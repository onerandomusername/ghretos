import yarl


import dataclasses
import collections
import collections.abc


@dataclasses.dataclass
class ParsedResource:
    pass


@dataclasses.dataclass
class User(ParsedResource):
    login: str


@dataclasses.dataclass
class Repo(ParsedResource):
    name: str
    owner: User

## ISSUES
@dataclasses.dataclass
class Issue(ParsedResource):
    repo: Repo
    number: str


@dataclasses.dataclass
class IssueComment(ParsedResource):
    issue: Issue
    comment_id: str

## PULL REQUESTS

@dataclasses.dataclass
class PullRequest(ParsedResource):
    repo: Repo
    number: str


@dataclasses.dataclass
class PullRequestComment(ParsedResource):
    pull_request: PullRequest
    comment_id: str


@dataclasses.dataclass
class Discussion(ParsedResource):
    repo: Repo
    number: str


@dataclasses.dataclass
class ReleaseTag(ParsedResource):
    repo: Repo
    tag: str


@dataclasses.dataclass
class MatcherSettings:
    domains: list[str] = dataclasses.field(default_factory=lambda: ["github.com"])


_DEFAULT_MATCHER_SETTINGS = MatcherSettings()


def _get_comment_id_from_fragment(url: yarl.URL, prefix: str) -> str | None:
    fragment = url.fragment
    if fragment.startswith(prefix):
        return fragment[len(prefix) :]
    return None


# TODO: check yarl documentation regarding encoded or decoded values
def parse_url(
    url: str,
    *,
    settings: MatcherSettings = _DEFAULT_MATCHER_SETTINGS,
) -> ParsedResource | None:
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
    parsed_url = yarl.URL(url)
    if (
        not parsed_url.absolute
        or parsed_url.host_port_subcomponent not in settings.domains
    ):
        return None
    # parts consists of a slash at the front plus each path segments
    parts = collections.deque(parsed_url.parts)
    if parts:
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
        # we don't currently have a type for tags
        return None


def parse_shorthand(
    shorthand: str,
    *,
    default_user: str | None = None,
) -> ParsedResource | None:
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
