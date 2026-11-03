# SPINE Learn on S3DF

The application serves the website and `/api/tutor/*` on one origin:
`https://spine-learn.slac.stanford.edu`. Deploy from an authenticated S3DF session
using the `neutrino-ml` context. The local Mac need not have a kubeconfig.

## Update the deployed application

SPINE Learn is managed by self-hosted Argo CD in the `neutrino-ml` vcluster.
Publish a vetted stable GitHub Release following [the release procedure](../RELEASE.md).
CI validates the tag and notes, builds and tests the container, and promotes its
bundle to the OCI `release` channel only if that release is still GitHub's latest
stable release. Argo follows that channel and deploys automatically, with
self-heal enabled and pruning disabled. No additional manual approval is needed.
Main-branch builds, drafts and prereleases do not advance production.

See [Argo CD operations](argocd/README.md) for private UI access, verification,
pausing automation, and rollback. Do not apply a competing release with kubectl
while automatic sync remains enabled. The manual first-rollout instructions
below are retained for bootstrap/recovery with Argo paused.

## Release flow

1. The existing **Narrated site** workflow runs checks, executes the lesson, and
   synthesizes only changed narration. GitHub Pages keeps its `/spine-learn/` build.
2. The workflow also builds the S3DF site with an empty `BASE_URL`, publishes it
   as the `s3df-site` artifact, and packages it with the matching tutor source.
3. For published stable releases, CI tests the container without a Gemini key, then publishes
   `ghcr.io/deeplearnphysics/spine-learn:sha-COMMIT`.
4. The `s3df-release` artifact contains a Deployment, Service, and HTTPRoute. The
   Deployment references the image by SHA-256 digest, not a mutable `latest` tag.
5. CI publishes the same manifests to
   `ghcr.io/deeplearnphysics/spine-learn-deploy:sha-COMMIT`. It gives the
   bundle its version tag and promotes `release` only for the latest stable
   GitHub Release.
6. Argo CD follows the promoted OCI `release` bundle and automatically syncs it to
   S3DF. No cluster credential or Gemini key is stored in GitHub Actions.

The first publication requires GitHub Actions package-write permission. Make
the application image package public so S3DF can pull anonymously, or configure
S3DF-approved registry pull credentials. Public source repositories do not
guarantee public packages. Never use the Gemini Secret for registry authentication.
The image and deployment-artifact packages were anonymously readable during
release verification; preserve that access or provision separate registry credentials.

CI currently uses the Flux CLI to publish the OCI deployment artifact. This is
an artifact-packaging step, not a Flux installation or an active deployment
controller. Argo CD reads this bundle with an explicit media-type configuration
and resolves the stable-release channel to an immutable artifact digest.

## GitHub CLI setup on S3DF

Load the available module and authenticate before downloading a release. For an
occasional manual deployment, use a temporary configuration directory so the
GitHub credential does not remain in your home or shared checkout:

```bash
module load githubcli
export GH_CONFIG_DIR=$(mktemp -d /tmp/spine-learn-gh.XXXXXX)
gh auth login --hostname github.com --git-protocol https --web
```

Open the displayed URL in your laptop's browser and enter the code. If asked to
authenticate Git too, choose **No**; artifact downloads do not need Git credential
configuration. If no system credential store is available, `gh` may warn that it
will save the token as plain text in this temporary, private directory. Continue
in the same shell so the download uses this configuration. Cleanup commands are
provided immediately after the download below.

## First rollout from S3DF

Use the existing login and vcluster setup documented at
https://k8s.slac.stanford.edu/neutrino-ml. In a checkout of this repository:

```bash
kubectl config current-context  # Must be neutrino-ml before proceeding.
kubectl apply -f k8s/namespace.yaml
```

Provision the Gemini key once with the interactive helper:

```bash
bash k8s/create-gemini-secret.sh
```

Paste the key at the prompt. Input is hidden, and the helper sends the key directly
through standard input to Kubernetes: no key file is created, and the key is not
included in shell history or process arguments. Do not pass the key as an argument.
The helper displays the current context and creates `spine-learn-gemini` in the
`spine-learn` namespace. It fails if the Secret already exists, preserving the
existing credential; it is not a key-rotation command.

The Deployment reads this Kubernetes Secret. No copy is needed in your home,
checkout, or shared S3DF filesystem. Kubernetes access controls protect the
Secret; cluster administrators and users allowed to read Secrets or control the
application's pods can still access the credential. Keep the key out of Git,
chat, and screenshots.

The deployment uses the `spine-learn` namespace in the `neutrino-ml` vcluster.
The current deployment uses public sample URLs and needs no PVC or filesystem
mount. Filesystem permissions can be added separately when lessons need them.

Download **s3df-release** from a successful **Narrated site** run for the
commit you want to deploy. List recent successful runs:

```bash
gh run list --repo DeepLearnPhysics/spine-learn \
  --workflow narration.yml --event release --status success --limit 5
```

