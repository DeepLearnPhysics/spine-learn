# SPINE Learn

SPINE Learn is a learning resource for particle reconstruction and analysis:
executable tutorials, guided narration, interactive event displays, and a
lesson-aware AI companion.

**[Open SPINE Learn](https://spine-learn.slac.stanford.edu/)** ·
[Start the first lesson](https://spine-learn.slac.stanford.edu/lesson) ·
[Deployment guide](k8s/README.md)

The initial collection contains one complete lesson, **From points to particles
to interactions**. It establishes a repeatable approach for a broader curriculum:
authored explanations and code produce both the website and runnable notebooks;
continuous integration executes the examples; version-controlled narration and
pronunciation settings keep audio maintainable alongside the written material.

Workshops and recorded lectures are valuable, but copying notebooks into a new
repository each year makes fixes hard to propagate. SPINE Learn keeps the material
in one shared source so improvements can carry forward as the software evolves.
The next priority is to expand the lesson collection and evaluate how well the
combined written, spoken, and interactive material supports learners.

The longer-term direction is **SciLoom**, a proposed reusable toolkit extracted
from this work so other scientific-software communities can maintain their own
executable, narrated, and optionally AI-assisted tutorials. SPINE Learn will remain
the reference implementation and a maintained learning resource for SPINE users.
The reusable toolkit is planned work; this repository currently implements the
SPINE-specific learning experience.

The lesson uses **SPINE 1.4.1**, installed from PyPI with
`pip install "spine[viz]==1.4.1"`. It reads existing reconstruction output and
requires no neural-network runtime or GPU.

## Questions, problems, and suggestions

On tutorial pages, the **Feedback** menu beside the notebook download stays
available while scrolling. Choose a problem report or suggestion; the current
lesson is prefilled in the GitHub form, which opens in a new tab.

Use [SPINE Learn issues](https://github.com/DeepLearnPhysics/spine-learn/issues)
for code that does not run, unclear or incorrect explanations, website problems,
and requests for new tutorials or SPINE functionality to cover.
[Report a problem](https://github.com/DeepLearnPhysics/spine-learn/issues/new?template=problem.yml) or [suggest an improvement](https://github.com/DeepLearnPhysics/spine-learn/issues/new?template=suggestion.yml) using the corresponding form. Search existing issues first; adding details to
an existing report helps keep the discussion together. A GitHub account is needed
to submit an issue.

For execution problems, include the lesson and cell, relevant error output, and
what you know about your Python/SPINE versions and installation. Reports are
public: remove API keys, credentials, and private data. If you are unsure whether
a problem belongs to SPINE or the lesson, report it here; maintainers can help
identify the right place for a fix.

The lesson companion can help explain the material, but chatting with it does not
file an issue or notify maintainers. Use an issue when you want a problem or
suggestion tracked. Maintainers can watch this repository's Issues notifications
in GitHub to receive reports without a separate support inbox or Slack channel.

## Start locally

Use Python 3.12 and Docker (Docker is needed only for speech synthesis).
The requirements include a Node 24 binary for MyST, so no global Node install is
needed. Installation, the initial site-theme fetch, and initial model downloads
need internet access. Subsequent speech synthesis uses local cached model files.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
make test narration-check
make notebook              # export AND execute all six cells
make site                  # execute, render; audio is optional
make serve                 # http://localhost:8000
```

To add narration:

```bash
make tts-image             # build once; repeat after editing tts/ dependencies
mkdir -p .cache/kokoro
make narration             # five semantic chunks, local CPU Kokoro
make narration             # unchanged chunks are skipped before loading Kokoro
make narration-status
make site                  # incorporates current audio and transcripts
make serve
```

Narration is maintained as version-controlled text and synthesized locally.
Its authoring used AI assistance with maintainer review; no LLM rewrites the
scripts during builds. Review the corresponding narration whenever a lesson
changes. Editorial metadata does not change the speech or force a rebuild.

## Try the embedded lesson companion locally

The lesson includes a floating **Ask SPINE** panel, available on the S3DF-hosted
website and in the local preview. It explains the canonical lesson using Gemini,
offers hints, and supports follow-up questions. It cannot run code or inspect
local notebooks. The runnable notebook remains independent of the chat.

```bash
make site
make tutor-key              # hidden prompt; paste a free-tier Gemini API key
make tutor                  # http://127.0.0.1:8002/lesson
```

Create your key in [Google AI Studio](https://aistudio.google.com/api-keys), using
a project with the quota and billing settings you intend to use.
The code does not enable or upgrade billing; a key from a paid project is still
billed according to that project's settings. The default model is
`gemini-3.1-flash-lite`; select another model available to your project with
`GEMINI_MODEL=model-name make tutor` if needed. Opening the panel only
checks whether a key is configured. **Check connection**
sends a real test request to verify model access and consumes API quota.

`make tutor-key` saves the key in `.gemini-api-key` with owner-only permissions.
The file is Git-ignored and outside the served directory. An existing
`GEMINI_API_KEY` environment variable takes precedence. You can add or replace the
key while the server runs, then click **Check connection**; no rebuild or restart
is required. Do not place keys in lesson sources, browser code, or GitHub Pages.

Open **Ask SPINE** in the lower-right corner of the lesson. The panel stays
accessible while scrolling; minimize it or press Escape to return to reading
without losing the conversation. Press **Enter** to send or **Shift+Enter** for a new line. The arrow button also
sends your question; **New conversation** is at the top of the panel.
Answers render Markdown, including code blocks,
lists, and tables. Try a suggested question, ask a follow-up, and use **New
conversation** to clear it. Chat history stays in memory in the current browser
tab and disappears on reload. Each request sends the lesson source, question,
and up to six recent exchanges (at most 24,000 history characters) to Google.
The server does not save prompts or responses. Google's own data handling terms
apply; use public lesson material rather than confidential research data.

The backend accepts one request at a time, at most six per minute and 200
per UTC day **per process**. Restarting resets these local counters. These limits
are separate from Google's account/model quotas, not a guarantee of free-tier
capacity. An explicit transient HTTP error (500, 502, 503, or 504) is retried
once after one second, using the remaining 45-second provider timeout budget.
Both attempts count toward the local limits. Quota, authentication, network
timeout, and malformed-response failures are not retried automatically. The
pending indicator stays visible during the request; failed questions remain
available to retry manually. Output is capped at 2,048 tokens. API responses include token usage for
inspection in browser developer tools; no extra logging infrastructure is needed.

`scripts/serve_tutor.py` serves both static pages and `/api/tutor/*` on loopback
port 8002. It rejects foreign Host/Origin headers and bounds request sizes. It
uses Python's standard library, so there are no new runtime dependencies.
The existing `make serve` remains a static preview; its chat displays setup help.
The S3DF deployment serves the site and chat API together using Flask and Gunicorn.
GitHub Pages hosts a static edition; its chat panel directs learners to the full
site. Tests mock provider responses and never spend API quota. Evaluating answer
quality with representative learner questions remains an ongoing editorial task;
a successful API response alone does not establish teaching quality.

## The first lesson

**From points to particles to interactions** is a 20-minute introduction to
`RecoParticle`, `RecoInteraction`, class labels, units, primary flags, topology,
and an explicit candidate selection. Four sections contain six executed code
cells, assertions, a figure, predictions, and exercises.

The notebook reads a 1.6 MB generic-simulation sample from public S3DF storage,
checks its SHA-256, and restores stored particle/interaction associations with
SPINE 1.4.1. Entry 0 provides 2,228 points, nine particles, and three interactions.
The sample was written by SPINE 0.9.5; this is recorded provenance, not the version
learners must install. No model inference is run in the lesson. Reconstructed
labels are distinguished from simulation truth. See `data/README.md` for the
source, checksum, and update procedure.

The first section uses guided narration: `orientation` introduces a
prediction, highlights `orientation-activity` when playback ends, and waits for
an explicit learner action before playing `orientation-explanation`. That clip
highlights the next section on completion but does not start another recording.
Scrolling is opt-in, keyboard focus is never moved automatically, and the same
activity and explanation are available in writing. Later sections use shorter
spoken guidance. Additional guided exercises can build on the same navigation
and playback controls.

Narration YAML can set `focus`, `next_step`, `next_chunk`, and `continue_label`.
Anchors and clip references are validated at build time. Changing only these
navigation fields does not regenerate speech. Browser playback errors retain
Play controls and downloadable transcripts as fallbacks.

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
links. Website and download copies live in `_build/`; nobody edits them by hand.
The website has no live kernel. Use **Open in Colab** to run and edit the lesson
in a Google-hosted notebook, or download it for local use. Colab requires a Google
account; its temporary CPU runtime is sufficient for this lesson.

`make colab` regenerates `notebooks/01_points_particles_interactions.ipynb` from
the canonical Markdown with a dependency-installation cell and Colab's Plotly
renderer. Commit this generated export when the lesson changes; tests reject a
stale export. It contains no outputs and is not edited by hand. The button opens
the export on `main`, so changes become available after merging/pushing to GitHub.

The choice is the current MyST CLI rather than a new Sphinx/Jupyter Book 1
configuration. MyST supplies navigation, notebook rendering, static export, and
GitHub Pages support. Jupytext and nbclient make notebook export and CI execution
explicit. This adds a small staging script, but keeps one source and one execution
path for both website outputs and the downloadable notebook.

Audio players use tiny same-origin HTML iframes because MyST supports them
natively. Each compact toolbar has an expandable settings panel with matching
buttons for speed, optional step-following, and audio/transcript downloads.
Transcripts are UTF-8 text files; the lesson's written explanations remain visible.
Editorial review status stays in source metadata, not in the learner-facing UI.
One continuous orange gutter line spans the active step, including code and outputs.
A matching accent identifies the controlling audio player.
Continue links use ordinary anchors and do not verify execution or hide content.
A small local script fits each iframe to its controls, including expanded settings. Serve the HTML over HTTP; the site's routing
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
review_status: reviewed
chunks:
  - id: inspect-particles
    section: inspect-particles
    text: |
      Take a moment to look at the first particle before moving on.
      Its size counts indexed points; inspect its units too.
```

Set `review_status` to `reviewed` only after a maintainer has reviewed the script.
Map `section` to a stable `(inspect-particles)=` anchor in the tutorial. Use
semantic chunks of a few sentences, not one file per sentence. Narration should
add pacing and instructor context. Keep essential explanations and exercises in
the visible lesson. Validation rejects missing sections, duplicate chunk IDs,
duplicate YAML keys, unsafe IDs, malformed text, and invalid configuration.

`narration/pronunciations.yaml` changes spoken text only. Matching is
case-sensitive, longest-first, bounded by non-word characters, and nonrecursive.
For example, `HDF5` uses a connected phonetic pronunciation; it will not match
`HDF50`. The dictionary supports spelling replacements and Kokoro/Misaki phonetic
annotations. These affect speech only; written transcripts retain the original
technical terms.

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
| `tutorials/` | Canonical MyST lesson with sample download and analysis |
| `narration/` | Narration scripts, pronunciation dictionary, pinned voice/model config |
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
| `make notebook` | `_build/notebooks/01_points_particles_interactions.ipynb`, executed |
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
[SPINE Learn](https://www.deeplearnphysics.org/spine-learn/).

Except for the generated Colab export, notebooks, executed outputs, speech files, and model caches stay out of Git;
GitHub Actions rebuilds the publication from the authored sources.

## Current scope and development priorities

The complete reading, notebook, narration, visualization, feedback, and chat
workflow is available for the initial lesson. Expanding the curriculum is the
main development priority: additional reconstruction and analysis tasks, more
worked examples, and exercises at different levels of experience.

Further work includes learner evaluation, systematic review of AI answers,
richer instructor-style narration, and release-aligned maintenance across lessons.
The build currently stages one lesson; adding a collection also requires
extending lesson discovery, navigation, and per-lesson companion context.

Operational limits are explicit: chat does not execute notebooks, its quotas
are process-local, and the single-replica deployment briefly interrupts service
during updates. See the [deployment guide](k8s/README.md) for details. Direct
Python dependencies, SPINE, and the speech model revision are pinned; transitive
packages and the upstream MyST theme can still evolve. Offline builds require
previously downloaded dependencies and assets.

See [TTS notes](tts/README.md) for synthesis dependencies and licensing sources.
The [historical implementation report](FIRST_PASS_REPORT.md) records early
measurements and decisions; it does not describe the current release status.

## Website colors

`site_assets/style.css` defines the canonical SPINE logo orange once as
`--spine-orange: #EB7913`. MyST theme tokens and narration players share that
source. Pale backgrounds and darker text colors are derived from it; the darker
orange keeps small links readable on white. Run `make site` and refresh the
preview after editing the stylesheet.

## S3DF hosting and automated releases

The production serving layer, public HTTPRoute, and manual rollout/update
instructions are documented in [k8s/README.md](k8s/README.md). GitHub Actions
publishes a tested application image and a digest-pinned deployment bundle;
cluster access and the Gemini Secret remain on S3DF.

The intended automation is **Argo CD provisioned by the S3DF platform team** in
the existing vcluster. Application configuration and release-source integration
are pending; deployments currently use the manual update procedure. The local
`make tutor` preview remains available independently.

## License

Original code, tutorial text and examples, narration scripts, and documentation
in this repository are available under the [MIT License](LICENSE), matching
[SPINE's license](https://github.com/DeepLearnPhysics/spine/blob/main/LICENSE).
Generated notebooks carry the same terms for the original material they contain.

Third-party material retains its own licenses and notices:

- SPINE branding retains its [upstream MIT license](site_assets/brand/LICENSE)
  and [provenance](site_assets/brand/README.md).
- Vendored browser libraries retain the notices for
  [Marked](site_assets/tutor/vendor/marked-LICENSE.txt) and
  [DOMPurify](site_assets/tutor/vendor/dompurify-LICENSE.txt).
- Speech dependencies and model assets are documented in the
  [TTS licensing notes](tts/README.md#licenses-and-asset-distribution).
- The externally hosted sample dataset is documented in
  [data provenance](data/README.md); this repository's license does not relicense
  that dataset or other external dependencies.
