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
    assert len(code) == 5
    assert "from spine.data.out import" in code[0].source
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
