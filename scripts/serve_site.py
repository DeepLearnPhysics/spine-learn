"""Serve the built tutorial locally without caching pages or stylesheets.

The preview uses a stable URL while builds replace its contents. Disabling
caching makes each refresh reflect the latest build, including layout changes.
"""

import argparse
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import BinaryIO

ROOT = Path(__file__).resolve().parents[1]


class PreviewHandler(SimpleHTTPRequestHandler):
    """Serve static files with caching disabled for local development."""

    def send_head(self) -> BinaryIO | None:
        """Support single byte ranges so browsers can seek within audio files.

        Delegate ordinary requests, directory redirects, and missing files to
        the standard handler. Unsupported ranges fall back to a full response.
        """
        self._range_remaining: int | None = None
        range_header = self.headers.get("Range", "")
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header)
        path = Path(self.translate_path(self.path))
        if (
            self.command != "GET"
            or not match
            or not any(match.groups())
            or self.headers.get("If-Range")
            or not path.is_file()
        ):
            return super().send_head()

        try:
            source = path.open("rb")
        except OSError:
            return super().send_head()

        size = os.fstat(source.fileno()).st_size
        first, last = match.groups()
        if first:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        else:
            # A suffix range asks for the final N bytes of the representation.
            start = max(0, size - int(last))
            end = size - 1

        if start > end or start >= size:
            source.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        source.seek(start)
        self._range_remaining = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(self._range_remaining))
        self.end_headers()
        return source

    def copyfile(self, source: BinaryIO, outputfile: BinaryIO) -> None:
        """Copy only the requested bytes, without loading a whole WAV into memory."""
        if self._range_remaining is None:
            super().copyfile(source, outputfile)
            return

        remaining = self._range_remaining
        while remaining:
            block = source.read(min(64 * 1024, remaining))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)

    def end_headers(self) -> None:
        """Ensure the browser requests current files on every page refresh."""
        self.send_header("Accept-Ranges", "bytes")
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
