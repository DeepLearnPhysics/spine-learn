"""Check narration validation, pronunciation rules, and selective audio caching."""

import wave
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from spine_learn.models import NarrationDocument, SynthesisConfig
from spine_learn.narration import (
    ConfigurationError,
    build,
    current_audio,
    expand,
    fingerprint,
    load_inputs,
    read_yaml,
)

NarrationInputs = tuple[NarrationDocument, SynthesisConfig, dict[str, str]]


class FakeBackend:
    """Write tiny deterministic WAV files without loading a speech model."""

    def __init__(self) -> None:
        """Start with an empty record of synthesis requests."""
        self.calls: list[str] = []

    def synthesize(self, text: str, output_path: Path, config: SynthesisConfig) -> None:
        """Record the requested text and write a valid silent test WAV."""
        self.calls.append(text)
        with wave.open(str(output_path), "wb") as out:
            out.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            out.writeframes(b"\0\0" * 240)


@pytest.fixture
def inputs() -> NarrationInputs:
    """Return fresh copies of the validated inputs so tests stay independent."""
    return deepcopy(load_inputs())


def test_yaml_and_mapping(inputs: NarrationInputs) -> None:
    """Accept the real four-section draft narration and its section mapping."""
    document, _, _ = inputs
    assert len(document["chunks"]) == 4
    assert document["review_status"] == "draft"


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda document: document["chunks"].append(document["chunks"][0]),
            "Duplicate chunk ID",
        ),
        (
            lambda document: document["chunks"][0].update(section="missing"),
            "missing tutorial section",
        ),
        (lambda document: document["chunks"][0].update(text=" "), "nonempty"),
        (
            lambda document: document["chunks"][0].update(id="../escape"),
            "lowercase slugs",
        ),
        (lambda document: document.update(chunks="wrong"), "nonempty list"),
    ],
)
def test_bad_narration(
    tmp_path: Path,
    inputs: NarrationInputs,
    mutation: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    """Reject invalid chunk metadata with an actionable author-facing message."""
    document, _, _ = inputs
    # Deliberately break the validated schema to exercise authoring errors.
    mutation(cast(dict[str, Any], document))
    path = tmp_path / "narration.yaml"
    path.write_text(yaml.safe_dump(document))
    with pytest.raises(ConfigurationError, match=message):
        load_inputs(path)


@pytest.mark.parametrize("text", ["chunks: [", "a: 1\na: 2", "- list"])
def test_yaml_errors(tmp_path: Path, text: str) -> None:
    """Reject malformed YAML, duplicate keys, and a non-mapping document."""
    path = tmp_path / "bad.yaml"
    path.write_text(text)
    with pytest.raises(ConfigurationError):
        read_yaml(path)


def test_pronunciations_are_longest_nonrecursive_and_bounded() -> None:
    """Prefer longer matches without recursive substitutions or partial words."""
    result, used = expand(
        "Graph-SPICE SPICE HDF5 HDF50 dE/dx",
        {
            "SPICE": "spicy",
            "Graph-SPICE": "Graph Spice",
            "HDF5": "H D F five",
            "dE/dx": "D E by D X",
        },
    )
    assert result == "Graph Spice spicy H D F five HDF50 D E by D X"
    assert len(used) == 4
    assert expand("SPINE", {"SPINE": "spine", "spine": "wrong"})[0] == "spine"


def test_hash_deterministic_and_normalized(inputs: NarrationInputs) -> None:
    """Ignore ordering and whitespace, but invalidate changed spoken content."""
    document, configuration, dictionary = inputs
    chunk = document["chunks"][0]
    original = fingerprint(chunk, configuration, dictionary)
    assert original == fingerprint(
        chunk,
        cast(SynthesisConfig, dict(reversed(list(configuration.items())))),
        dictionary,
    )
    chunk["text"] = "  " + chunk["text"].replace(" ", "  ") + "\n"
    assert original == fingerprint(chunk, configuration, dictionary)
    chunk["text"] += " Added sentence."
    assert original != fingerprint(chunk, configuration, dictionary)


@pytest.mark.parametrize(
    "key,value",
    [
        ("voice", "am_adam"),
        ("model", "another-model"),
        ("backend", "future-backend"),
        ("speed", 1.1),
        ("revision", "a" * 40),
    ],
)
def test_config_invalidates(
    inputs: NarrationInputs, key: str, value: str | float
) -> None:
    """Invalidate audio whenever a speech-affecting configuration value changes."""
    document, configuration, dictionary = inputs
    original = fingerprint(document["chunks"][0], configuration, dictionary)
    changed_configuration = cast(SynthesisConfig, {**configuration, key: value})
    assert (
        fingerprint(document["chunks"][0], changed_configuration, dictionary)
        != original
    )


def test_realistic_incremental_sequence(
    tmp_path: Path, inputs: NarrationInputs
) -> None:
    """Rebuild only affected chunks across ordinary narration maintenance edits."""
    document, configuration, dictionary = inputs
    fake = FakeBackend()
    assert build(document, configuration, dictionary, tmp_path, fake) == 4
    assert build(document, configuration, dictionary, tmp_path, fake) == 0
    # Text and pronunciation edits should each touch just one recording.
    document["chunks"][1]["text"] += " Look again."
    assert build(document, configuration, dictionary, tmp_path, fake) == 1
    dictionary["HDF5"] = "H D F five files"
    assert build(document, configuration, dictionary, tmp_path, fake) == 1
    dictionary["unused-term"] = "unused term"
    assert build(document, configuration, dictionary, tmp_path, fake) == 0
    # Voice changes affect every recording; a missing file affects only itself.
    configuration["voice"] = "am_adam"
    assert build(document, configuration, dictionary, tmp_path, fake) == 4
    assert len(current_audio(document, configuration, dictionary, tmp_path)) == 4
    first = next(
        iter(current_audio(document, configuration, dictionary, tmp_path).values())
    )
    first.unlink()
    assert build(document, configuration, dictionary, tmp_path, fake) == 1


def test_failed_synthesis_does_not_publish(
    tmp_path: Path, inputs: NarrationInputs
) -> None:
    """Keep failed synthesis from publishing partial audio or a manifest."""
    document, configuration, dictionary = inputs

    class Broken:
        """Simulate a backend that fails after writing an incomplete audio file."""

        def synthesize(
            self, text: str, output_path: Path, config: SynthesisConfig
        ) -> None:
            """Write partial output, then raise the simulated inference failure."""
            output_path.write_bytes(b"broken")
            raise RuntimeError("inference failed")

    with pytest.raises(RuntimeError):
        build(document, configuration, dictionary, tmp_path, Broken())
    assert not list(tmp_path.glob("*.wav"))
    assert not (tmp_path / "manifest.json").exists()


def test_stale_audio_not_presented(tmp_path: Path, inputs: NarrationInputs) -> None:
    """Hide an old recording when its narration source changes."""
    document, configuration, dictionary = inputs
    build(document, configuration, dictionary, tmp_path, FakeBackend())
    document["chunks"][0]["text"] += " Changed."
    assert len(current_audio(document, configuration, dictionary, tmp_path)) == 3


def test_corrupted_audio_not_presented(tmp_path: Path, inputs: NarrationInputs) -> None:
    """Hide cached WAV files whose bytes no longer match the manifest."""
    document, configuration, dictionary = inputs
    build(document, configuration, dictionary, tmp_path, FakeBackend())
    next(tmp_path.glob("*.wav")).write_bytes(b"corrupted" * 20)
    assert len(current_audio(document, configuration, dictionary, tmp_path)) == 3


def test_corrupted_audio_is_regenerated(
    tmp_path: Path, inputs: NarrationInputs
) -> None:
    """Repair only the corrupted cached recording on the next build."""
    document, configuration, dictionary = inputs
    build(document, configuration, dictionary, tmp_path, FakeBackend())
    next(tmp_path.glob("*.wav")).write_bytes(b"corrupted" * 20)
    assert build(document, configuration, dictionary, tmp_path, FakeBackend()) == 1
    assert len(current_audio(document, configuration, dictionary, tmp_path)) == 4
