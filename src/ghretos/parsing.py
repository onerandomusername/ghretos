import string

import yarl

from ghretos import models

__all__ = (
    "parse_url",
    "parse_shorthand",
)


_DEFAULT_MATCHER_SETTINGS = models.MatcherSettings()


def _get_id_from_fragment(url: yarl.URL, prefix: str) -> str | None:
    fragment = url.fragment
    if fragment.startswith(prefix):
        return fragment[len(prefix) :]
    return None


def _parse_strict_url(
    parsed_url: yarl.URL,
    *,
    settings: models.MatcherSettings,
):
    path_and_fragment = list(parsed_url.parts)
    if parsed_url.fragment:
        path_and_fragment.append(f"#{parsed_url.fragment}")
    _ = path_and_fragment.pop(0)
    match path_and_fragment:
        # User
        case [owner]:
            return models.User(login=owner)
        # Repository
        case [owner, repo]:
            return models.Repo(name=repo, owner=owner)
        case [owner, repo, "issues", resource_id] if settings.issues:
            if not resource_id.isdigit():
                return None
            return models.Issue(
                repo=models.Repo(name=repo, owner=owner), number=int(resource_id)
            )
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
                return models.Issue(
                    repo=models.Repo(name=repo, owner=owner), number=int(resource_id)
                )
            else:
                return models.PullRequest(
                    repo=models.Repo(name=repo, owner=owner), number=int(resource_id)
                )
        case [owner, repo, "pull", resource_id] if settings.pull_requests:
            if not resource_id.isdigit():
                return None
            return models.PullRequest(
                repo=models.Repo(name=repo, owner=owner), number=int(resource_id)
            )
        case [owner, repo, "discussions", resource_id] if settings.discussions:
            if not resource_id.isdigit():
                return None
            return models.Discussion(
                repo=models.Repo(name=repo, owner=owner), number=int(resource_id)
            )
        case [owner, repo, "discussions", resource_id, fragment] if (
            settings.discussions and fragment.startswith("#discussion-")
        ):
            if not resource_id.isdigit():
                return None
            return models.Discussion(
                repo=models.Repo(name=repo, owner=owner), number=int(resource_id)
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
            return models.PullRequestReviewComment(
                repo=models.Repo(name=repo, owner=owner),
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
            return models.PullRequestReviewComment(
                repo=models.Repo(name=repo, owner=owner),
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
            return models.Issue(
                repo=models.Repo(name=repo, owner=owner), number=int(resource_id)
            )
        # Issue comments
        case [owner, repo, "issues", resource_id, fragment] if (
            settings.issue_comments and fragment.startswith("#issuecomment-")
        ):
            if not resource_id.isdigit():
                return None
            comment_id = fragment[len("#issuecomment-") :]
            if not comment_id.isdigit():
                return None
            return models.IssueComment(
                repo=models.Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(comment_id),
            )
        # Pull request comments
        case [owner, repo, "pull", resource_id, fragment] if (
            settings.pull_request_comments and fragment.startswith("#issuecomment-")
        ):
            if not resource_id.isdigit():
                return None
            comment_id = fragment[len("#issuecomment-") :]
            if not comment_id.isdigit():
                return None
            return models.PullRequestComment(
                repo=models.Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(comment_id),
            )
        # Issue events
        case [owner, repo, "issues", resource_id, fragment] if (
            settings.issue_events and fragment.startswith("#event-")
        ):
            if not resource_id.isdigit():
                return None
            event_id = fragment[len("#event-") :]
            if not event_id.isdigit():
                return None
            return models.IssueEvent(
                repo=models.Repo(name=repo, owner=owner),
                number=int(resource_id),
                event_id=int(event_id),
            )
        # Pull request events
        case [owner, repo, "pull", resource_id, fragment] if (
            settings.pull_request_events and fragment.startswith("#event-")
        ):
            if not resource_id.isdigit():
                return None
            event_id = fragment[len("#event-") :]
            if not event_id.isdigit():
                return None
            return models.PullRequestEvent(
                repo=models.Repo(name=repo, owner=owner),
                number=int(resource_id),
                event_id=int(event_id),
            )
        # Pull request reviews
        case [owner, repo, "pull", resource_id, fragment] if (
            settings.pull_request_reviews and fragment.startswith("#pullrequestreview-")
        ):
            if not resource_id.isdigit():
                return None
            review_id = fragment[len("#pullrequestreview-") :]
            if not review_id.isdigit():
                return None
            return models.PullRequestReview(
                repo=models.Repo(name=repo, owner=owner),
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
            comment_id = fragment[len("#discussion_r") :]
            if not comment_id.isdigit():
                return None
            return models.PullRequestReviewComment(
                repo=models.Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(comment_id),
            )
        # Discussion comments
        case [owner, repo, "discussions", resource_id, fragment] if (
            settings.discussion_comments and fragment.startswith("#discussioncomment-")
        ):
            if not resource_id.isdigit():
                return None
            comment_id = fragment[len("#discussioncomment-") :]
            if not comment_id.isdigit():
                return None
            return models.DiscussionComment(
                repo=models.Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(comment_id),
            )
        case _:
            return None


def _parse_unstrict_url(parsed_url: yarl.URL, *, settings: models.MatcherSettings):
    ...

    path_and_fragment = list(parsed_url.parts)
    if parsed_url.fragment:
        path_and_fragment.append(f"#{parsed_url.fragment}")
    _ = path_and_fragment.pop(0)
    match path_and_fragment:
        # User
        case [owner]:
            return models.User(login=owner)
        # Repository
        case [owner, repo]:
            return models.Repo(name=repo, owner=owner)
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
                    return models.Issue(
                        repo=models.Repo(name=repo, owner=owner),
                        number=int(resource_id),
                    )
            elif resource_type == "pull":
                if settings.pull_requests:
                    return models.PullRequest(
                        repo=models.Repo(name=repo, owner=owner),
                        number=int(resource_id),
                    )
            elif resource_type == "discussions":
                if settings.discussions:
                    return models.Discussion(
                        repo=models.Repo(name=repo, owner=owner),
                        number=int(resource_id),
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
                    return models.PullRequest(
                        repo=models.Repo(name=repo, owner=owner),
                        number=int(resource_id),
                    )
                return models.Issue(
                    repo=models.Repo(name=repo, owner=owner), number=int(resource_id)
                )
            elif fragment.startswith("#discussion-"):
                return models.Discussion(
                    repo=models.Repo(name=repo, owner=owner), number=int(resource_id)
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
            return models.PullRequestReviewComment(
                repo=models.Repo(name=repo, owner=owner),
                number=int(resource_id),
                comment_id=int(fragment),
            )
        # Pull request review comments on commits page with SHA (allow /issues/ URLs)
        case [
            owner,
            repo,
            "issues" | "pull",
            resource_id,
            "commits",
            sha,
            fragment,
        ] if settings.pull_request_review_comments and (
            fragment := _get_id_from_fragment(parsed_url, "r")
        ):
            if not resource_id.isdigit():
                return None
            # Validate SHA is hexadecimal
            try:
                int(sha, 16)
            except ValueError:
                return None
            return models.PullRequestReviewComment(
                repo=models.Repo(name=repo, owner=owner),
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
            return models.PullRequestReviewComment(
                repo=models.Repo(name=repo, owner=owner),
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
    settings: models.MatcherSettings = _DEFAULT_MATCHER_SETTINGS,
) -> models.GitHubResource | None:
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
    _ = path_and_fragment.pop(0)

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
            return models.User(login=owner)
        case [owner, repo]:
            return models.Repo(name=repo, owner=owner)
        case [owner, repo, "commit", sha] if settings.commits:
            return models.Commit(repo=models.Repo(name=repo, owner=owner), sha=sha)
        case [owner, repo, "commit", sha, fragment] if (
            settings.commit_comments and fragment.startswith("#commitcomment-")
        ):
            comment_id = fragment[len("#commitcomment-") :]
            if not comment_id.isdigit():
                return None
            return models.CommitComment(
                repo=models.Repo(name=repo, owner=owner),
                sha=sha,
                comment_id=int(comment_id),
            )
        case [owner, repo, "releases", "tag", tag] if settings.releases:
            return models.ReleaseTag(repo=models.Repo(name=repo, owner=owner), tag=tag)
        case [owner, repo, "commit", sha] if settings.commits:
            return models.Commit(repo=models.Repo(name=repo, owner=owner), sha=sha)
        case [owner, repo, "commit", sha, fragment] if (
            settings.commit_comments and fragment.startswith("#commitcomment-")
        ):
            comment_id = fragment[len("#commitcomment-") :]
            if not comment_id.isdigit():
                return None
            return models.CommitComment(
                repo=models.Repo(name=repo, owner=owner),
                sha=sha,
                comment_id=int(comment_id),
            )
        case [owner, repo, "releases", "tag", tag] if settings.releases:
            return models.ReleaseTag(repo=models.Repo(name=repo, owner=owner), tag=tag)
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
        if not ref.isdigit():
            return None
        return (
            models.NumberedResource(
                repo=models.Repo(name=repo, owner=user), number=int(ref)
            )
            if settings.short_numberables
            else None
        )
    elif ref_type == "@":
        return (
            models.ReleaseTag(repo=models.Repo(name=repo, owner=user), tag=ref)
            if settings.short_refs
            else None
        )
    return None
