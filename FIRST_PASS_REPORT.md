# First-pass implementation report

This report records the original local first pass tested on 2026-10-07.
Later changes are recorded in the follow-up notes below. The repository now contains a working executable
lesson and actual Docker-generated narration. The website and notebook use
**SPINE 1.4.0 from PyPI**. Publication and expert audio review remain outstanding.

## Delivered structure and files

All files are new; the starting repository contained only `.git`.

```text
README.md                      setup, architecture, authoring, CI, limitations
FIRST_PASS_REPORT.md            acceptance evidence and measured results
requirements.txt               pinned direct tutorial/site dependencies
pyproject.toml                 test configuration
Makefile                       maintainer commands
.gitignore                     derived artifacts, model caches, virtualenv
 tutorials/01_reconstruction_basics.md
 narration/01_reconstruction_basics.yaml
 narration/pronunciations.yaml
 narration/config.yaml
 narration/terminology.yaml
 spine_learn/__init__.py
 spine_learn/build.py
 spine_learn/narration.py
 spine_learn/kokoro_backend.py
 tts/Dockerfile
 tts/requirements.txt
 tts/README.md
 scripts/benchmark_narration.py
 scripts/verify_site.py
 tests/test_narration.py
 tests/test_notebook.py
 .github/workflows/ci.yml
 .github/workflows/narration.yml
```

