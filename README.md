# SPINE Learn

An executable, narrated lesson that can evolve with the software it teaches.
This first prototype targets **SPINE 1.4.0**, installed directly from PyPI with
`pip install spine==1.4.0`. Most basic SPINE work needs only a normal pip
installation; the lesson does not need a neural-network runtime or GPU.

Workshops and recorded lectures are valuable, but copying notebooks into a new
repository each year makes fixes hard to propagate. Here, a small teaching unit
has one diffable source, executable checks, and separately editable narration.
The immediate scope is one complete lesson, not a course platform.

## Start locally

Use Python 3.12 and Docker (Docker is needed only for speech synthesis).
The requirements include a Node 24 binary for MyST, so no global Node install is
needed. Installation, the initial site-theme fetch, and initial model downloads
need internet access. Subsequent speech synthesis uses local cached model files.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
make test narration-check
make notebook              # export AND execute all five cells
make site                  # execute, render; audio is optional
make serve                 # http://localhost:8000
```

To add narration:

```bash
make tts-image             # build once; repeat after editing tts/ dependencies
mkdir -p .cache/kokoro
make narration             # four semantic chunks, local CPU Kokoro
make narration             # unchanged chunks are skipped before loading Kokoro
make narration-status
make site                  # incorporates current audio and transcripts
make serve
```

The initial narration is **AI-assisted draft text for expert review**, created
with the maintainer's explicit approval. Edit it directly; no LLM runs in the
build pipeline. Set `review_status: reviewed` after your review. That label does
not change the synthesized speech or force a rebuild.

## The first lesson

**From points to particles to interactions** is a 20-minute introduction to
`RecoParticle`, `RecoInteraction`, class labels, units, primary flags, topology,
and an explicit candidate selection. Four sections contain five executed code
cells, assertions, a figure, predictions, and exercises.

The notebook constructs two short point groups using the real SPINE classes.
Everything in this fixture is synthetic and defined in the notebook: no
experiment data, model inference, detector simulation, calibration, or physics
performance claim. SPINE's class indices are kept distinct from PDG codes.

## One source, several artifacts

```text
tutorials/01_reconstruction_basics.md
    → Jupytext → nbclient execution → downloadable .ipynb
                                → generated MyST site notebook → static HTML

