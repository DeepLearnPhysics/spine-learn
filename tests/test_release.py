"""Keep deployable bundles pinned to tested images and free of secret material."""

from pathlib import Path

import pytest
import yaml

from scripts.render_release import render_release


def test_release_contains_only_pinned_application_resources(tmp_path: Path) -> None:
    """Render a public route without overriding S3DF's injected Gateway references."""
    image = "ghcr.io/deeplearnphysics/spine-learn@sha256:" + "a" * 64
    render_release(image, tmp_path)
    objects = list(yaml.safe_load_all((tmp_path / "release.yaml").read_text()))
    assert [obj["kind"] for obj in objects] == ["Deployment", "Service", "HTTPRoute"]
    assert all(obj["metadata"]["namespace"] == "spine-learn" for obj in objects)
    pod = objects[0]["spec"]["template"]["spec"]
    assert pod["containers"][0]["image"] == image
    assert pod["automountServiceAccountToken"] is False
    assert "parentRefs" not in objects[2]["spec"]
    assert "annotations" not in objects[2]["metadata"]
    assert objects[2]["spec"]["rules"][0]["backendRefs"][0]["port"] == 8080
    with pytest.raises(ValueError, match="immutable"):
        render_release("ghcr.io/deeplearnphysics/spine-learn:latest", tmp_path)
