"""Export the canonical lesson, execute its cells, and stage a MyST website.

The downloadable notebook remains independent of the website. Narration players
and navigation are added only to a generated copy used by the MyST renderer.
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import zipfile
from copy import deepcopy
from pathlib import Path

import jupytext
import nbformat
import yaml
from nbclient import NotebookClient
from nbformat import NotebookNode

from .models import NarrationChunk, NarrationDocument
from .narration import ROOT, SOURCE, current_audio, load_inputs

BUILD = ROOT / "_build"
NOTEBOOK_PATH = BUILD / "notebooks/01_points_particles_interactions.ipynb"
COLAB_PATH = ROOT / "notebooks/01_points_particles_interactions.ipynb"
COLAB_URL = (
    "https://colab.research.google.com/github/DeepLearnPhysics/spine-learn/"
    "blob/main/notebooks/01_points_particles_interactions.ipynb"
)


def colab_notebook() -> NotebookNode:
    """Generate the published Colab export from the authoritative lesson.

    Keep outputs out of Git and use deterministic cell IDs so regeneration
    produces a reviewable diff. The ordinary download remains unchanged.
    """
    notebook = jupytext.read(SOURCE)
    notebook.metadata = {"kernelspec": notebook.metadata.kernelspec}
    introduction = nbformat.v4.new_markdown_cell(
        "## Run this lesson in Colab\n\n"
        "Sign in to Google, connect to a CPU runtime, then run the cells in order. "
        "Run the setup cell below first; it installs the lesson dependencies. "
        "You can edit every example. Save a copy in Drive to keep your changes.\n\n"
        "Return to [SPINE Learn](https://spine-learn.slac.stanford.edu/lesson) "
        "for narration and Ask SPINE. Colab sessions are temporary; after a "
        "runtime reset, rerun setup and the lesson cells."
    )
    setup = nbformat.v4.new_code_cell(
        "# Install the version used to validate this lesson.\n"
        '%pip install -q "spine[viz]==1.4.1"'
    )
    notebook.cells[1:1] = [introduction, setup]
    for index, cell in enumerate(notebook.cells):
        cell.id = f"lesson-{index:03d}"
        cell.metadata = {}
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
            # Colab renders Plotly through its own HTML output integration.
            cell.source = cell.source.replace(
                'renderer="plotly_mimetype"', 'renderer="colab"'
            )
        else:
            cell.source = re.sub(
                r"^\(([a-z0-9-]+)\)=$",
                r'<a id="\1"></a>',
                cell.source,
                flags=re.MULTILINE,
            )
    nbformat.validate(notebook)
    return notebook


def export_notebook(
    destination: Path | None = None, execute: bool = True
) -> NotebookNode:
    """Convert the MyST lesson into a standard Jupyter notebook.

    Parameters
    ----------
    destination
        Output filename. Defaults to the notebook download under ``_build``.
    execute
        Run every code cell before writing the notebook. Tests can disable
        execution when they only need to check the source conversion.

    Returns
    -------
    NotebookNode
        The converted notebook, including outputs when execution is enabled.
    """
    destination = destination or NOTEBOOK_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    notebook = jupytext.read(SOURCE)

    # Jupyter understands HTML anchors, but not MyST's section-label syntax.
    for cell in notebook.cells:
        if cell.cell_type == "markdown":
            cell.source = re.sub(
                r"^\(([a-z0-9-]+)\)=$",
                r'<a id="\1"></a>',
                cell.source,
                flags=re.MULTILINE,
            )

    if execute:
        client = NotebookClient(
            notebook,
            timeout=120,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT)}},
        )
        client.execute()

    nbformat.validate(notebook)
    nbformat.write(notebook, destination)
    print(f"Notebook: {destination}")
    return notebook


def player_html(chunk: NarrationChunk, audio: Path | None) -> str:
    """Render a small accessible audio player, or a clear missing-audio message."""
    label = html.escape(chunk["section"].replace("-", " "))
    focus = html.escape(chunk.get("focus", chunk["section"]), quote=True)

    def icon(path: str) -> str:
        """Keep control icons consistent and hidden from screen readers."""
        return (
            '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" '
            'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round"><path d="{path}"/></svg>'
        )

    play_icon = icon("M8 5v14l11-7z")
    next_icon = icon("M5 12h14m-6-6 6 6-6 6")
    settings_icon = icon("M4 7h16M4 17h16M9 4v6M15 14v6")
    download_icon = icon("M12 3v12m-5-5 5 5 5-5M5 17v4h14v-4")
    transcript_name = html.escape(
        f"spine-learn-{chunk['id']}-transcript.txt", quote=True
    )
    transcript_button = (
        f'<a class="setting-button" href="../downloads/{transcript_name}" '
        f'download="{transcript_name}" title="Download transcript (.txt)">'
        f"{download_icon}<span>Transcript</span></a>"
    )
    guidance_attributes = ""
    continuation = ""
    scroll_option = ""
    if "next_step" in chunk:
        guidance_attributes = " ".join(
            f'data-{key.replace("_", "-")}="'
            f'{html.escape(chunk.get(key, ""), quote=True)}"'
            for key in ("focus", "next_step", "next_chunk")
        )
        button_label = html.escape(chunk.get("continue_label", "Continue"), quote=True)
        continuation = (
            '<button type="button" class="icon-button continue-narration" '
            f'title="{button_label}" aria-label="{button_label}">{next_icon}</button>'
        )
        scroll_option = (
            '<button type="button" class="setting-button follow-scroll" '
            'aria-pressed="false" title="Scroll to the active step">'
            "Follow step</button>"
        )

    if audio is None:
        control = "<p>Audio unavailable for this version.</p>" + transcript_button
    else:
        filename = html.escape(audio.name, quote=True)
        download_name = html.escape(f"spine-learn-{chunk['id']}.wav", quote=True)
        speed_buttons = []
        for speed in (0.75, 1.0, 1.25, 1.5, 2.0):
            selected = "true" if speed == 1 else "false"
            speed_buttons.append(
                f'<button type="button" class="setting-button" data-speed="{speed:g}" '
                f'aria-pressed="{selected}">{speed:g}×</button>'
            )
        choices = " ".join(speed_buttons)
        control = f"""
  <audio preload="metadata" aria-label="Narration: {label}" src="../audio/{filename}">
  </audio>
  <div class="audio-toolbar">
    <button type="button" class="icon-button toggle-play" title="Play narration"
            aria-label="Play narration">{play_icon}</button>
    <span class="audio-label">Listen</span>
    <input class="audio-progress" type="range" min="0" max="100" value="0"
           step="0.1" aria-label="Seek narration" disabled>
    <span class="audio-time" aria-hidden="true">0:00</span>
    {continuation}
    <button type="button" class="icon-button toggle-settings" title="Audio settings"
            aria-label="Audio settings" aria-expanded="false"
            aria-controls="audio-settings">{settings_icon}</button>
  </div>
  <div class="narration-options" id="audio-settings" hidden>
    <div class="narration-speeds" role="group" aria-label="Playback speed">
      <span>Speed</span> {choices}
    </div>
    {scroll_option}
    <a class="setting-button" href="../audio/{filename}" download="{download_name}"
       title="Download audio (.wav)">{download_icon}<span>Audio</span></a>
    {transcript_button}
  </div>
