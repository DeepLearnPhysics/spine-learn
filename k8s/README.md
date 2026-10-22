# SPINE Learn on S3DF

The application serves the website and `/api/tutor/*` on one origin:
`https://spine-learn.slac.stanford.edu`. Deploy from an authenticated S3DF session
using the `neutrino-ml` context. The local Mac need not have a kubeconfig.

## Update an existing deployment

For routine updates, reuse the existing namespace, Gemini Secret, Service, and
HTTPRoute. Complete [GitHub CLI setup](#github-cli-setup-on-s3df) if this shell is
not authenticated, then select the successful release you want to deploy:

```bash
gh run list --repo DeepLearnPhysics/spine-learn \
  --workflow narration.yml --branch main --status success --limit 5
```

Use the **ID** column for the intended commit. Wait for the `publish-s3df` job to
succeed and provide `s3df-release`; a successful validation job alone is not a
release. Download into a fresh directory to avoid mixing releases:

```bash
read -r -p "Successful Narrated site run ID: " run_id
release_dir=$(mktemp -d /tmp/spine-learn-release.XXXXXX)
gh run download "$run_id" --repo DeepLearnPhysics/spine-learn \
  --name s3df-release --dir "$release_dir"
```

After a successful download, these are the deployment commands:

```bash
kubectl --context neutrino-ml apply -k "$release_dir"
kubectl --context neutrino-ml -n spine-learn rollout status deployment/spine-learn --timeout=180s
kubectl --context neutrino-ml -n spine-learn get pods
curl --fail https://spine-learn.slac.stanford.edu/readyz
```

The new image digest triggers the rollout; no separate `rollout restart` is
needed. Do not recreate the namespace or Gemini Secret. The single-replica
`Recreate` strategy causes a brief interruption. After rollout, refresh the
lesson and check playback, notebook download, and one chat response. If you used
temporary GitHub authentication, [clean it up](#remove-temporary-github-authentication).
To roll back manually, repeat these steps with an earlier successful run.

These instructions apply while releases are deployed manually. If a GitOps
controller is later enabled, update its desired release instead of applying a
competing manual version.

## Release flow

1. The existing **Narrated site** workflow runs checks, executes the lesson, and
   synthesizes only changed narration. GitHub Pages keeps its `/spine-learn/` build.
2. The workflow also builds the S3DF site with an empty `BASE_URL`, publishes it
   as the `s3df-site` artifact, and packages it with the matching tutor source.
3. CI tests the container without a Gemini key, then publishes
   `ghcr.io/deeplearnphysics/spine-learn:sha-COMMIT`.
4. The `s3df-release` artifact contains a Deployment, Service, and HTTPRoute. The
   Deployment references the image by SHA-256 digest, not a mutable `latest` tag.
5. CI publishes the same manifests to
   `ghcr.io/deeplearnphysics/spine-learn-deploy:sha-COMMIT`. It promotes the
   deployment artifact's `main` tag only if that commit is still GitHub's main head.
6. Until the planned S3DF-managed Argo CD integration is configured, download
   `s3df-release` and apply it manually using the update instructions above.
   No cluster credential or Gemini key is stored in GitHub Actions.

The first publication requires GitHub Actions package-write permission. Make
the application image package public so S3DF can pull anonymously, or configure
S3DF-approved registry pull credentials. Public source repositories do not
guarantee public packages. Never use the Gemini Secret for registry authentication.
Access to the separate deployment-artifact package will also need configuration
if it is selected as the Argo CD release source.

CI currently uses the Flux CLI to publish the OCI deployment artifact. This is
an artifact-packaging step, not a Flux installation or an active deployment
controller. The existing `k8s/flux/` manifests are an unused alternative from the
earlier deployment design; do not apply them for the planned Argo CD setup.

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
  --workflow narration.yml --branch main --status success --limit 5
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

## Planned automation with S3DF-managed Argo CD

The intended deployment controller is **Argo CD**, provisioned and maintained by
the S3DF platform team in the existing vcluster. The project maintainers will
configure which applications and releases it manages. Manual deployments remain
the supported procedure until that integration is ready.

Before enabling automatic deployment, agree with the platform team on:

- The Argo CD instance, access, and application/project permissions.
- The supported release source: the published OCI deployment bundle or a Git
  location containing rendered manifests with a tested image digest. Do not
  point Argo CD directly at `k8s/base`, which contains a placeholder image.
- Application scope for SPINE Learn and, separately, spinal-tap, so the shared
  infrastructure can support both without coupling their releases.
- Sync approval, pruning, health checks, and the procedure for pausing updates
  or selecting an earlier release.

The Gemini Secret remains provisioned separately in Kubernetes. Release manifests
must not include its value, and application pruning must not remove it. No Argo CD
Application manifests are supplied yet; the source integration and permissions
must be confirmed before documenting executable setup commands.

### Rollback

For the current manual deployment, download an earlier successful run's
`s3df-release` into a fresh directory and follow **Update an existing deployment**.
Once Argo CD manages the application, select the earlier release through its
configured source and sync workflow. A manual `kubectl` change alone is not a
lasting rollback if the controller still targets the newer release.

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
