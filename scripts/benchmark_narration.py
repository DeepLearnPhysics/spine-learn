"""Measure real CPU synthesis and cache reuse inside the TTS container.

This is an opt-in integration benchmark, not part of the ordinary unit tests.
Run it with ``make benchmark`` after building the TTS image.
"""

import json
import time
import wave
from copy import deepcopy

from spine_learn.models import NarrationDocument
from spine_learn.narration import ROOT, build, load_inputs


def main() -> None:
    """Benchmark a full build, a cache hit, and two kinds of incremental edit."""
    document, configuration, dictionary = load_inputs()
    output = ROOT / "_build/benchmark-audio"
    if (output / "manifest.json").exists():
        raise SystemExit(
            "Use a fresh _build/benchmark-audio directory for a first-build benchmark."
        )

    measurements: dict[str, object] = {}

    def measure(
        name: str,
        narration: NarrationDocument,
        pronunciations: dict[str, str],
    ) -> None:
        """Time one build and record how many chunks actually needed synthesis."""
        start = time.perf_counter()
        generated = build(narration, configuration, pronunciations, output)
        measurements[name] = {
            "generated": generated,
            "seconds": round(time.perf_counter() - start, 3),
        }

    # The second build should skip everything without constructing a backend.
    measure("first_with_cached_model_download", document, dictionary)
    measure("unchanged", document, dictionary)

    # Edit copies in memory; the author's YAML files must remain unchanged.
    changed_document = deepcopy(document)
    changed_document["chunks"][1]["text"] += " Check those units once more."
    measure("one_chunk_edit", changed_document, dictionary)

    changed_dictionary = {**dictionary, "HDF5": "H D F five format"}
    measure("one_used_pronunciation_edit", changed_document, changed_dictionary)

    # Read durations from the files generated in the final benchmark step.
    durations = {}
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    for chunk_id, entry in manifest["chunks"].items():
        with wave.open(str(output / entry["file"])) as audio:
            duration = audio.getnframes() / audio.getframerate()
            durations[chunk_id] = round(duration, 3)

    measurements["audio_durations_seconds"] = durations
    report = json.dumps(measurements, indent=2)
    (ROOT / "_build/benchmark.json").write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
