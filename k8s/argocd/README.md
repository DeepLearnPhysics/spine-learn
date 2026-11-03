# Self-managed Argo CD on S3DF

Argo CD **v3.5.6** runs in namespace `argocd` inside the existing `neutrino-ml`
vcluster. Maintainers operate it; SLAC IT assists with platform matters and
potential future Vault integration. SPINE Learn is managed automatically.
spinal-tap has a separate, disabled project and is not yet managed by Argo.

## Release behavior

A successful **Narrated site** build publishes the tested application image and
an OCI deployment bundle. CI promotes the bundle's `main` tag only when that
commit is still the repository's main head. Argo polls that promoted tag and
syncs it automatically, including self-healing drift. No routine approval is
required. A new release can take several minutes to be detected and rolled out.
The application image inside every bundle is pinned by SHA-256 digest.

The repository currently has no Git tags or GitHub Releases: this channel follows
successful builds on `main`. Tagged-release-only promotion would require a CI
change. Argo does not build the site or manage the Gemini key. Flux CLI only
packages the OCI bundle; no Flux controller is installed.

The active configuration is [applications/spine-learn.yaml](applications/spine-learn.yaml).
It uses `oci://ghcr.io/deeplearnphysics/spine-learn-deploy`, `targetRevision: main`,
and `path: .`. The package is anonymously readable. The repo-server explicitly
accepts Flux's `application/vnd.cncf.flux.content.v1.tar+gzip` layer type.
Never point Argo at `k8s/base`, which contains a placeholder image.

Automatic pruning is **disabled**, and application RBAC disallows resource
deletion. Applications have no deletion finalizer and cannot create Namespaces.
Gemini credentials and namespace provisioning remain separate. Renames and
resource removals require a deliberate reviewed cleanup.

## Access and status

Use your normal S3DF Kubernetes login, then load `module load kubectl`.
The available 1.30.3 client worked for installation and server validation against
server 1.35.6, although this is outside the supported version skew. Use a newer
client if a compatibility issue appears.

```bash
kubectl --context neutrino-ml -n argocd get pods
kubectl --context neutrino-ml -n argocd get application spine-learn
kubectl --context neutrino-ml -n spine-learn get pods
curl --fail https://spine-learn.slac.stanford.edu/readyz
curl --fail https://spine-learn.slac.stanford.edu/api/tutor/status
```

The UI/API is private, behind ClusterIP services. Start a loopback forward:

```bash
kubectl --context neutrino-ml -n argocd port-forward --address 127.0.0.1 svc/argocd-server 8080:443
```

On your laptop, tunnel to the exact machine running that command (use
`hostname -f` in the S3DF terminal). Internal hosts may require your normal S3DF
login address as a jump host:

```bash
ssh -J drielsma@YOUR_S3DF_LOGIN_HOST -N -o ExitOnForwardFailure=yes \
  -L 8080:127.0.0.1:8080 drielsma@EXACT_INTERNAL_HOSTNAME
```

Open `https://localhost:8080`. Keep both tunnels running during browser access;
closing them does not stop Argo or deployments. The certificate is self-signed.
Sign in as `admin` using the permanent password stored privately by the
maintainer. The maintainer changed the bootstrap password after installation.

For a fresh installation only, retrieve the bootstrap password privately:

```bash
kubectl --context neutrino-ml -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 --decode
```

Do not paste its output into chat, logs, Git, or screenshots. Change the admin
password in **User Info → Update Password**, confirm a fresh login works, then
remove `argocd-initial-admin-secret`. Deleting that Secret does not change the
active admin password. SSO, Vault,
and shared administrative access are future platform work. No public route,
Ingress, NodePort, or LoadBalancer exposes Argo.

## Health and rollout

A sync changes only Deployment, Service, and HTTPRoute in namespace `spine-learn`.
The single-replica `Recreate` strategy briefly interrupts service during image
updates. Deployment readiness and liveness probes drive workload health.

The vcluster exposes no HTTPRoute status or parentRefs even though the public
site works. Argo would otherwise wait indefinitely for route health. An
Application-level Kustomize patch annotates **only this HTTPRoute** with
`argocd.argoproj.io/ignore-healthcheck: "true"`. The route remains managed, but
its status does not contribute to aggregate Application health. `Healthy` is
therefore not proof of public routing: use the external checks above. There is
no continuous external HTTP monitor or automatic rollback configured.
The configuration also preserves platform-injected parentRefs if they appear.

After a release, check Synced/Healthy, the expected image, readiness and tutor
status. Playback, seeking, notebook downloads and a deliberately chosen chat
request are additional end-to-end checks; chat consumes provider requests.