"""

    # Settings expand in the document flow so the iframe never clips a popup.
    guidance_class = "narration-guidance" if "next_step" in chunk else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Narration: {label}</title>
  <link rel="stylesheet" href="../style.css">
  <script src="../narration.js" defer></script>
</head>
<body class="narration-player" data-focus="{focus}"
      data-notebook="../downloads/{NOTEBOOK_PATH.name}"
      data-colab="{COLAB_URL}">
  <div class="{guidance_class}" {guidance_attributes}>
    {control}
    <p role="status" class="guidance-status visually-hidden"></p>
  </div>
</body>
</html>
"""


def _narration_directives(chunk: NarrationChunk, base_url: str) -> str:
    """Embed the compact player; transcripts are available as downloads."""
    player_url = f"{base_url}/players/{chunk['id']}.html"
    return (
        f"\n```{{iframe}} {player_url}\n"
        f":title: Narration for {chunk['section']}\n"
        ":width: 100%\n"
        "```\n\n"
    )


def _add_guided_sections(
    notebook: NotebookNode, document: NarrationDocument, base_url: str
) -> NotebookNode:
    """Add narration and Continue links without changing the downloadable copy."""
    website = deepcopy(notebook)
    website.metadata.pop("jupytext", None)
    website.metadata.update(
        {
            "downloads": [
                {
                    "url": f"{base_url}/downloads/{NOTEBOOK_PATH.name}",
                    "filename": NOTEBOOK_PATH.name,
                    "title": "Download lesson notebook (.ipynb)",
                }
            ],
            "exports": [],
        }
    )
    chunks = {chunk["section"]: chunk for chunk in document["chunks"]}
    previous_section: str | None = None

    for cell in website.cells:
        if cell.cell_type != "markdown":
            continue

        # Restore MyST labels so the website renderer can resolve section links.
        cell.source = re.sub(r'<a id="([a-z0-9-]+)"></a>', r"(\1)=", cell.source)
        for section, chunk in chunks.items():
            heading_pattern = rf"(\({re.escape(section)}\)=\n#{{2,3}} [^\n]+\n)"
            directives = _narration_directives(chunk, base_url)

            # Bind the current directives explicitly; each section has its own text.
            def append_narration(
                match: re.Match[str], content: str = directives
            ) -> str:
                """Keep the heading and follow it with this section's controls."""
                return match.group(1) + content

            cell.source = re.sub(heading_pattern, append_narration, cell.source)

        # Place Continue immediately before the next section, after any prose
        # that still belongs to the previous one in this Markdown cell.
        section_match = re.search(
            r"^\(([a-z0-9-]+)\)=\n(?=## )", cell.source, re.MULTILINE
        )
        if section_match and section_match[1] in chunks:
            section = section_match[1]
            if previous_section is not None:
                link = f"[Continue →](#{section})\n\n"
                cell.source = cell.source.replace(
                    section_match[0], link + section_match[0], 1
                )
            previous_section = section

    # Add lesson-specific website controls without a self-link in the download.
    companion = (
        f"\n```{{iframe}} {base_url}/tutor/index.html\n"
        ":title: SPINE Learn lesson companion\n"
        ":width: 100%\n"
        "```\n\n"
    )
    for cell in website.cells:
        if cell.cell_type == "markdown" and "(orientation)=" in cell.source:
            cell.source = cell.source.replace(
                "(orientation)=", companion + "(orientation)=", 1
            )
            break

    return website


