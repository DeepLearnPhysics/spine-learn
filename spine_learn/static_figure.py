"""Render a WebGL-free event view from the executed lesson's Plotly output."""

import base64
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from nbformat import NotebookNode

STATIC_FIGURE = "entry-0-particles.png"
STATIC_URL = f"https://spine-learn.slac.stanford.edu/downloads/{STATIC_FIGURE}"


def coordinates(values: Any) -> np.ndarray:
    """Decode either JSON arrays or Plotly's typed binary coordinate arrays."""
    if isinstance(values, dict):
        return np.frombuffer(base64.b64decode(values["bdata"]), dtype=values["dtype"])
    return np.asarray(values)


def render_static_event(notebook: NotebookNode, destination: Path) -> None:
    """Save three equal-scale projections with the interactive plot's colors.

    Read the executed output rather than loading another event or duplicating
    the lesson's reconstruction logic. Fail the build if that output is absent.
    """
    plots = [
        output.get("data", {}).get("application/vnd.plotly.v1+json")
        for cell in notebook.cells
        for output in cell.get("outputs", [])
    ]
    plot = next((plot for plot in plots if plot), None)
    if plot is None:
        raise ValueError("The executed lesson has no Plotly event display")

    figure = Figure(figsize=(12, 5), layout="constrained")
    FigureCanvasAgg(figure)
    axes = figure.subplots(1, 3)
    projections = (("x", "y"), ("x", "z"), ("z", "y"))
    for trace in plot["data"]:
        if trace.get("type") != "scatter3d":
            continue
        marker = trace["marker"]
        # Drawer assigns one particle ID and one corresponding color per trace.
        particle_id = float(coordinates(marker["color"])[0])
        fraction = (particle_id - marker["cmin"]) / max(
            marker["cmax"] - marker["cmin"], 1
        )
        color = min(marker["colorscale"], key=lambda stop: abs(stop[0] - fraction))[1]
        for axis, (horizontal, vertical) in zip(axes, projections, strict=True):
            axis.scatter(
                coordinates(trace[horizontal]),
                coordinates(trace[vertical]),
                s=3,
                color=color,
                label=trace["name"],
                rasterized=True,
            )

    for axis, (horizontal, vertical) in zip(axes, projections, strict=True):
        axis.set_xlabel(f"{horizontal} [cm]")
        axis.set_ylabel(f"{vertical} [cm]")
        axis.set_aspect("equal", adjustable="box")
        axis.grid(alpha=0.2)
    figure.suptitle("Entry 0: reconstructed particle candidates — static projections")
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside lower center", ncol=5, markerscale=3)
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=160)
