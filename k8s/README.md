# SPINE Learn on S3DF

The application serves the website and `/api/tutor/*` on one origin:
`https://spine-learn.slac.stanford.edu`. Deploy from an authenticated S3DF session
using the `neutrino-ml` context. The local Mac need not have a kubeconfig.

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
6. Once S3DF provides/configures Flux, its source controller polls that artifact
   every two minutes and reconciles the new release. No cluster credential or
   Gemini key is stored in GitHub Actions. No Git write token is needed by Flux.

The first publication requires GitHub Actions package-write permission. After it
finishes, make **both GHCR packages public** in their package settings so S3DF can
pull anonymously. Public source repositories do not guarantee public packages.
Alternatively, configure S3DF-approved registry pull credentials in both the
workload and Flux source; never use the Gemini Secret for registry authentication.

This repository prepares Flux resources but does not install cluster controllers.
Confirm with Micha that the controllers support `source.toolkit.fluxcd.io/v1`
`OCIRepository`, watch `spine-learn`, allow the specified reconciler service account,
and can pull from GHCR. If S3DF manages Flux centrally, give them `flux/sync.yaml`
to adapt rather than installing a second controller stack.

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

The namespace is proposed as `spine-learn`; confirm it is allowed in the vcluster.
The current deployment uses public sample URLs and needs no PVC or filesystem
mount. Filesystem permissions can be added separately when lessons need them.

Download **s3df-release** from the successful Narrated site workflow for the
chosen commit. With GitHub CLI (replace `RUN_ID` with that workflow run's ID):

```bash
gh run download RUN_ID --repo DeepLearnPhysics/spine-learn \
  --name s3df-release --dir /tmp/spine-learn-release
kubectl apply -k /tmp/spine-learn-release
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
as advised by Micha. It also omits `auth.sdf.slac.stanford.edu/required` because
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

## Enable automatic reconciliation

After Flux support is confirmed and both registry packages are accessible:

```bash
kubectl apply -f k8s/flux/sync.yaml
kubectl -n spine-learn get ocirepositories,kustomizations
```

The reconciler is namespace-scoped and may manage only Deployments, Services,
and HTTPRoutes. The namespace, Gemini Secret, and Flux bootstrap resources are
not part of the continuously pruned release bundle. The application itself has
no Kubernetes API token mounted.

Once enabled, a successful main build updates the site and lesson context
together. Editing the HTTPRoute or backend configuration uses the same release
path. Failed builds and smoke tests do not promote the deployment artifact.
Flux reports unhealthy deployments; it does **not** automatically roll back a
release that passes CI but fails in S3DF.

## Rollback or pause automation

To hold deployment updates without stopping the app:

```bash
kubectl -n spine-learn patch kustomization spine-learn --type=merge \
  -p '{"spec":{"suspend":true}}'
```

To choose a previous published release, set the OCI source to its full commit
SHA tag and resume reconciliation:

```bash
kubectl -n spine-learn patch ocirepository spine-learn --type=merge \
  -p '{"spec":{"ref":{"tag":"sha-PREVIOUS_FULL_COMMIT_SHA"}}}'
kubectl -n spine-learn patch kustomization spine-learn --type=merge \
  -p '{"spec":{"suspend":false}}'
```

To follow CI again, change that source tag back to `main`. Without Flux, apply
the older run's `s3df-release` artifact. Do not rely on `rollout undo` while Flux
continues reconciling a newer desired image.

## Runtime scope

Gunicorn serves Flask with one process and four threads. The existing tutor
allows one in-flight generation, six requests per minute, and 200 per UTC day
per process (including connection checks). These are application safeguards,
not a provider billing cap: counters reset on process/pod restart. Keep the
Gemini project on the intended provider quota/billing configuration. There is no
user authentication or per-user allowance in this public demonstrator.

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

References: [Flux OCI sources](https://fluxcd.io/flux/components/source/ocirepositories/),
[Flux artifact publishing](https://fluxcd.io/flux/cmd/flux_push_artifact/), and
[SLAC's route example](https://github.com/slaclab/slac-k8s-examples/blob/main/basic/httproutes/httproute-authnz.yaml).
