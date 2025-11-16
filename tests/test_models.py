import dataclasses

import ghretos


class TestMatcherSettings:
    def test_none_is_none(self) -> None:
        """Test that MatcherSettings with all features disabled behaves correctly."""
        settings = ghretos.MatcherSettings.none()
        for attr in dataclasses.fields(settings):
            if attr.type is not bool:
                continue
            assert getattr(settings, attr.name) is False


def test_repo_full_name() -> None:
    repo = ghretos.Repo(name="myrepo", owner="owner")
    assert repo.full_name == "owner/myrepo"


def test_repo_html_url() -> None:
    repo = ghretos.Repo(name="myrepo", owner="owner")
    assert repo.html_url == "https://github.com/owner/myrepo"