narration/*.yaml + pronunciations + synthesis configuration
    → validated section mapping → content hashes → Docker/Kokoro → WAV + manifest
                                                               → website players
```

MyST Markdown is authoritative. `make notebook` translates section anchors into
standard HTML anchors that also work in Jupyter Markdown. The executed notebook
is staged for MyST's `book-theme` with optional players, transcripts, and Continue
links. Generated copies live only in `_build/`; nobody edits or synchronizes them.
The website has no live kernel. Download the notebook to run or change the code.

The choice is the current MyST CLI rather than a new Sphinx/Jupyter Book 1
configuration. MyST supplies navigation, notebook rendering, static export, and
GitHub Pages support. Jupytext and nbclient make notebook export and CI execution
explicit. This adds a small staging script, but keeps one source and one execution
path for both website outputs and the downloadable notebook.

Audio players use tiny same-origin HTML iframes because MyST supports them
natively. Transcripts stay in the main accessible document. Continue links use
ordinary anchors and do not verify execution, autoplay, or hide lesson content.
A small local script handles playback speed choices and fits each player to its
controls. Speed buttons and an audio download link stay visible, avoiding native
popup menus clipped by iframe boundaries. Serve the HTML over HTTP; the site's routing
and assets are not intended for `file://` viewing.

## Python development and VS Code

Use the same environment for the command line and editor:

```bash
.venv/bin/pip install -r requirements-dev.txt
make lint                   # Ruff, formatting, Pyright, and tutorial code cells
make test
make format                 # fix lint issues and format Python files
```

The workspace recommends the Python, Pylance, and Ruff extensions and defaults to
`.venv/bin/python`. If VS Code already remembered a different environment, use
**Python: Select Interpreter** and select this repository's `.venv/bin/python`.
The default interpreter setting does not override a previously selected one.
Ruff formats Python on save; Pylance uses the same basic type-checking settings
as the Pyright CLI. CI runs `make lint` before the tests and website build.

Python code uses descriptive names, type annotations, NumPy-style docstrings,
and short comments for non-obvious steps. Ruff checks imports, unused names,
common mistakes, docstrings, and an 88-character line limit. The Python cells in
the canonical MyST lesson are linted together (they share a kernel namespace)
and checked for formatting individually. Their surrounding prose supplies the
module documentation. Generated files, caches, and virtual environments are
excluded from the source checks.

TTS dependencies remain isolated in Docker. The Kokoro adapter loads its optional
packages only when instantiated; the editor and site environment do not need a
second installation of Torch or Kokoro just to inspect the code.

## Authoring narration

```yaml
tutorial: reconstruction-basics
review_status: draft
chunks:
  - id: inspect-particles
    section: inspect-particles
    text: |
      Take a moment to look at the first particle before moving on.
      Its size counts indexed points; inspect its units too.
```

Map `section` to a stable `(inspect-particles)=` anchor in the tutorial. Use
semantic chunks of a few sentences, not one file per sentence. Narration should
add pacing and instructor context. Keep essential explanations and exercises in
the visible lesson. Validation rejects missing sections, duplicate chunk IDs,
duplicate YAML keys, unsafe IDs, malformed text, and invalid configuration.

`narration/pronunciations.yaml` changes spoken text only. Matching is
case-sensitive, longest-first, bounded by non-word characters, and nonrecursive.
For example, `HDF5` becomes `H D F five`; it will not match `HDF50`.
Plain spelling expansions are intentionally simple; phonetic/SSML controls and
context-sensitive pronunciation are not implemented.

A chunk's SHA-256 includes whitespace-normalized original text, expanded text,
**the dictionary entries actually used**, backend, immutable model revision,
voice, language, speed, sample rate, tool version, backend code and Docker recipe.
The relevant dictionary projection lets an HDF5 change rebuild only the section
that uses it. New matches change the expanded text too. Unused dictionary entries
do not invalidate audio. The manifest records full hashes, filenames, section IDs,
and audio checksums. Missing or corrupted files are rebuilt. Audio and manifest
writes are atomic; concurrent builds into one output directory are not supported.

Visible-prose edits do **not** regenerate speech. Maintainers must review the
mapped narration when changing a section. `narration-status` reports audio cache
freshness, not pedagogical staleness relative to the tutorial.

## Files and commands

| Location | Purpose |
| --- | --- |
| `tutorials/` | Canonical MyST lesson, including the entire synthetic fixture |
| `narration/` | Draft scripts, pronunciation dictionary, pinned voice/model config |
| `spine_learn/build.py` | Export, execution, staging, and static-site build |
| `spine_learn/narration.py` | Validation, hashing, cache, status, and CLI |
| `spine_learn/kokoro_backend.py` | Lazy CPU Kokoro adapter |
| `tts/` | Isolated synthesis environment and licensing notes |
| `requirements-dev.txt` | Pinned lint/type-check tools and YAML type stubs |
| `.vscode/` | Shared interpreter, formatter, and extension recommendations |
| `site_assets/` | Website CSS kept separate from Python build logic |
| `tests/` | Fast tests with fake synthesis; no model downloads |
| `scripts/benchmark_narration.py` | Opt-in real CPU incremental-build benchmark |
| `.github/workflows/` | PR validation, narrated artifact, and Pages deployment |
| `_build/` | Ignored notebooks, site, audio, manifests, and benchmark output |
| `.cache/kokoro/` | Ignored runtime model/voice download cache |

| Command | Result |
| --- | --- |
| `make notebook` | `_build/notebooks/reconstruction-basics.ipynb`, executed |
| `make site` | `_build/site/_build/html/`, includes available current audio |
| `make serve` | Local preview on port 8000 |
| `make lint` | Ruff lint/format, Pyright, and tutorial cell checks |
| `make format` | Automatic Python lint fixes and formatting |
| `make test` | Unit tests; no actual speech inference |
| `make narration-check` | YAML, configuration, and section validation |
| `make narration-status` | Per-chunk audio freshness |
| `make tts-image` | Build CPU TTS image; never implicit in `make narration` |
| `make narration` | Incremental tutorial speech synthesis |
| `make terminology` | Separate sample exercising all nine technical terms |
| `make benchmark` | Real first/cached/edit/pronunciation benchmark; fresh output required |

Use `PYTHON=/path/to/python make ...` to select a different Python. A publishable
build can require every audio file:

```bash
export PATH="$PWD/.venv/bin:$PATH"
.venv/bin/python -m spine_learn.build site --require-audio
```

## CI and publication

PRs and main pushes run lint/type checks and tests, validate narration,
execute the lesson, and build the strict static site. The preview artifact is usable without audio and displays
an explicit audio-unavailable message and the transcript. Cheap CI never runs TTS.

A separate narrated-site workflow runs on main pushes or manual dispatch. It
builds the Docker image, restores a cache of model files and generated audio,
synthesizes changed chunks, requires complete audio, and uploads the narrated
site. Main pushes deploy it to Pages. A manual run deploys only on main when its
`deploy` input is selected. Jobs have separate read and deployment permissions.

GitHub Pages uses **GitHub Actions** as its publishing source. To configure a
fork, select **Settings → Pages → Build and deployment → GitHub Actions**. The workflow sets `BASE_URL=/<repository-name>` for project-site
paths, including iframe players. Publication target:
[SPINE Learn](https://deeplearnphysics.github.io/spine-learn/).

The initial prototype is the baseline for a more realistic lesson. Generated
notebooks, executed outputs, speech files, and model caches stay out of Git;
GitHub Actions rebuilds the publication from the authored sources.

## Limitations and next pass

See [the first-pass report](FIRST_PASS_REPORT.md) for measured execution and audio
results, and [TTS notes](tts/README.md) for dependencies and licensing sources.

Expert review of the draft narration and an audible terminology check are still
needed. The header and narration controls were checked in an isolated browser at desktop
and phone widths. This inspection captures only the tutorial page, not the desktop.
The build pins direct Python dependencies, SPINE, and model revision; transitive
packages and the upstream MyST theme can still evolve. WAV is deliberately simple
but larger than compressed delivery audio. Cache files are not automatically
pruned. Offline operation requires previously downloaded dependencies and theme.
The helpers currently target one tutorial rather than pretending to be a framework.

Next: review the lesson and voice, track section changes
for narration review, and add a small real-output reading lesson. Later options
include Chatterbox, consented instructor voice cloning, richer phonetics and
languages, optional guided progress, browser exercises, Binder/JupyterHub launch,
release-aligned course versions, and reuse beyond SPINE. None needs to complicate
this first lesson's authoring workflow.

## Website colors

`site_assets/style.css` defines the canonical SPINE logo orange once as
`--spine-orange: #EB7913`. MyST theme tokens and narration players share that
source. Pale backgrounds and darker text colors are derived from it; the darker
orange keeps small links readable on white. Run `make site` and refresh the
preview after editing the stylesheet.
