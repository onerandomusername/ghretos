"""This is the parsing aspect of GitHub.com URLs and shorthands.

GitHub's api schema for (supported) types are the following:

- Issue: ``/{owner}/{repo}/issues/{issue_number}``
- Pull Request: ``/{owner}/{repo}/pull/{pr_number}``
- Branch/Tag/Commit: ``/{owner}/{repo}/tree/{ref}``
- Discussion: ``/{owner}/{repo}/discussions/{discussion_number}``
- Tag: ``/{owner}/{repo}/releases/tag/{tag}``

In addition, issues, pull requests, and commits support comments:

- Issue Comment: ``/{owner}/{repo}/issues/{issue_number}#issuecomment-{comment_id}``
- Pull Request Comment: ``/{owner}/{repo}/pull/{pr_number}#issuecomment-{comment_id}``
- Discussion Comment: ``/{owner}/{repo}/discussions/{discussion_number}#discussioncomment-{comment_id}``
- Commit Comment: ``/{owner}/{repo}/commit/{commit_sha}#commitcomment-{comment_id}``

Issues and pull requests also support events:

- Issue Event: ``/{owner}/{repo}/issues/{issue_number}#event-{event_id}``
- Pull Request Event: ``/{owner}/{repo}/pull/{pr_number}#event-{event_id}``

Pull Requests support reviews and review comments:

- Review: ``/{owner}/{repo}/pull/{pr_number}#pullrequestreview-3373902296``
- Review comments: ``/{owner}/{repo}/pull/{pr_number}#discussion_r2269233870``
"""  # noqa: E501

import string

import yarl

from ghretos import models


__all__ = (
    "parse_shorthand",
    "parse_url",
)


_DEFAULT_MATCHER_SETTINGS = models.MatcherSettings()


def _valid_user(user: str) -> bool:
    """Validates a GitHub username according to GitHub's rules."""
    if not (1 <= len(user) <= 39):
        return False
    allowed_chars = string.ascii_letters + string.digits + "-"

    if user[0] == "-" or user[-1] == "-":
        return False

    for char in user:  # noqa: SIM110
        if char not in allowed_chars:
            return False

    return True


def _valid_repository(repository: str) -> bool:
    """Validates a GitHub Repository name according to GitHub's rules."""
    if not (1 <= len(repository) <= 100):
        return False
    allowed_chars = string.ascii_letters + string.digits + "-._"

    for char in repository:  # noqa: SIM110
        if char not in allowed_chars:
            return False

    return True


def _validate_ref(ref: str) -> bool:
    """Validates a Git reference name according to Git's rules.

    https://git-scm.com/docs/git-check-ref-format
    """
    if not ref:
        return False

    if ref == "@":
        return False
    last_char = ref[0]
    if last_char in (".", "/"):
        return False
    if any(
        phrase in ref
        for phrase in ("..", "~", "^", ":", "?", "*", "[", "\\", "@{", "//", "/.", ".lock/")
    ):
        return False
    for char in ref:
        if char in string.whitespace:
            return False
        if last_char in (".") and char == "/":
            return False
        last_char = char

    if any(c.endswith((".lock", ".")) or c.startswith(".") for c in ref.split("/")):  # noqa: SIM103
        return False

    return True


def _get_id_from_fragment(url: yarl.URL, prefix: str) -> str | None:
    fragment = url.fragment
    if fragment.startswith(prefix):
        return fragment[len(prefix) :]
    return None


