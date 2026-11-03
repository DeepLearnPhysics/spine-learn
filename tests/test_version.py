"""Prevent development previews and mismatched tags from posing as releases."""

from pathlib import Path

import pytest

from spine_learn import version


@pytest.fixture
def version_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use an isolated release record without changing the repository files."""
    (tmp_path / "VERSION").write_text("0.1.0\n")
    (tmp_path / "CHANGELOG.md").write_text("## [0.1.0] - 2026-11-02\n")
    monkeypatch.setattr(version, "ROOT", tmp_path)
    monkeypatch.delenv("SPINE_LEARN_RELEASE", raising=False)
    return tmp_path


def test_preview_and_release_labels(
    version_source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep preview labels honest and link releases to their own changelog."""
    assert version.site_version() == "v0.1.0-dev"
    assert "blob/main/CHANGELOG.md" in version.version_notice()
    monkeypatch.setenv("SPINE_LEARN_RELEASE", "v0.1.0")
    assert version.site_version() == "v0.1.0"
    assert "blob/v0.1.0/CHANGELOG.md" in version.version_notice()
    (version_source / "CHANGELOG.md").write_text("## [Unreleased]\n")
    with pytest.raises(ValueError, match="dated CHANGELOG"):
        version.site_version()


@pytest.mark.parametrize("tag", ["v0.2.0", "0.1.0", "v0.1.0-rc.1", "<script>"])
def test_release_tag_must_match_version(
    version_source: Path, monkeypatch: pytest.MonkeyPatch, tag: str
) -> None:
    """Fail a release build instead of displaying an incorrect version."""
    monkeypatch.setenv("SPINE_LEARN_RELEASE", tag)
    with pytest.raises(ValueError, match="match VERSION"):
        version.site_version()


def test_homepage_contains_version_and_changelog(
    tmp_path: Path, version_source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise the actual staged homepage, not just a version helper string."""
    from spine_learn.build import _write_site_configuration

    site = tmp_path / "site"
    site.mkdir()
    _write_site_configuration(site)
    page = (site / "index.md").read_text()
    assert "SPINE Learn **v0.1.0-dev**" in page
    assert "[Changelog](https://github.com/DeepLearnPhysics/spine-learn/" in page