Use the number in the **ID** column as `RUN_ID` below. You can also find it in
the browser: open **Actions → Narrated site → the successful run**. The number
at the end of `https://github.com/DeepLearnPhysics/spine-learn/actions/runs/NUMBER`
is the run ID (not the commit SHA or the workflow's sequential run number).
For example, `/actions/runs/39796096951` means `RUN_ID` is `39796096951`.
Choose a run that includes a successful `publish-s3df` job and the `s3df-release`
artifact, not a **Validate tutorial** run.

Replace `RUN_ID` with that number when downloading:

```bash
release_dir=$(mktemp -d /tmp/spine-learn-release.XXXXXX)
gh run download RUN_ID --repo DeepLearnPhysics/spine-learn \
  --name s3df-release --dir "$release_dir"
```

### Remove temporary GitHub authentication

After the download succeeds, remove the temporary GitHub authentication. Also
run this cleanup if you abandon the deployment after logging in:

```bash
gh auth logout --hostname github.com
rm -rf -- "${GH_CONFIG_DIR:?}"
unset GH_CONFIG_DIR
```

Deploy the downloaded release (GitHub authentication is no longer needed):

```bash
kubectl apply -k "$release_dir"
kubectl -n spine-learn rollout status deployment/spine-learn --timeout=180s
kubectl -n spine-learn get pods,service,httproute
kubectl -n spine-learn describe httproute spine-learn
```

Do not apply `k8s/base` directly: its image is deliberately a placeholder. CI's
release bundle contains the actual tested digest. For local rendering, use:

```bash
.venv/bin/python scripts/render_release.py \
  --image ghcr.io/deeplearnphysics/spine-learn@sha256:ACTUAL_IMAGE_DIGEST
```

The HTTPRoute deliberately omits `parentRefs`: S3DF's Kyverno policy injects them,
as configured by the S3DF platform team. It also omits `auth.sdf.slac.stanford.edu/required` because
this is a public learning site. Check the route's `Accepted` and `ResolvedRefs`
conditions and confirm the injected parent references before diagnosing a 404.

After rollout:

```bash
curl --fail https://spine-learn.slac.stanford.edu/readyz
curl --fail https://spine-learn.slac.stanford.edu/api/tutor/status
```

Open `/lesson`, check audio seeking and notebook download, and send one chat
question. The status and readiness checks do not consume Gemini requests;
**Check connection** and chat do. Keep the API key out of screenshots/logs.

## Self-managed Argo CD in neutrino-ml

Argo CD v3.5.6 is installed and verified in namespace `argocd`. Maintainers operate
it, with SLAC IT assistance for platform matters and possible Vault integration.
SPINE Learn follows the stable-release channel with automatic sync; spinal-tap
remains outside Argo management with its own disabled project reserved for later
onboarding.

See [the deployment and operations README](argocd/README.md) for the scoped
configuration, private access, CI release channel, health limitations, and tested
rollback procedure. Initial adoption, rollback to the previous successful build,
and automatic roll-forward were verified on 2026-11-02.

Gemini credentials remain separately managed Kubernetes Secrets. Application
permissions exclude Secret and Namespace management; pruning is disabled. The
HTTPRoute has no status exposed in this vcluster, so its aggregate Argo health
check is excluded. External readiness checks remain necessary.

### Rollback

Pause Argo automatic sync, select an earlier validated OCI bundle digest, then
sync without pruning. Verify workload and external readiness before resuming.
Follow the exact commands and caveats in [Argo CD operations](argocd/README.md#pause-and-rollback).
A kubectl-only rollback will be reverted by self-heal if Argo still targets the
newer release.

## Runtime scope

Gunicorn serves Flask with one process and four threads. The existing tutor
allows one in-flight generation, six requests per minute, and 200 per UTC day
per process (including connection checks and retry attempts). Transient upstream
HTTP errors receive at most one retry after one second within the remaining
45-second provider timeout budget. These are application safeguards,
not a provider billing cap: counters reset on process/pod restart. Keep the
Gemini project on the intended provider quota/billing configuration. There is no
user authentication or per-user allowance in this public service.

Use one replica and the supplied `Recreate` strategy so a rollout does not run
two independent tutor budgets. Updates cause a brief interruption. A shared,
persistent budget store is needed before adding replicas/workers or requiring
limits to survive restarts. Provider errors degrade chat without taking down
written lessons. Readiness checks require page and lesson files, not a live
Gemini call.

The runtime image contains only the generated public site, lesson context,
server code, and small runtime dependencies. It runs as UID 10001 with a read-only
root filesystem and a bounded temporary volume. It neither executes learner
code nor needs SPINE, a GPU, TTS models, or access to the host filesystem.

## Local production smoke test

```bash
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m spine_learn.build site --require-audio
docker build -f deploy/Dockerfile -t spine-learn:s3df-test .
.venv/bin/python scripts/smoke_container.py spine-learn:s3df-test --require-audio
```

This test uses a temporary loopback port, passes no key, and removes its container
on completion. It verifies static pages, portable downloads, status, and an
actual HTTP 206 audio range response under the read-only runtime settings.

Reference: [SLAC's route example](https://github.com/slaclab/slac-k8s-examples/blob/main/basic/httproutes/httproute-authnz.yaml).