def _parse_strict_numberable_url(
    parsed_url: yarl.URL,
    *,
    settings: models.MatcherSettings,
) -> models.GitHubResource | None:
    path_and_fragment = list(parsed_url.parts)
    if parsed_url.fragment:
        path_and_fragment.append(f"#{parsed_url.fragment}")
    _ = path_and_fragment.pop(0)
    match path_and_fragment:
        case [
            owner,
            repository,
            "issues" | "pull" | "discussions" as resource_type,
            resource_id,
            *rest,
        ]:
            pass
        case _:
            return None
    if not _valid_user(owner) or not _valid_repository(repository):
        return None
    try:
        resource_id = int(resource_id)
    except ValueError:
        return None
    repo = models.Repo(name=repository, owner=owner)
    # inject the resource_type for strict matching
    rest.insert(0, resource_type)
    match rest:
        case ["issues"] if settings.issues:
            return models.Issue(repo=repo, number=resource_id)
        case ["issues", fragment] if settings.issues and fragment.startswith("#issue-"):
            return models.Issue(repo=repo, number=resource_id)
        case ["pull"] if settings.pull_requests:
            return models.PullRequest(repo=repo, number=resource_id)
        case ["pull", fragment] if settings.pull_requests and fragment.startswith("#issue-"):
            return models.PullRequest(repo=repo, number=resource_id)
        case ["discussions"] if settings.discussions:
            return models.Discussion(repo=repo, number=resource_id)
        case ["discussions", fragment] if settings.discussions and fragment.startswith(
            "#discussion-"
        ):
            return models.Discussion(repo=repo, number=resource_id)
        case ["pull", "commits", sha, fragment] if settings.pull_request_review_comments and (
            fragment := _get_id_from_fragment(parsed_url, "r")
        ):
            # Validate SHA is hexadecimal
            try:
                int(sha, 16)
            except ValueError:
                return None
            try:
                comment_id = int(fragment)
            except ValueError:
                return None
            return models.PullRequestReviewComment(
                repo=repo, number=resource_id, comment_id=comment_id, sha=sha, commit_page=True
            )
        # Pull request review comments on /files page (no SHA allowed here)
        case [
            "pull",
            "files",
            fragment,
        ] if settings.pull_request_review_comments and (
            fragment := _get_id_from_fragment(parsed_url, "r")
        ):
            try:
                comment_id = int(fragment)
            except ValueError:
                return None
            return models.PullRequestReviewComment(
                repo=repo,
                number=resource_id,
                comment_id=comment_id,
                commit_page=False,
                files_page=True,
            )
        # Issue with #issue- fragment
        case ["issues", fragment] if settings.issues and fragment.startswith("#issue-"):
            return models.Issue(repo=repo, number=resource_id)
        # Issue comments
        case ["issues", fragment] if settings.issue_comments and fragment.startswith(
            "#issuecomment-"
        ):
            comment_id = fragment[len("#issuecomment-") :]
            try:
                comment_id = int(comment_id)
            except ValueError:
                return None
            return models.IssueComment(repo=repo, number=resource_id, comment_id=comment_id)
        # Pull request comments
        case ["pull", fragment] if settings.pull_request_comments and fragment.startswith(
            "#issuecomment-"
        ):
            comment_id = fragment[len("#issuecomment-") :]
            try:
                comment_id = int(comment_id)
            except ValueError:
                return None
            return models.PullRequestComment(repo=repo, number=resource_id, comment_id=comment_id)
        # Issue events
        case ["issues", fragment] if settings.issue_events and fragment.startswith("#event-"):
            event_id = fragment[len("#event-") :]
            try:
                event_id = int(event_id)
            except ValueError:
                return None
            return models.IssueEvent(repo=repo, number=resource_id, event_id=event_id)
        # Pull request events
        case ["pull", fragment] if settings.pull_request_events and fragment.startswith("#event-"):
            event_id = fragment[len("#event-") :]
            try:
                event_id = int(event_id)
            except ValueError:
                return None
            return models.PullRequestEvent(
                repo=repo,
                number=resource_id,
                event_id=event_id,
            )
        # Pull request reviews
        case ["pull", fragment] if settings.pull_request_reviews and fragment.startswith(
            "#pullrequestreview-"
        ):
            review_id = fragment[len("#pullrequestreview-") :]
            try:
                review_id = int(review_id)
            except ValueError:
                return None
            return models.PullRequestReview(repo=repo, number=resource_id, review_id=review_id)
        # Pull request review comments (discussion_r)
        case ["pull", fragment] if settings.pull_request_review_comments and fragment.startswith(
            "#discussion_r"
        ):
            comment_id = fragment[len("#discussion_r") :]
            try:
                comment_id = int(comment_id)
            except ValueError:
                return None
            return models.PullRequestReviewComment(
                repo=repo, number=resource_id, comment_id=comment_id
            )
        # Discussion comments
        case ["discussions", fragment] if settings.discussion_comments and fragment.startswith(
            "#discussioncomment-"
        ):
            comment_id = fragment[len("#discussioncomment-") :]
            try:
                comment_id = int(comment_id)
            except ValueError:
                return None
            return models.DiscussionComment(repo=repo, number=resource_id, comment_id=comment_id)
        case _:
            return None


