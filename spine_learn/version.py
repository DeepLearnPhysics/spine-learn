"""Identify released sites and distinguish them from development previews."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def site_version() -> str:
    """Return the release tag, rejecting mismatches before building the site.

    A source checkout alone is not a published release. CI sets
    ``SPINE_LEARN_RELEASE`` only for published releases; other builds carry
    a development suffix even when preparing the same version number.
    """
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
        raise ValueError("VERSION must contain a stable MAJOR.MINOR.PATCH version.")
    release = os.environ.get("SPINE_LEARN_RELEASE", "")
    if release:
        if release != f"v{version}":
            raise ValueError(
                "Release tag must match VERSION exactly (vMAJOR.MINOR.PATCH)."
            )
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        if not re.search(
            rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$",
            changelog,
            re.MULTILINE,
        ):
            raise ValueError("Published releases require a dated CHANGELOG entry.")
        return release
    return f"v{version}-dev"


def version_notice() -> str:
    """Render a small version and changelog notice for the generated site."""
    version = site_version()
    ref = "main" if version.endswith("-dev") else version
    url = f"https://github.com/DeepLearnPhysics/spine-learn/blob/{ref}/CHANGELOG.md"
    return f"\n\n---\n\nSPINE Learn **{version}** · [Changelog]({url})\n"


if __name__ == "__main__":
    print(site_version())
