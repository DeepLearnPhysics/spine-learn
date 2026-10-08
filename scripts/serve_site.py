"""Serve the built tutorial locally without caching pages or stylesheets.

The preview uses a stable URL while builds replace its contents. Disabling
caching makes each refresh reflect the latest build, including layout changes.
"""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PreviewHandler(SimpleHTTPRequestHandler):
    """Serve static files with caching disabled for local development."""

    def end_headers(self) -> None:
        """Ensure the browser requests current files on every page refresh."""
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> None:
    """Start a loopback-only preview of the generated static website."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--directory", type=Path, default=ROOT / "_build/site/_build/html"
    )
    arguments = parser.parse_args()
    if not (arguments.directory / "index.html").is_file():
        parser.exit(1, "No built site found. Run make site first.\n")

    handler = partial(PreviewHandler, directory=str(arguments.directory))
    with ThreadingHTTPServer(("127.0.0.1", arguments.port), handler) as server:
        print(
            f"Preview: http://localhost:{arguments.port} (caching disabled)", flush=True
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nPreview stopped.")


if __name__ == "__main__":
    main()
