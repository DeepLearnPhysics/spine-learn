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
