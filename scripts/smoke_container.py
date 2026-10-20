"""Check the production image on loopback without credentials or provider calls."""

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request


def main() -> None:
    """Test a restricted container, then remove it even if a check fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("--require-audio", action="store_true")
    arguments = parser.parse_args()
    container = subprocess.check_output(
        [
            "docker",
            "run",
            "--detach",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--publish",
            "127.0.0.1::8080",
            arguments.image,
        ],
        text=True,
    ).strip()
    try:
        address = subprocess.check_output(
            ["docker", "port", container, "8080"], text=True
        ).strip()
        base = f"http://{address}"

        def fetch(
            path: str, headers: dict[str, str] | None = None
        ) -> tuple[int, bytes]:
            """Use the production Host header while connecting only to loopback."""
            request = urllib.request.Request(
                base + path,
                headers={
                    "Host": "spine-learn.slac.stanford.edu",
                    **(headers or {}),
                },
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, response.read()

        for attempt in range(30):
            try:
                assert fetch("/readyz")[0] == 200
                break
            except (urllib.error.URLError, ConnectionError):
                if attempt == 29:
                    raise
                time.sleep(1)
        assert fetch("/")[0] == 200
        assert fetch("/lesson")[0] == 200
        assert json.loads(fetch("/api/tutor/status")[1])["configured"] is False
        player = fetch("/players/orientation.html")[1].decode()
        audio = re.search(r'src="\.\./(audio/[^"]+)"', player)
        if arguments.require_audio:
            assert audio, "Publication image must contain narration"
        if audio:
            status, body = fetch("/" + audio[1], {"Range": "bytes=44-143"})
            assert status == 206 and len(body) == 100
        assert fetch("/downloads/spine-learn-orientation-transcript.txt")[0] == 200
        assert fetch("/downloads/01_points_particles_interactions.ipynb")[0] == 200
        print(
            "Container passed: read-only runtime, pages, notebook, transcript, "
            "audio range, key-free status."
        )
    finally:
        subprocess.run(["docker", "logs", container], check=False)
        subprocess.run(
            ["docker", "rm", "--force", container],
            check=True,
            stdout=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    main()
