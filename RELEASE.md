# SPINE Learn releases

SPINE Learn's first release is **v0.1.0 — Initial public prototype**.
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

Completed on 2026-11-02 for `v0.1.0`. The versioned and `release` OCI tags were
validated against the successful release workflow artifact before the live
Application switched from `main` to `release`. The installed configuration is
recorded in `k8s/argocd/applications/spine-learn.yaml`; the `.example` file retains
the reviewed transition configuration.

Verification checks:

- Argo resolves the release channel to the intended bundle, reports Synced and
  Healthy, and records an automated sync.
- The running pod image matches the published bundle.
- Public readiness and tutor status succeed; homepage and lesson show `v0.1.0`
  and link to its tagged changelog.
- The executed notebook downloads and narration serves HTTP 206 byte ranges.
- One live tutor question returns HTTP 200 with a nonempty answer.

For later releases, publication and successful CI promotion deploy automatically.
For rollback, pause automatic sync and select the earlier immutable OCI bundle
as documented in [Argo operations](k8s/argocd/README.md#pause-and-rollback).
If still pinned to that digest, publishing a new release does not resume updates;
restore the release-channel Application configuration deliberately.
