# Changelog

Notable changes to SPINE Learn are recorded here, following the version sections
and change categories used by [SPINE](https://github.com/DeepLearnPhysics/spine/blob/main/CHANGELOG.md).
SPINE Learn has its own release numbers, independent of the SPINE library.

## [Unreleased]

## [0.1.0] - 2026-11-02

Initial public prototype.

### Added

- Executable lesson introducing points, particles, interactions, and selections
  using public sample data and SPINE 1.4.1.
- Guided narration with transcripts, audio seeking, and portable notebook,
  Colab, and static-figure downloads.
- Ask SPINE lesson companion with separately managed Gemini credentials,
  request limits, and graceful handling of provider failures.
- SPINE branding and light/dark presentation.
- Release version and changelog links on the homepage and lesson.
- Tested runtime containers and digest-pinned OCI deployment bundles.
- Self-managed Argo CD in the S3DF `neutrino-ml` vcluster, with scoped application
  permissions, private administrative access, and automatic synchronization.

### Changed

- Release-only deployment promotion: successful development builds
  remain previews; published stable releases advance the S3DF release channel.

### Tests

- CI validates the lesson, narration, static assets, runtime container, and
  deployment bundle image pinning.
- Verified Argo adoption, rollback, automatic roll-forward, and automatic
  deployment after a successful CI publication.

### Migration notes

- Argo's live source currently follows `main`. Switch it to the `release` OCI
  channel only after the first vetted stable release publishes that channel.
- Application Secrets remain separately provisioned; automatic pruning is off.
- The single-replica Recreate rollout briefly interrupts service.
