"""Check the data conversion used by the WebGL-free event display."""

import base64
from pathlib import Path

import nbformat
import numpy as np
import pytest

from spine_learn.static_figure import coordinates, render_static_event


def test_plotly_coordinate_formats_agree() -> None:
    """Keep positions unchanged for both supported Plotly serialization forms."""
    points = np.array([-127.5, 0.0, 91.25], dtype="float32")
    encoded = {"dtype": "f4", "bdata": base64.b64encode(points.tobytes()).decode()}
    np.testing.assert_array_equal(coordinates(encoded), coordinates(points.tolist()))


def test_missing_event_fails_instead_of_publishing_empty_plot(tmp_path: Path) -> None:
    """A broken notebook output must not silently produce a misleading fallback."""
    with pytest.raises(ValueError, match="no Plotly event display"):
        render_static_event(nbformat.v4.new_notebook(), tmp_path / "event.png")