## Pause and rollback

Do not use `kubectl rollout undo` while automated reconciliation still targets
the newer bundle. Pause automatic sync and select a known successful **OCI
manifest digest**, which differs from the application image digest:

```bash
kubectl --context neutrino-ml -n argocd patch application spine-learn --type merge \
  -p '{"spec":{"syncPolicy":{"automated":{"enabled":false}}}}'
```

In the private Argo UI, set the source revision to the chosen `sha256:...` bundle
digest, then Sync with pruning unchecked. Confirm Synced/Healthy, the running
image and public endpoints. This holds the selected release until resumed.
Keep the active configuration file aligned if this is a lasting rollback.

To resume the successful-main channel after resolving the problem:

```bash
kubectl --context neutrino-ml apply -f k8s/argocd/applications/spine-learn.yaml
kubectl --context neutrino-ml -n argocd annotate application spine-learn \
  argocd.argoproj.io/refresh=hard --overwrite
```

That re-enables automatic sync and self-heal, keeps pruning off, and deploys the
currently promoted bundle. Resuming without a corrected release may redeploy
the version you rolled back. Argo does not automatically judge website behavior
or roll back an unhealthy release.

## Installation record and reproducibility

Installed and verified on 2026-11-02 using the existing kubectl module. The three
pinned CRDs in `crds/` were installed with server-side apply without forcing
ownership conflicts; namespace installation and scoped RBAC passed server dry
runs. This directory records the installed configuration; Argo itself is not
self-managed, so editing these files alone does not update its installation.

- `namespace.yaml`: dedicated namespace.
- `install/`: vendored upstream namespace installation plus readable patches;
  render with `kubectl kustomize k8s/argocd/install`.
- `install/vendor/SHA256SUMS`: downloaded upstream file checksum for reproducibility,
  not independent publisher signature verification.
- `install/local-cluster.yaml`: Secret-shaped non-sensitive cluster configuration,
  no token. Controller authentication uses its Kubernetes service account.
- `spine-learn-rbac.yaml`: workload writes and health reads confined to the
  application namespace; no Secret, RBAC, namespace, exec, or delete grant there.
- `projects.yaml`: restricted SPINE Learn project, denied default project, and
  disabled spinal-tap project. spinal-tap has no controller namespace permissions.
- `applications/spine-learn.yaml.example`: pinned adoption/reference configuration;
  `spinal-tap.yaml.example`: inactive onboarding template requiring separate review.

Argo's own namespace retains upstream runtime permissions to operate credentials.
Application workload write access can indirectly use application credentials, so
protect Argo administrator access and CI publishing rights. No credentials are
stored in these repository files.

Four active components: application-controller, repo-server, server, Redis. Dex,
ApplicationSet and notifications deployments have zero replicas. Non-HA operation
means an Argo outage pauses deployment management; application pods continue.
Steady-state requests total 500m CPU/960Mi memory; limits total 2.75 CPU/2816Mi,
plus transient initialization. No ResourceQuota or LimitRange was reported;
virtual node allocatable is not a guarantee of free host capacity.

Verification exercised initial adoption without changing the running image,
rollback to the previous successful build, and automatic roll-forward to main.
Rollback readiness and tutor status checks passed without making a Gemini call.
The previous release used bundle
`sha256:e7cca46b4b004ba27f1a70c2a063e9e535e220f36cea95dc94d50622b58c3ea0`.
The restored current bundle was
`sha256:7529012b9accb6da2bfba039238a94b2660f818694be423f2942b3fb324a36a4`,
with image
`ghcr.io/deeplearnphysics/spine-learn@sha256:3ef17cce22c68e196d0654cede2d049013caedee36adf822ba887d12e226ddc9`.
The `main` channel can advance after this record. A newly published CI release
has not been created solely for this test; automatic reconciliation was tested by
returning the Application from the pinned prior release to the promoted channel.

Do not recursively apply this directory. Reinstalling/upgrading Argo, enabling
pruning, adding applications, and public/SSO access need their own review.
`inspect.sh` remains a read-only metadata/permissions inspection helper.

References: [installation](https://argo-cd.readthedocs.io/en/stable/operator-manual/installation/),
[OCI requirements](https://argo-cd.readthedocs.io/en/stable/user-guide/oci/),
[resource health exclusions](https://argo-cd.readthedocs.io/en/stable/operator-manual/health/#ignoring-child-resource-health-check-in-applications),
[Flux OCI format](https://fluxcd.io/flux/cheatsheets/oci-artifacts/).
