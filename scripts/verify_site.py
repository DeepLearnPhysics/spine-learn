"""Check the rendered static artifact without a browser or live notebook kernel.

These integration checks verify section links, player assets, WAV metadata, and
the notebook download. They complement, but do not replace, visual review.
"""

import argparse
import json
import wave
from html.parser import HTMLParser
from pathlib import Path


class Tags(HTMLParser):
    """Collect HTML start tags and their attributes for simple artifact checks."""

    def __init__(self, text: str) -> None:
        """Parse a complete HTML string and retain its opening tags."""
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record attributes, treating boolean attributes as empty strings."""
        attributes = {name: value or "" for name, value in attrs}
        self.tags.append((tag, attributes))


def _verify_player(player_path: Path, root: Path, require_audio: bool) -> float | None:
    """Check one player's WAV references and return its duration when present."""
    tags = Tags(player_path.read_text(encoding="utf-8"))
    audio_elements = [attributes for tag, attributes in tags.tags if tag == "audio"]
    if require_audio:
        assert len(audio_elements) == 1, f"Missing audio in {player_path}"

    # Every player, including the no-audio fallback, must offer a usable transcript.
    transcripts = [
        attributes
        for tag, attributes in tags.tags
        if tag == "a" and attributes.get("download", "").endswith("-transcript.txt")
    ]
    assert len(transcripts) == 1, f"Missing transcript in {player_path}"
    transcript_path = (player_path.parent / transcripts[0]["href"]).resolve()
    assert transcript_path.is_relative_to(root.resolve())
    assert transcript_path.read_text(encoding="utf-8").strip()

    duration = None
    for attributes in audio_elements:
        audio_path = (player_path.parent / attributes["src"]).resolve()
        assert audio_path.is_relative_to(root.resolve())

        with wave.open(str(audio_path)) as audio:
            assert audio.getnchannels() == 1
            assert audio.getframerate() == 24000
            assert audio.getsampwidth() == 2
            duration = round(audio.getnframes() / audio.getframerate(), 3)

    return duration


def _verify_notebook(path: Path) -> None:
    """Require executed lesson cells, the expected SPINE version, and a figure."""
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert len(code_cells) == 6
    assert all(cell["execution_count"] for cell in code_cells)

    # Flatten outputs once so the error and figure checks remain easy to read.
    outputs = [output for cell in code_cells for output in cell["outputs"]]
    assert not any(output["output_type"] == "error" for output in outputs)
    assert any(
        "application/vnd.plotly.v1+json" in output.get("data", {}) for output in outputs
    )
    assert "SPINE 1.4.1" in json.dumps(notebook)


def verify(root: Path, require_audio: bool = False, base: str = "") -> None:
    """Verify lesson navigation, audio references, and the executed download.

    Parameters
    ----------
    root
        Directory containing the static HTML build.
    require_audio
        Fail if any narrated section has no current WAV reference.
    base
        Hosting prefix, such as ``/spine-learn`` for a GitHub Pages project site.
    """
    lesson = Tags((root / "lesson/index.html").read_text(encoding="utf-8"))
    anchors = {attributes["id"] for _, attributes in lesson.tags if "id" in attributes}
    expected_sections = {
        "orientation",
        "inspect-particles",
        "inspect-interactions",
        "selection",
    }
    assert expected_sections <= anchors

    links = {attributes.get("href") for tag, attributes in lesson.tags if tag == "a"}
    expected_targets = {"#inspect-particles", "#inspect-interactions", "#selection"}
    assert expected_targets <= links

    players = [
        attributes
        for tag, attributes in lesson.tags
        if tag == "iframe" and attributes.get("title", "").startswith("Narration for")
    ]
    assert len(players) == 5

    durations = {}
    for player in players:
        source = player["src"]
        assert source.startswith(base + "/players/")
        player_path = root / source.removeprefix(base).lstrip("/")
        duration = _verify_player(player_path, root, require_audio)
        if duration is not None:
            durations[player_path.stem] = duration

    _verify_notebook(root / "downloads/01_points_particles_interactions.ipynb")
    print(
        "Verified 4 sections, 3 Continue targets, "
        f"{len(durations)} playable WAV references, 6 executed cells, and figure."
    )
    print(json.dumps(durations, indent=2))


def main() -> None:
    """Parse the artifact directory and optional publication checks from the CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", type=Path, nargs="?", default=Path("_build/site/_build/html")
    )
    parser.add_argument("--require-audio", action="store_true")
    parser.add_argument("--base", default="")
    arguments = parser.parse_args()
    verify(arguments.root, arguments.require_audio, arguments.base)


if __name__ == "__main__":
    main()
