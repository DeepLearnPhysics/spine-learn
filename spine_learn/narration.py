"""Validate narration sources and incrementally synthesize semantic audio chunks.

Authors edit YAML; this module validates it before handing text to a backend.
Only chunks whose speech inputs or cached files have changed are synthesized.
"""

import argparse
import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any, cast

import yaml

from .models import (
    NarrationChunk,
    NarrationDocument,
    SpeechBackend,
    SynthesisConfig,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tutorials/01_reconstruction_basics.md"
NARRATION = ROOT / "narration/01_reconstruction_basics.yaml"
OUTPUT = ROOT / "_build/audio"
ANCHOR = re.compile(r"^\(([a-z0-9-]+)\)=$", re.MULTILINE)
ID = re.compile(r"^[a-z][a-z0-9-]*$")


class ConfigurationError(ValueError):
    """Report an actionable authoring or build error."""


class UniqueLoader(yaml.SafeLoader):
    """Read safe YAML while rejecting duplicate or non-string mapping keys."""


def _mapping(
    loader: UniqueLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[str, Any]:
    """Construct a YAML mapping without silently overwriting duplicate keys."""
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            line = key_node.start_mark.line + 1
            raise ConfigurationError(f"YAML keys must be unique strings (line {line})")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def read_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping and give authors a readable error when it is invalid.

    Values remain untyped at this boundary because their schema has not yet been
    checked. ``load_inputs`` validates them before returning typed records.
    """
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)
    except (OSError, yaml.YAMLError) as error:
        raise ConfigurationError(f"Cannot read {path}: {error}") from error

    if not isinstance(value, dict):
        raise ConfigurationError(f"{path}: expected a YAML mapping")
    return value


def _validate_document(document: dict[str, Any], anchors: list[str]) -> None:
    """Check the tutorial identity, review label, and section-linked chunks."""
    tutorial = document.get("tutorial")
    if not isinstance(tutorial, str) or not ID.fullmatch(tutorial):
        raise ConfigurationError("tutorial must be a stable lowercase slug")
    if document.get("review_status") not in ("draft", "reviewed"):
        raise ConfigurationError("review_status must be draft or reviewed")
    if len(anchors) != len(set(anchors)):
        raise ConfigurationError("Tutorial contains duplicate section anchors")

    chunks = document.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ConfigurationError("chunks must be a nonempty list")

    seen_ids: set[str] = set()
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise ConfigurationError("Each chunk must be a mapping")

        chunk_id = chunk.get("id")
        if not isinstance(chunk_id, str) or not ID.fullmatch(chunk_id):
            raise ConfigurationError(
                "Chunk IDs must be lowercase slugs, e.g. inspect-particles"
            )
        if chunk_id in seen_ids:
            raise ConfigurationError(f"Duplicate chunk ID: {chunk_id}")
        seen_ids.add(chunk_id)

        if chunk.get("section") not in anchors:
            raise ConfigurationError(
                f"{chunk_id}: missing tutorial section {chunk.get('section')!r}"
            )
        text = chunk.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ConfigurationError(f"{chunk_id}: narration text must be nonempty")


def _validate_config(configuration: dict[str, Any]) -> None:
    """Reject unsupported backends, unpinned models, and invalid speech settings."""
    required = {
        "backend",
        "model",
        "revision",
        "voice",
        "language",
        "speed",
        "sample_rate",
        "tool_version",
    }
    if set(configuration) != required:
        names = ", ".join(sorted(required))
        raise ConfigurationError(f"Configuration requires exactly: {names}")
    if configuration["backend"] != "kokoro":
        raise ConfigurationError(f"Unsupported backend: {configuration['backend']}")

    # Check string fields before passing them to regular expressions or downloads.
    for key in required - {"speed", "sample_rate"}:
        value = configuration[key]
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError(f"{key} must be a nonempty string")

    if not re.fullmatch(r"[0-9a-f]{40}", configuration["revision"]):
        raise ConfigurationError(
            "revision must be an immutable 40-character model commit SHA"
        )

    speed = configuration["speed"]
    if (
        not isinstance(speed, (int, float))
        or not math.isfinite(speed)
        or not 0.5 <= speed <= 2
    ):
        raise ConfigurationError("speed must be between 0.5 and 2")
    if configuration["sample_rate"] != 24000:
        raise ConfigurationError("Kokoro output sample_rate must be 24000")


def load_inputs(
    narration: Path = NARRATION,
    source: Path = SOURCE,
    config: Path | None = None,
    pronunciations: Path | None = None,
) -> tuple[NarrationDocument, SynthesisConfig, dict[str, str]]:
    """Read and validate narration, synthesis settings, and pronunciations.

    Section references are checked against explicit anchors in the canonical
    tutorial. No model is downloaded or loaded during validation.
    """
    document = read_yaml(narration)
    configuration = read_yaml(config or ROOT / "narration/config.yaml")
    dictionary = read_yaml(pronunciations or ROOT / "narration/pronunciations.yaml")
    anchors = ANCHOR.findall(source.read_text(encoding="utf-8"))

    _validate_document(document, anchors)
    _validate_config(configuration)
    for key, value in dictionary.items():
        if not key.strip() or not isinstance(value, str) or not value.strip():
            raise ConfigurationError(
                "Pronunciations must map nonempty strings to nonempty strings"
            )

    # These casts record the guarantees established by the checks above.
    return (
        cast(NarrationDocument, document),
        cast(SynthesisConfig, configuration),
        cast(dict[str, str], dictionary),
    )


def normalize(text: str) -> str:
    """Collapse authoring whitespace without changing words or punctuation."""
    return " ".join(text.split())


def expand(text: str, dictionary: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Apply pronunciations once and return the expanded text and entries used.

    Longer terms take precedence over overlapping shorter terms. Word boundaries
    avoid matches inside larger identifiers, and replacements are not reprocessed.
    """
    if not dictionary:
        return text, {}

    ordered_terms = sorted(dictionary, key=lambda term: (-len(term), term))
    alternatives = "|".join(re.escape(term) for term in ordered_terms)
    pattern = re.compile(r"(?<!\w)(?:" + alternatives + r")(?!\w)")
    used: dict[str, str] = {}

    def substitute(match: re.Match[str]) -> str:
        """Record each matched dictionary entry while replacing its spelling."""
        term = match.group()
        used[term] = dictionary[term]
        return dictionary[term]

    return pattern.sub(substitute, text), used


def digest(value: object) -> str:
    """Hash a JSON-serializable value with stable key ordering and encoding."""
    serialized = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def fingerprint(
    chunk: NarrationChunk,
    config: SynthesisConfig,
    dictionary: dict[str, str],
) -> tuple[str, str]:
    """Return a chunk's speech-input hash and pronunciation-expanded text."""
    original = normalize(chunk["text"])
    spoken, used = expand(original, dictionary)

    # Only relevant pronunciations belong in this chunk's key. New matches also
    # change the expanded text; unrelated dictionary edits leave this key alone.
    inputs = {
        "text": original,
        "spoken": spoken,
        "pronunciations": used,
        "config": config,
        "recipe": recipe_hash(),
    }
    return digest(inputs), spoken


def recipe_hash() -> str:
    """Include backend code and container dependencies in audio cache keys."""
    recipe_paths = [
        Path(__file__),
        ROOT / "spine_learn/kokoro_backend.py",
        ROOT / "tts/Dockerfile",
        ROOT / "tts/requirements.txt",
    ]
    recipe_contents = {
        str(path.relative_to(ROOT)): path.read_text(encoding="utf-8")
        for path in recipe_paths
    }
    return digest(recipe_contents)


def _synthesize_chunk(
    backend: SpeechBackend, text: str, path: Path, config: SynthesisConfig
) -> None:
    """Generate a temporary WAV and publish it only after synthesis succeeds."""
    temporary = path.with_suffix(".tmp.wav")
    try:
        backend.synthesize(text, temporary, config)
        if not temporary.is_file() or temporary.stat().st_size <= 44:
            raise ConfigurationError(f"{path.name}: synthesis produced no usable audio")
        temporary.replace(path)
    finally:
        # A failed build must not leave a partial file that looks like cached audio.
        temporary.unlink(missing_ok=True)


def build(
    doc: NarrationDocument,
    config: SynthesisConfig,
    dictionary: dict[str, str],
    output: Path = OUTPUT,
    backend: SpeechBackend | None = None,
) -> int:
    """Synthesize changed chunks, write their manifest, and return their count.

    The backend is constructed lazily: a fully cached build never loads Kokoro.
    Tests can provide a lightweight backend implementing ``synthesize`` instead.
    """
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    entries: dict[str, dict[str, str]] = {}
    generated = 0
    valid_audio = current_audio(doc, config, dictionary, output)

    for chunk in doc["chunks"]:
        chunk_id = chunk["id"]
        key, spoken = fingerprint(chunk, config, dictionary)
        filename = f"{chunk_id}.{key}.wav"
        path = output / filename
        chunk_start = time.perf_counter()

        if chunk_id in valid_audio:
            state = "cached"
        else:
            if backend is None:
                from .kokoro_backend import KokoroBackend

                backend = KokoroBackend(config)
            _synthesize_chunk(backend, spoken, path, config)
            generated += 1
            state = "generated"

        entries[chunk_id] = {
            "hash": key,
            "file": filename,
            "section": chunk["section"],
            "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        elapsed = time.perf_counter() - chunk_start
        print(f"{state:9} {chunk_id} ({elapsed:.3f}s)")

    # Publish the manifest last so readers never see a partially completed build.
    manifest = {
        "tutorial": doc["tutorial"],
        "review_status": doc["review_status"],
        "chunks": entries,
    }
    temporary_manifest = output / "manifest.tmp.json"
    temporary_manifest.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    temporary_manifest.replace(output / "manifest.json")

    elapsed = time.perf_counter() - start
    print(f"Generated {generated}/{len(doc['chunks'])} chunks in {elapsed:.3f}s")
    return generated


def current_audio(
    doc: NarrationDocument,
    config: SynthesisConfig,
    dictionary: dict[str, str],
    output: Path = OUTPUT,
) -> dict[str, Path]:
    """Return only audio matching current speech inputs and manifest checksums."""
    manifest_path = output / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}

    result = {}
    for chunk in doc["chunks"]:
        chunk_id = chunk["id"]
        key, _ = fingerprint(chunk, config, dictionary)
        entry = manifest.get("chunks", {}).get(chunk_id, {})
        filename = f"{chunk_id}.{key}.wav"
        audio_path = output / filename

        # Check names and existence before reading potentially large audio files.
        if entry.get("hash") != key or entry.get("file") != filename:
            continue
        if not audio_path.is_file():
            continue
        checksum = hashlib.sha256(audio_path.read_bytes()).hexdigest()
        if entry.get("audio_sha256") == checksum:
            result[chunk_id] = audio_path

    return result


def main() -> None:
    """Expose validation, cache status, and synthesis as small CLI commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "status", "build"])
    parser.add_argument("--narration", type=Path, default=NARRATION)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    try:
        document, configuration, dictionary = load_inputs(arguments.narration)
        if arguments.command == "build":
            build(document, configuration, dictionary, arguments.output)
        elif arguments.command == "status":
            available = current_audio(
                document, configuration, dictionary, arguments.output
            )
            for chunk in document["chunks"]:
                status = "OK" if chunk["id"] in available else "MISSING/STALE"
                print(f"{status} {chunk['id']}")
        else:
            print(
                f"Validated {len(document['chunks'])} chunks; "
                f"narration review: {document['review_status']}"
            )
    except (OSError, RuntimeError, ImportError, ValueError) as error:
        parser.exit(1, f"Narration error: {error}\n")


if __name__ == "__main__":
    main()
