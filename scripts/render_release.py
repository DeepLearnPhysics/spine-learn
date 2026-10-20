"""Render an S3DF release bundle pinned to a tested, immutable container image."""

import argparse
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def render_release(image: str, destination: Path) -> None:
    """Write only application resources; never include credentials or bootstrap RBAC."""
    if not re.fullmatch(
        r"ghcr.io/deeplearnphysics/spine-learn@sha256:[a-f0-9]{64}", image
    ):
        raise ValueError("An immutable spine-learn GHCR image digest is required.")
    resources = []
    for filename in ("deployment.yaml", "service.yaml", "httproute.yaml"):
        resource = yaml.safe_load((ROOT / "k8s/base" / filename).read_text())
        resource["metadata"]["namespace"] = "spine-learn"
        if resource["kind"] == "Deployment":
            resource["spec"]["template"]["spec"]["containers"][0]["image"] = image
        resources.append(resource)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "release.yaml").write_text(
        yaml.safe_dump_all(resources, sort_keys=False)
    )
    (destination / "kustomization.yaml").write_text(
        "apiVersion: kustomize.config.k8s.io/v1beta1\n"
        "kind: Kustomization\nresources:\n  - release.yaml\n"
    )


def main() -> None:
    """Generate the artifact CI publishes and operators can apply manually."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "_build/s3df-release")
    arguments = parser.parse_args()
    render_release(arguments.image, arguments.output)


if __name__ == "__main__":
    main()
