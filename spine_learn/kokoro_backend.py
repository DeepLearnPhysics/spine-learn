"""Provide CPU-only Kokoro synthesis without requiring TTS packages for the site.

The heavy dependencies are installed in the TTS container. Import them only when
constructing this backend, so validation and cache hits work in a small Python
environment that has no speech model or PyTorch installation.
"""

from importlib import import_module
from pathlib import Path

from .models import SynthesisConfig


class KokoroBackend:
    """Load pinned model assets once and synthesize multiple narration chunks."""

    def __init__(self, config: SynthesisConfig) -> None:
        """Download cached assets and initialize a CPU pipeline and voice tensor."""
        # Runtime imports keep container-only packages out of the site environment.
        torch = import_module("torch")
        huggingface = import_module("huggingface_hub")
        kokoro = import_module("kokoro")

        torch.set_num_threads(4)
        download_options = {
            "repo_id": config["model"],
            "revision": config["revision"],
        }
        model_config = huggingface.hf_hub_download(
            filename="config.json", **download_options
        )
        model_weights = huggingface.hf_hub_download(
            filename="kokoro-v1_0.pth", **download_options
        )
        voice_file = huggingface.hf_hub_download(
            filename=f"voices/{config['voice']}.pt", **download_options
        )

        model = kokoro.KModel(
            repo_id=config["model"], config=model_config, model=model_weights
        )
        model = model.to("cpu").eval()
        self.pipeline = kokoro.KPipeline(
            lang_code=config["language"],
            repo_id=config["model"],
            model=model,
            device="cpu",
        )
        self.voice = torch.load(voice_file, map_location="cpu", weights_only=True)

    def synthesize(self, text: str, output_path: Path, config: SynthesisConfig) -> None:
        """Join Kokoro's internal segments into one 24 kHz PCM WAV per chunk."""
        numpy = import_module("numpy")
        soundfile = import_module("soundfile")

        # Kokoro may split a paragraph internally; the cache unit stays semantic.
        results = self.pipeline(text, voice=self.voice, speed=config["speed"])
        segments = [result.audio.numpy() for result in results]
        if not segments:
            raise RuntimeError("Kokoro returned no audio")

        waveform = numpy.concatenate(segments)
        soundfile.write(
            str(output_path), waveform, config["sample_rate"], subtype="PCM_16"
        )
