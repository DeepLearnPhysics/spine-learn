# Local speech synthesis

Build with `make tts-image`, then run `make narration` at the repository root.
Python 3.12, CPU PyTorch 2.6.0, Kokoro 0.9.4, eSpeak NG, and a small English spaCy
model are isolated from the tutorial environment. The image mounts this repository
as `/workspace`; it does not embed tutorial code or Kokoro weights. Only the
requested weights, config, and `af_heart` voice are downloaded to `.cache/kokoro`
at runtime, pinned to the SHA in `narration/config.yaml`. Never rebuild the image
just to edit narration. Rebuild it after changing its dependency recipe.

The default voice is `af_heart`, American English, speed 1.0. Inference is on CPU
with four PyTorch threads. Outputs are mono 24 kHz, 16-bit PCM WAV. An unchanged
build does not import Torch or load model assets. Semantic chunks can be split
internally by Kokoro, but their waveforms are concatenated into one cache unit.

```bash
docker build -t spine-learn-tts ./tts
mkdir -p .cache/kokoro
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/workspace" -v "$PWD/.cache/kokoro:/models" \
  spine-learn-tts build
```

Run `make terminology` to produce a separate all-terms listening sample under
`_build/terminology`. Run `make benchmark` for real incremental synthesis; results
are written to `_build/benchmark.json`. That benchmark refuses to overwrite an
existing benchmark manifest so its first-build timing cannot silently be cached.
Regular tests use a fake synthesizer and never load a speech model.

## Licenses and asset distribution

Verified from upstream pages on 2026-10-07:

- [Kokoro inference package](https://github.com/hexgrad/kokoro/blob/main/LICENSE):
  Apache-2.0.
- [Kokoro-82M model card](https://huggingface.co/hexgrad/Kokoro-82M): model weights
  are declared Apache-2.0. Preserve the upstream license and applicable notices
  if redistributing them. Its model card also records training-data attributions.
- [`af_heart` voice](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md):
  distributed in the same model repository. No distinct per-voice license was
  identified in that document. This prototype therefore keeps voice files, as
  well as weights, outside the image and does not publish those assets.
- [spaCy English pipeline 3.8.0](https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0):
  MIT, installed in the image for English grapheme-to-phoneme preprocessing.
- [eSpeak NG](https://github.com/espeak-ng/espeak-ng/blob/master/COPYING): GPLv3;
  this is a separate runtime dependency, not covered by Kokoro's Apache license.
  The local image retains installed package notices. Before publishing an image
  to GHCR, inventory all included packages and satisfy their notice/source
  distribution obligations. No container registry publishing is implemented.

The repository's workflow publishes a site containing generated narration, not
model weights or voice tensors. These notes record upstream declarations and
our distribution choices; they are not a blanket license for every dependency.
No reference-voice recordings, impersonation, or external speech API is used.
