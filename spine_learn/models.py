"""Describe the small YAML records shared by the tutorial build helpers.

These types document validated data; they do not replace runtime validation of
files edited by authors. Keep the on-disk format as ordinary YAML dictionaries.
"""

from pathlib import Path
from typing import Protocol, TypedDict


class NarrationChunk(TypedDict):
    """One spoken explanation and the tutorial section it accompanies."""

    id: str
    section: str
    text: str


class NarrationDocument(TypedDict):
    """A tutorial's narration chunks and human review status."""

    tutorial: str
    review_status: str
    chunks: list[NarrationChunk]


class SynthesisConfig(TypedDict):
    """Inputs that affect the speech produced by the local Kokoro backend."""

    backend: str
    model: str
    revision: str
    voice: str
    language: str
    speed: float
    sample_rate: int
    tool_version: str


class SpeechBackend(Protocol):
    """The one operation needed from either Kokoro or a test double."""

    def synthesize(self, text: str, output_path: Path, config: SynthesisConfig) -> None:
        """Write synthesized speech to the requested WAV file."""
        ...
