"""Lint notebook code cells without maintaining a duplicate Python source file.

Code cells share a kernel namespace, so lint their combined source as one module.
Check formatting separately for each cell to preserve the notebook's boundaries.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import jupytext

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tutorials/01_reconstruction_basics.md"


def main() -> None:
    """Apply the repository's Ruff checks to the canonical tutorial's Python."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    notebook = jupytext.read(SOURCE)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    virtual_path = "tutorials/01_reconstruction_basics.py"
    ruff = [sys.executable, "-m", "ruff"]

    # Ruff receives the full namespace, including imports from earlier cells.
    combined = "\n\n".join(cell.source for cell in code_cells) + "\n"
    subprocess.run(
        [*ruff, "check", "--stdin-filename", virtual_path, "-"],
        input=combined,
        text=True,
        cwd=ROOT,
        check=True,
    )

    for number, cell in enumerate(code_cells, start=1):
        result = subprocess.run(
            [*ruff, "format", "--check", "--stdin-filename", virtual_path, "-"],
            input=cell.source + "\n",
            text=True,
            capture_output=True,
            cwd=ROOT,
            check=False,
        )
        if result.returncode:
            parser.exit(1, f"Tutorial code cell {number} needs Ruff formatting.\n")

    print(f"Lint and formatting checks passed for {len(code_cells)} tutorial cells.")


if __name__ == "__main__":
    main()
