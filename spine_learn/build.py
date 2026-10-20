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
NOTEBOOK_PATH = BUILD / "notebooks/reconstruction-basics.ipynb"


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


def player_html(chunk: NarrationChunk, audio: Path | None, review_status: str) -> str:
    """Render a small accessible audio player, or a clear missing-audio message."""
    label = html.escape(chunk["section"].replace("-", " "))
    review_label = html.escape(review_status.upper())

    if audio is None:
        control = (
            "<p>Audio has not been generated for this version. "
            "Read the transcript below.</p>"
        )
    else:
        filename = html.escape(audio.name, quote=True)
        # Keep speed choices outside Chrome's native menu, which is clipped
        # by the iframe. Each player has its own audio element and controls.
        speed_buttons = []
        for speed in (0.75, 1.0, 1.25, 1.5, 2.0):
            selected = "true" if speed == 1 else "false"
            speed_buttons.append(
                f'<button type="button" data-speed="{speed:g}" '
                f'aria-pressed="{selected}">{speed:g}×</button>'
            )
        choices = " ".join(speed_buttons)
        download_name = html.escape(f"spine-learn-{chunk['id']}.wav", quote=True)
        control = f"""
  <audio controls preload="none" controlslist="nodownload noplaybackrate"
         aria-label="Narration: {label}" src="../audio/{filename}">
    Audio playback unavailable.
  </audio>
  <div class="narration-options">
    <div class="narration-speeds" role="group" aria-label="Playback speed">
      <span>Speed</span>
      {choices}
    </div>
    <a href="../audio/{filename}" download="{download_name}">Download audio</a>
  </div>
"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Narration: {label}</title>
  <link rel="stylesheet" href="../style.css">
  <script src="../narration.js" defer></script>
</head>
<body class="narration-player">
  <small>LISTEN · {review_label} NARRATION</small>
  {control}
</body>
</html>
"""


def _narration_directives(
    chunk: NarrationChunk, review_status: str, base_url: str
) -> str:
    """Create the MyST player and transcript for one semantic section."""
    player_url = f"{base_url}/players/{chunk['id']}.html"
    return (
        f"\n```{{iframe}} {player_url}\n"
        f":title: Narration for {chunk['section']}\n"
        ":width: 100%\n"
        "```\n\n"
        f"```{{dropdown}} Narration transcript · {review_status}\n"
        f"{chunk['text'].strip()}\n"
        "```\n"
    )


def _add_guided_sections(
    notebook: NotebookNode, document: NarrationDocument, base_url: str
) -> NotebookNode:
    """Add narration and Continue links without changing the downloadable copy."""
    website = deepcopy(notebook)
    website.metadata.pop("jupytext", None)
    chunks = {chunk["section"]: chunk for chunk in document["chunks"]}
    previous_section: str | None = None

    for cell in website.cells:
        if cell.cell_type != "markdown":
            continue

        # Restore MyST labels so the website renderer can resolve section links.
        cell.source = re.sub(r'<a id="([a-z0-9-]+)"></a>', r"(\1)=", cell.source)
        for section, chunk in chunks.items():
            heading_pattern = rf"(\({re.escape(section)}\)=\n## [^\n]+\n)"
            directives = _narration_directives(
                chunk, document["review_status"], base_url
            )

            # Bind the current directives explicitly; each section has its own text.
            def append_narration(
                match: re.Match[str], content: str = directives
            ) -> str:
                """Keep the heading and follow it with this section's controls."""
                return match.group(1) + content

            cell.source = re.sub(heading_pattern, append_narration, cell.source)

        # Place Continue immediately before the next section, after any prose
        # that still belongs to the previous one in this Markdown cell.
        section_match = re.search(r"^\(([a-z0-9-]+)\)=$", cell.source, re.MULTILINE)
        if section_match and section_match[1] in chunks:
            section = section_match[1]
            if previous_section is not None:
                link = f"[Continue →](#{section})\n\n"
                cell.source = cell.source.replace(
                    section_match[0], link + section_match[0], 1
                )
            previous_section = section

    # Keep the interactive companion out of the standalone runnable notebook.
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
            "downloads": [
                {
                    "file": "downloads/reconstruction-basics.ipynb",
                    "title": "Runnable notebook",
                }
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
    Preview builds instead show a transcript and a message for missing audio.
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

    for chunk in document["chunks"]:
        player_path = site / "players" / f"{chunk['id']}.html"
        player_path.write_text(
            player_html(chunk, audio.get(chunk["id"]), document["review_status"]),
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
    parser.add_argument("command", choices=["notebook", "site"])
    parser.add_argument("--require-audio", action="store_true")
    arguments = parser.parse_args()

    try:
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
