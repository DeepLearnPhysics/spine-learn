"""Serve the static lesson and a loopback-only Gemini tutor on one origin.

This development server is for local previews; public hosting uses Gunicorn.
Keeping the API on the preview origin avoids CORS configuration and exposing
credentials.
"""

import argparse
import json
import sys
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

# Direct script execution puts scripts/ rather than the repository on sys.path.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.serve_site import PreviewHandler  # noqa: E402
from spine_learn.tutor import LessonTutor, TutorError  # noqa: E402


class TutorHandler(PreviewHandler):
    """Serve files and a small JSON API without allowing cross-origin requests."""

    server: ThreadingHTTPServer
    tutor: LessonTutor

    def _send_json(self, data: dict, status: int = 200) -> None:
        """Send a bounded JSON response with caching disabled."""
        encoded = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)

    def _trusted_request(self) -> bool:
        """Reject foreign hosts and origins before reading credentials or bodies."""
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        return host in hosts and (origin is None or origin == f"http://{host}")

    def do_GET(self) -> None:
        """Return tutor readiness or the requested static asset."""
        if not self._trusted_request():
            self._send_json({"error": "This preview accepts local requests only."}, 403)
        elif urlsplit(self.path).path == "/api/tutor/status":
            self._send_json(self.tutor.status())
        else:
            super().do_GET()

    def do_POST(self) -> None:
        """Validate a chat request and return its answer or a recoverable error."""
        if not self._trusted_request():
            self._send_json({"error": "This preview accepts local requests only."}, 403)
            return
        route = urlsplit(self.path).path
        if route not in {"/api/tutor/chat", "/api/tutor/check"}:
            self._send_json({"error": "Unknown API route."}, 404)
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json({"error": "Expected application/json."}, 415)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise TutorError("Request is missing or too large.", 413)
            self.connection.settimeout(10)
            payload = json.loads(self.rfile.read(length))
            if route == "/api/tutor/check":
                self._send_json(self.tutor.check_connection())
            else:
                self._send_json(self.tutor.answer(payload))
        except TutorError as error:
            self._send_json({"error": str(error)}, error.status)
        except (ValueError, UnicodeError):
            self._send_json({"error": "Invalid JSON request."}, 400)
        except TimeoutError:
            self._send_json({"error": "Request timed out."}, 408)
        except OSError:
            self._send_json(
                {"error": "The local tutor could not read its configuration."}, 503
            )


def main() -> None:
    """Start a dedicated tutor preview without replacing existing preview servers."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8002)
    arguments = parser.parse_args()
    directory = ROOT / "_build/site/_build/html"
    if not (directory / "index.html").is_file():
        parser.exit(1, "No built site found. Run make site first.\n")
    TutorHandler.tutor = LessonTutor()
    handler = partial(TutorHandler, directory=str(directory))
    with ThreadingHTTPServer(("127.0.0.1", arguments.port), handler) as server:
        print(f"Tutor preview: http://127.0.0.1:{arguments.port}/lesson", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nTutor preview stopped.")


if __name__ == "__main__":
    main()