def _write_site_configuration(site: Path) -> None:
    """Copy the landing page and styles, then write MyST's build configuration."""
    shutil.copy(ROOT / "tutorials/index.md", site / "index.md")
    shutil.copy(ROOT / "site_assets/style.css", site / "style.css")
    shutil.copy(ROOT / "site_assets/narration.js", site / "narration.js")
    shutil.copytree(ROOT / "site_assets/brand", site / "brand", dirs_exist_ok=True)
    shutil.copytree(ROOT / "site_assets/tutor", site / "tutor", dirs_exist_ok=True)

    configuration = {
        "version": 1,
        "project": {
            "title": "About SPINE Learn",
            "description": "Executable lessons with maintainable narration",
            "toc": [
                {"file": "index.md", "title": "About SPINE Learn"},
                {"file": "lesson.ipynb"},
            ],
            "static_files": [
                "tutor",
                "players",
                "audio",
                "downloads",
                "style.css",
                "narration.js",
            ],
        },
        "site": {
            "title": "SPINE Learn",
            "template": "book-theme",
            "options": {
                "logo": "brand/spine-logo-light.png",
                "logo_dark": "brand/spine-logo-light.png",
                "logo_alt": "SPINE",
                "favicon": "brand/favicon.ico",
                "logo_text": "Learn",
                "style": "style.css",
            },
        },
    }
    (site / "myst.yml").write_text(
        yaml.safe_dump(configuration, sort_keys=False), encoding="utf-8"
    )


def stage_site(notebook: NotebookNode, require_audio: bool = False) -> Path:
    """Assemble website inputs and return the directory MyST should build.

    Publication builds can require current audio for every narration chunk.
    Preview builds offer a transcript download and a message for missing audio.
    """
    document, configuration, dictionary = load_inputs()
    audio = current_audio(document, configuration, dictionary)
    if require_audio and len(audio) != len(document["chunks"]):
        raise ValueError(
            "Publication requires current audio for every chunk. "
            "Run make narration first."
        )

    site = BUILD / "site"
    site.mkdir(parents=True, exist_ok=True)

    # Clear only staged assets. Keep MyST's downloaded theme and build cache.
    for folder in ("players", "audio", "downloads"):
        path = site / folder
        if path.exists():
            shutil.rmtree(path)
        path.mkdir()
    shutil.copy(NOTEBOOK_PATH, site / "downloads")
    # The collection currently has one lesson; package the same portable export.
    with zipfile.ZipFile(
        site / "downloads/spine-learn-notebooks.zip", "w", zipfile.ZIP_DEFLATED
    ) as archive:
        archive.write(NOTEBOOK_PATH, NOTEBOOK_PATH.name)
        archive.writestr(
            "README.txt",
            'Install: pip install "spine[viz]"\n'
            "Open the notebook in Jupyter or VS Code and run cells in order.\n"
            "The sample is downloaded from public S3DF storage on first run.\n",
        )

    for chunk in document["chunks"]:
        # Plain UTF-8 text keeps each transcript portable and accessible offline.
        transcript_path = (
            site / "downloads" / f"spine-learn-{chunk['id']}-transcript.txt"
        )
        transcript_path.write_text(chunk["text"].strip() + "\n", encoding="utf-8")
        player_path = site / "players" / f"{chunk['id']}.html"
        player_path.write_text(
            player_html(chunk, audio.get(chunk["id"])),
            encoding="utf-8",
        )
        if chunk["id"] in audio:
            shutil.copy(audio[chunk["id"]], site / "audio")

    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    website = _add_guided_sections(notebook, document, base_url)
    nbformat.write(website, site / "lesson.ipynb")
    _write_site_configuration(site)
    return site


def main() -> None:
    """Run notebook export or the complete static-site build from the CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["notebook", "site", "colab"])
    parser.add_argument("--require-audio", action="store_true")
    arguments = parser.parse_args()

    try:
        if arguments.command == "colab":
            COLAB_PATH.parent.mkdir(parents=True, exist_ok=True)
            nbformat.write(colab_notebook(), COLAB_PATH)
            print(f"Colab notebook: {COLAB_PATH}")
            return
        notebook = export_notebook()
        if arguments.command == "site":
            site = stage_site(notebook, require_audio=arguments.require_audio)
            subprocess.run(
                ["myst", "build", "--html", "--strict"], cwd=site, check=True
            )
    except Exception as error:
        # This CLI boundary also catches errors raised by notebook execution.
        parser.exit(1, f"Build failed: {error}\n")


if __name__ == "__main__":
    main()
