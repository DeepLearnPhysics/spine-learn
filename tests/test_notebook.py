"""Check that the canonical lesson exports to a standard Jupyter notebook."""

from pathlib import Path

import nbformat

from spine_learn.build import export_notebook


def test_single_source_exports_standard_notebook(tmp_path: Path) -> None:
    """Export standard Jupyter cells and anchors from the canonical MyST source."""
    path = tmp_path / "lesson.ipynb"
    notebook = export_notebook(path, execute=False)
    nbformat.validate(nbformat.read(path, as_version=4))
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert len(code) == 6
    assert "from spine.io.read import HDF5Reader" in code[0].source
    assert not any("{code-cell}" in c.source for c in notebook.cells)
    assert any('<a id="orientation"></a>' in c.source for c in notebook.cells)


def test_companion_keeps_notebook_portable(tmp_path: Path) -> None:
    """Add one correctly prefixed website companion without modifying the download."""
    from spine_learn.build import _add_guided_sections
    from spine_learn.narration import load_inputs

    notebook = export_notebook(tmp_path / "lesson.ipynb", execute=False)
    document, _, _ = load_inputs()
    website = _add_guided_sections(notebook, document, "/spine-learn")
    original = "\n".join(cell.source for cell in notebook.cells)
    rendered = "\n".join(cell.source for cell in website.cells)
    assert "tutor/index.html" not in original
    assert rendered.count("/spine-learn/tutor/index.html") == 1
    assert rendered.index("tutor/index.html") < rendered.index("(orientation)=")


def test_guided_steps_and_lesson_download(tmp_path: Path) -> None:
    """Keep guided controls on the website and offer the named portable notebook."""
    from spine_learn.build import NOTEBOOK_PATH, _add_guided_sections
    from spine_learn.narration import load_inputs

    notebook = export_notebook(tmp_path / "lesson.ipynb", execute=False)
    document, _, _ = load_inputs()
    website = _add_guided_sections(notebook, document, "/spine-learn")
    rendered = "\n".join(cell.source for cell in website.cells)
    original = "\n".join(cell.source for cell in notebook.cells)
    assert rendered.count("/players/orientation-explanation.html") == 1
    assert rendered.index("/players/orientation-explanation.html") > rendered.index(
        "(orientation-activity)="
    )
    assert "/players/" not in original
    assert "downloads" not in notebook.metadata
    assert website.metadata["downloads"][0]["filename"] == NOTEBOOK_PATH.name
    assert website.metadata["downloads"][0]["url"].startswith("/spine-learn/downloads/")


def test_every_narration_has_a_playback_focus() -> None:
    """Manual playback can identify its section without a guided next step."""
    from spine_learn.build import player_html
    from spine_learn.narration import load_inputs

    document, _, _ = load_inputs()
    for chunk in document["chunks"]:
        rendered = player_html(chunk, Path("audio.wav"))
        focus = chunk.get("focus", chunk["section"])
        assert f'data-focus="{focus}"' in rendered


def test_colab_export_is_current() -> None:
    """Keep the GitHub-hosted export synchronized with the maintained lesson."""
    from spine_learn.build import COLAB_PATH, colab_notebook

    expected = colab_notebook()
    assert nbformat.read(COLAB_PATH, as_version=4) == expected, "Run make colab"
    code = [cell for cell in expected.cells if cell.cell_type == "code"]
    assert len(code) == 7
    assert '%pip install -q "spine[viz]==1.4.1"' in code[0].source
    assert any('renderer="colab"' in cell.source for cell in code)
    assert all(not cell.outputs and cell.execution_count is None for cell in code)
