# SPINE Learn releases

SPINE Learn's first release target is **v0.1.0 — Initial public prototype**.
Its version is independent of the SPINE library version used by the lesson.

`VERSION` holds the intended stable version without the `v` prefix. Local, pull
request and main-branch site builds display `vVERSION-dev`. A published stable
GitHub Release supplies `SPINE_LEARN_RELEASE` to CI; its tag must equal `vVERSION`,
and `CHANGELOG.md` must contain a matching dated version section. Both the
homepage and lesson display the version and link to the corresponding changelog.

## Prepare a release

1. Update `CHANGELOG.md` under **Unreleased** as changes land, using SPINE-style
   Added, Changed, Fixed, Tests and Migration notes sections where appropriate.
2. Choose a version: `v0.1.0` for the initial prototype, patch versions for fixes,
   and minor versions for substantial additions while the project is pre-1.0.
3. Set `VERSION`, and move the release notes into `## [0.1.0] - YYYY-MM-DD` using
   the actual release date. Keep an Unreleased section for subsequent changes.
4. Review and merge the release preparation. Wait for both validation and
   Narrated site builds on that exact commit to pass. Review the generated
   preview, lesson, narration and downloads. Main builds do not update S3DF.
5. Publish a stable GitHub Release with tag `v0.1.0` pointing to that exact
   validated commit, using the changelog section as release notes. A tag push
   alone does not trigger publication. Do not move or reuse published tags.

The published-release workflow checks out the release commit, validates the tag
and notes, rebuilds the narrated site, tests the exact container, and publishes
image and OCI bundle references by commit. The OCI bundle also receives the
release version tag. Only GitHub's latest published stable release may advance
the mutable `release` deployment channel. Releases are serialized to avoid
concurrent channel promotions. Draft and prerelease publication does not deploy.
GitHub Pages remains a main-branch development preview with the `-dev` label.

A failed release build does not advance the deployment channel. Argo sync/health
and external checks remain necessary to confirm deployment success; there is no
automatic rollback or external HTTP monitor.

## One-time S3DF channel transition

The installed Application still follows the last successful **main** OCI channel.
The proposed workflow stops advancing that channel; the existing site remains
served. Do not point Argo at `release` until the first release successfully
publishes it, and do not apply the template with a `.example` suffix by accident.

After the first release succeeds, inspect its bundle: exactly Deployment,
Service and HTTPRoute in namespace `spine-learn`, with the tested image pinned
by digest and no credentials. Review the channel switch, then apply the prepared
`k8s/argocd/applications/spine-learn-release.yaml.example` and verify:

- Argo resolves the `release` channel to the intended bundle and reports Synced
  and Healthy, with automatic sync enabled and pruning disabled.
- The running pod image matches the published bundle.
- Public `/readyz`, `/api/tutor/status`, homepage and lesson work; both pages show
  `v0.1.0` and link to its changelog.
- Audio, notebook download, and a deliberately chosen chat request work.

Once verified, make `applications/spine-learn.yaml` record the live `release`
source and update the Argo operations README. This transition changes deployed
configuration and requires maintainer review. No live change is made merely by
editing this repository.

For later releases, publication and successful CI promotion deploy automatically.
For rollback, pause automatic sync and select the earlier immutable OCI bundle
as documented in [Argo operations](k8s/argocd/README.md#pause-and-rollback).
If still pinned to that digest, publishing a new release does not resume updates;
restore the release-channel Application configuration deliberately.