The full command reference is in the README. The key sequence is:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
make test narration-check notebook
make tts-image
mkdir -p .cache/kokoro
make narration narration-status site
make serve
```

## Toolchain, topic, and source flow

MyST CLI 1.11.0 and its book theme supply navigation, structured notebook
rendering, and static HTML export. Jupytext 1.19.6 converts the canonical MyST
Markdown to a notebook; nbclient 0.11.0 executes it before either delivery path.
This follows the modern MyST ecosystem instead of extending the older
Sphinx/Jupyter Book architecture in the historical tutorial repository.

The original 2025/2026 workshop repositories and older Jupyter Book repository
were consulted for context; their notebooks and data were not copied. The small
fixture is authored directly in this repository. The main SPINE repository was
not modified. The initial exploration used an older release, then the lesson was
updated and rerun against 1.4.0 following the maintainer's correction. Basic pip
installation is not a capability unique to that older release.

The four-section lesson, **From points to particles to interactions**, teaches
object inspection, coordinate units, SPINE class labels versus PDG codes,
interaction aggregation, valid primary topology, and an explicit primary-muon
selection. Two synthetic point sequences instantiate real SPINE classes. Labels
are assigned, not inferred; no detector data, weights, or calibration is implied.

One Markdown file produces an executed `.ipynb`, a downloadable copy, and a
staged MyST site notebook. All duplicates are generated under `_build/` and
ignored by Git. The website staging step adds per-section iframe players,
transcripts, and ordinary Continue links. The exported notebook stays complete
without narration or site-specific directives. There is no live website kernel.

## Execution evidence

All five code cells ran under SPINE 1.4.0. The outputs include:

| Check | Observed result |
| --- | --- |
| Imported package | SPINE 1.4.0 |
| First candidate | Muon, class index 2, 6 points, units cm |
| Constituent IDs | `[0, 1]` |
| Initial primary IDs | `[0, 1]` |
| Initial primary topology | `1mu1p` |
| Valid primary muon selection | 1 candidate |
| Remove proton primary flag | 2 particles, 1 primary, topology `1mu` |
| Aggregated point count | 10, unchanged by the primary flag experiment |

Assertions check the relevant counts, disjoint point indices, and unchanged
geometry count. The generated figure was visually inspected: the two point
groups, labels, coordinate units, and synthetic-data caption are legible.

## Narration, pronunciation, and cache

The YAML contains a tutorial slug, `review_status`, and a list of chunks with
stable `id`, `section`, and `text` fields. Four instructor-style drafts add
prompts and interpretation rather than reading the visible prose verbatim.
The user explicitly approved drafting them for review. The build contains no
LLM narration generation or rewriting step.

Pronunciation overrides cover SPINE, LArTPC, DUNE, ICARUS, UResNet, Graph-SPICE,
MinkowskiEngine, HDF5, and dE/dx. Matching is deterministic, case-sensitive,
longest-first, nonrecursive, and bounded to avoid replacing substrings of longer
words. These are **provisional overrides**, not confirmed corrections to observed
mispronunciations. All nine terms appear in a separate generated listening sample.

Hashes include normalized and expanded text, the relevant dictionary entries,
all synthesis configuration, and the build/backend recipe. Unused dictionary
entries do not invalidate unrelated chunks. Full hashes appear in filenames and
the manifest; checksums detect corrupt artifacts. Missing/corrupt audio rebuilds.
Both audio and manifest are installed atomically. Tutorial prose changes do not
trigger speech synthesis; section-to-narration staleness remains a manual review.

The cache test sequence runs with fake synthesis in ordinary unit tests and with
actual Kokoro in the separate benchmark. Twenty-two unit tests pass, covering
YAML and section errors, duplicate IDs/keys, substitutions, deterministic hashes,
configuration changes, missing/corrupt files, atomic failure, selective rebuilds,
and notebook conversion. The site build separately exercises real notebook code.

## Kokoro and Docker

Kokoro 0.9.4 runs on CPU PyTorch 2.6.0 in a Python 3.12 Debian image, with four
PyTorch threads. Configuration uses `hexgrad/Kokoro-82M`, immutable revision
`f3ff3571791e39611d31c381e3a41a3af07b4987`, voice `af_heart`, American English,
and speed 1.0. WAV output is mono 24 kHz, 16-bit PCM.

Model/config/voice files are downloaded only at runtime into a mounted cache.
No Kokoro weights are baked into the image or committed. Image building is a
separate explicit command. The image includes the small English spaCy pipeline
so synthesis does not need an unplanned language-model installation.

## Measured performance and audio checks

Measurements are local Docker Desktop **Linux aarch64**, CPU inference with four
threads, not GitHub-hosted runner measurements. Exact host CPU was unavailable
through the sandbox. They are observations from individual runs, not benchmarks
with statistical error bars. Docker startup is excluded from the Python build
timings below.

| Measurement | Observed |
| --- | --- |
| Docker image reported size | 1,742,013,032 bytes, approximately 1.62 GiB |
| Kokoro weight payload | approximately 312 MiB |
| Selected voice payload | approximately 511 KiB |
| Config payload | approximately 2.3 KiB |
| Initial 4-chunk build, including model downloads/startup | 88.936 s |
| Fresh audio build with model files already cached | 33.678 s, 4 generated |
| Identical second build | 0.020 s, 0 generated |
| One chunk text edit | 9.064 s, exactly 1 generated |
| One used pronunciation edit | 9.200 s, exactly 1 generated |
| Orientation chunk | 24.5 s speech; 11.612 s first-chunk synthesis including backend startup in warm-download benchmark |
| Full final lesson audio | 91.25 s |
| Terminology sample | 18.825 s speech; 8.836 s final build |

The four final chunk durations are 24.5, 20.85, 22.025, and 23.875 seconds.
Together the final tutorial WAVs occupy about 4.18 MiB. The first chunk is close
to the requested approximately 30-second performance probe; a separate exactly
30-second sample was not generated. Detailed benchmark JSON and waveform checks
are preserved locally under `_build/`.

Every sample is non-silent, decodes as the expected PCM format, and has zero
clipped samples in a full waveform scan. This does **not** establish intelligibility,
prosody, or correct terminology. Audio listening was not available through the
session's tools. No term is falsely reported as audibly correct or mispronounced.
The next review should play the terminology sample and all four lesson chunks,
then adjust the dictionary or narration and rerun the incremental build.

## Website, guided flow, CI, and deployment

`make site` builds two pages with a sidebar, executed code and plot, four narration
players, transcripts, a notebook download, and three Continue links to the next
conceptual section. No custom JavaScript, autoplay, or execution gate is used.
The source lesson remains complete when audio is absent. A publishable build uses
`--require-audio` to prevent deploying incomplete/stale audio.

`verify_site.py` inspects the generated HTML: section/Continue targets, four player
paths, referenced WAV files, the downloaded notebook's executed cells, its SPINE
version, and its figure. Both root hosting and the `/spine-learn` Pages prefix are
checked. Browser visual/interaction QA could not be completed: no connected
browser was available and native computer-use permissions were not granted.
The iframe layout is therefore not claimed to have passed browser visual review.

PR CI is cheap: install, unit tests, narration validation, real notebook execution,
strict MyST build, static-artifact checks, and upload a preview. It does not run
speech inference. The narrated workflow builds Docker, restores caches,
synthesizes changed chunks, checks a complete narrated site, and uploads it.
Main pushes deploy to Pages; manual runs deploy only from main with `deploy`
selected. GitHub Pages must use Actions as its publishing source.

No commit, push, remote Pages setting change, or live deployment was performed.
The configured expected URL is `https://deeplearnphysics.github.io/spine-learn/`;
it is not presented as an already-deployed deliverable. GitHub-hosted x86 CPU
runtime, cache behavior, and deployment still need a first workflow run.