def _parse_loose_numberable_url(
    parsed_url: yarl.URL, *, settings: models.MatcherSettings
) -> models.GitHubResource | None:
    path_and_fragment = list(parsed_url.parts)
    if parsed_url.fragment:
        path_and_fragment.append(f"#{parsed_url.fragment}")
    _ = path_and_fragment.pop(0)
    # assert the style of URL matches what we expect
    match path_and_fragment:
        case [
            owner,
            repository_name,
            "issues" | "pull" | "discussions" as resource_type,
            resource_id,
            *rest,
        ]:
            pass
        case _:
            return None
    if not _valid_user(owner) or not _valid_repository(repository_name):
        return None
    try:
        resource_id = int(resource_id)
    except ValueError:
        return None
    repo = models.Repo(name=repository_name, owner=owner)
    # inject the resource_type for loose matching
    match rest:
        case []:
            if resource_type == "issues":
                if settings.issues:
                    return models.Issue(repo=repo, number=resource_id)
            elif resource_type == "pull":
                if settings.pull_requests:
                    return models.PullRequest(repo=repo, number=resource_id)
            elif resource_type == "discussions" and settings.discussions:
                return models.Discussion(repo=repo, number=resource_id)
            return None
        case [fragment] if fragment.startswith("#issuecomment-"):
            comment_id = fragment[len("#issuecomment-") :]
            try:
                comment_id = int(comment_id)
            except ValueError:
                return None
            if resource_type == "pull":
                return (
                    models.PullRequestComment(repo=repo, number=resource_id, comment_id=comment_id)
                    if settings.pull_request_comments
                    else None
                )
            return (
                models.IssueComment(repo=repo, number=resource_id, comment_id=comment_id)
                if settings.issue_comments
                else None
            )
        case [fragment] if settings.discussion_comments and fragment.startswith(
            "#discussioncomment-"
        ):
            comment_id = fragment[len("#discussioncomment-") :]
            try:
                comment_id = int(comment_id)
            except ValueError:
                return None
            return models.DiscussionComment(repo=repo, number=resource_id, comment_id=comment_id)
        case [fragment] if fragment.startswith(("#issue-", "#discussion-")):
            if fragment.startswith("#issue-"):
                if resource_type == "pull":
                    return (
                        models.PullRequest(repo=repo, number=resource_id)
                        if settings.pull_requests
                        else None
                    )
                return models.Issue(repo=repo, number=resource_id) if settings.issues else None
            elif fragment.startswith("#discussion-"):
                return (
                    models.Discussion(repo=repo, number=resource_id)
                    if settings.discussions
                    else None
                )
            return None
        case [fragment] if settings.pull_request_review_comments and (
            fragment.startswith(("#pullrequestreview-", "#discussion_r"))
        ):
            if fragment.startswith("#pullrequestreview-"):
                review_id = fragment.removeprefix("#pullrequestreview-")
                try:
                    review_id = int(review_id)
                except ValueError:
                    return None
                return models.PullRequestReview(repo=repo, number=resource_id, review_id=review_id)
            elif fragment.startswith("#discussion_r"):
                comment_id = fragment.removeprefix("#discussion_r")
                try:
                    comment_id = int(comment_id)
                except ValueError:
                    return None
                return models.PullRequestReviewComment(
                    repo=repo, number=resource_id, comment_id=comment_id
                )
            return None
        case ["commits", sha, fragment] if (
            settings.pull_request_review_comments
            and resource_type == "pull"
            and (fragment := _get_id_from_fragment(parsed_url, "r"))
        ):
            # Validate SHA is hexadecimal
            try:
                int(sha, 16)
            except ValueError:
                return None
            return models.PullRequestReviewComment(
                repo=repo,
                number=resource_id,
                comment_id=int(fragment),
                sha=sha,
                commit_page=True,
            )
        # Pull request review comments on files page
        case ["files", fragment] if (
            settings.pull_request_review_comments
            and resource_type == "pull"
            and (fragment := _get_id_from_fragment(parsed_url, "r"))
        ):
            return models.PullRequestReviewComment(
                repo=repo,
                number=resource_id,
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
    settings: models.MatcherSettings = _DEFAULT_MATCHER_SETTINGS,
) -> models.GitHubResource | None:
    """Parses a GitHub URL into its corresponding resource.

    Please note that PullRequests are a type of Issue in GitHub's data model, and are represented as
    such in the API. This method still distinguishes them for clarity.

    .. note::
        Unlike :py:obj:`.parse_shorthand`, this method returns a separate PullRequest type for pull
        requests. However, since pull requests are represented as issues in GitHub's data model and
        API, this distinction is primarily for clarity. In addition, unsanitized input URLs may lead
        to unexpected results. Do not assume a PullRequest actually refers to a pull request.

    Args:
        url: The URL to parse.
        settings: :obj:`.MatcherSettings` for the URL matcher.
    Returns:
        A ParsedResource instance if the URL corresponds to a known GitHub resource,
        None otherwise.
    """
    if not isinstance(url, yarl.URL):
        parsed_url = yarl.URL(url)
    else:
        parsed_url = url
    if not parsed_url.absolute or parsed_url.host_port_subcomponent not in settings.domains:
        return None
    path_and_fragment = list(parsed_url.parts)
    if parsed_url.fragment:
        path_and_fragment.append(f"#{parsed_url.fragment}")
    _ = path_and_fragment.pop(0)

    if settings.require_strict_type:
        result = _parse_strict_numberable_url(parsed_url, settings=settings)
    else:
        result = _parse_loose_numberable_url(parsed_url, settings=settings)
    if result is not None:
        return result
    # Case normalisation is not performed on GitHub's end, so we do not do it here either.
    match path_and_fragment:
        case [""] | []:
            return None
        case [owner, *rest] if _valid_user(owner):
            if not rest:
                return models.User(login=owner)
            match rest:
                case [repository_name, *rest] if _valid_repository(repository_name):
                    repo = models.Repo(name=repository_name, owner=owner)
                    if not rest:
                        return repo
                    match rest:
                        case ["commit", sha] if settings.commits:
                            return models.Commit(repo=repo, sha=sha)
                        case ["commit", sha, fragment] if (
                            settings.commit_comments and fragment.startswith("#commitcomment-")
                        ):
                            comment_id = fragment[len("#commitcomment-") :]
                            try:
                                comment_id = int(comment_id)
                            except ValueError:
                                return None
                            return models.CommitComment(repo=repo, sha=sha, comment_id=comment_id)
                        case ["releases", "tag", tag] if settings.releases:
                            return models.ReleaseTag(repo=repo, tag=tag)
                        case ["commit", sha] if settings.commits:
                            return models.Commit(repo=repo, sha=sha)
                        case ["commit", sha, fragment] if (
                            settings.commit_comments and fragment.startswith("#commitcomment-")
                        ):
                            comment_id = fragment[len("#commitcomment-") :]
                            try:
                                comment_id = int(comment_id)
                            except ValueError:
                                return None
                            return models.CommitComment(repo=repo, sha=sha, comment_id=comment_id)
                        case ["releases", "tag", tag] if settings.releases:
                            return models.ReleaseTag(repo=repo, tag=tag)
                        case _:
                            return None
                case _:
                    return None
        case _:
            return None


def parse_shorthand(
    shorthand: str,
    *,
    default_user: str | None = None,
    settings: models.MatcherSettings = _DEFAULT_MATCHER_SETTINGS,
) -> models.GitHubResource | None:
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
        return models.Repo(name=repo, owner=user) if settings.short_repo else None

    ref = shorthand[len(repo) + 1 :]
    if ref_type == "#":
        try:
            number = int(ref)
        except ValueError:
            return None
        if number < 1:
            return None
        return (
            models.NumberedResource(repo=models.Repo(name=repo, owner=user), number=number)
            if settings.short_numberables
            else None
        )
    elif ref_type == "@":
        # Check the type of ref matches allowed patterns
        if not _validate_ref(ref):
            return None
        return (
            models.Ref(repo=models.Repo(name=repo, owner=user), ref=ref)
            if settings.short_refs
            else None
        )
    return None