## Licensing, compromises, and next steps

Upstream declares the Kokoro package and weights Apache-2.0. The voice is supplied
in the same model repository; no separate per-voice license was identified.
Weights and voices stay outside the image. spaCy's selected English pipeline is
MIT; eSpeak NG is GPLv3, so a future published image needs the corresponding
license/source-distribution review. See the linked primary sources and explicit
asset choices in [tts/README.md](tts/README.md).

Compromises: direct dependencies and model revision are pinned, but transitive
packages and the upstream MyST theme are not fully locked. The small staging
script currently targets one lesson. WAV is larger than compressed speech.
Old hash-named audio is retained; concurrent writers are unsupported. Cache status
does not detect pedagogical staleness. Continue uses simple links. The notebook
teaches the data interface with constructed objects rather than a real HDF5 file.

Recommended next pass: expert lesson/narration review and audible terminology QA;
visual testing on desktop/mobile; a first GitHub workflow/deployment run; fuller
dependency/theme locking; narration review tracking from section changes; then a
small real-output lesson. Chatterbox, consented voice cloning, phonetic control,
languages, browser exercises, Binder/JupyterHub, release-aligned curricula, and
extraction for other scientific projects remain future extensions.

## Python readability follow-up

The Python implementation, scripts, tests, and tutorial code cells were cleaned
up after the initial pass. Functions now have docstrings; core records and
interfaces have explicit types; longer validation/build routines are split into
named steps; and static landing-page/CSS content lives outside Python code.
`requirements-dev.txt`, Ruff/Pyright configuration, VS Code settings, and CI lint
checks provide a reproducible editing workflow. `make lint` checks source lint,
formatting, type diagnostics, and the canonical tutorial's code cells. The original
22 unit tests remain the regression suite. Source changes conservatively invalidate
narration recipe hashes, so the derived speech is refreshed after this refactor.

## Repository naming follow-up

On 2026-10-07 the GitHub repository and local checkout were renamed from
`spine-tuto` to `spine-learn`. The local `origin`, Python module (`spine_learn`),
Docker image name, documentation links, and expected GitHub Pages path were
updated together. The existing uncommitted implementation remains local.

## Prototype publication preparation

The initial source snapshot is being published as the baseline for a more realistic
curriculum. Local lint, type checks, all 22 unit tests, notebook execution, real
Docker/Kokoro synthesis, and narrated static-site artifact checks passed during
development. Subsequent browser checks used a temporary isolated profile and
captured only the tutorial page. They covered the header at desktop/phone widths
and the speed controls, download links, and narration-frame sizing.

The landing page is titled **About SPINE Learn** in navigation and metadata. Its
visible opening is the branded banner. Playback speed options and download links
are displayed inside each narration panel, with a small script that updates speed
and fits the frame to its content. No native popup menu is needed for these options.

Generated files and model caches are ignored. Both validation and narrated-site
workflows run on pushes to main; the narrated build deploys through GitHub Pages.
Workflow run outcomes should be checked in the repository's Actions tab.
