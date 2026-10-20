"""Check local HTTP access boundaries without any live Gemini calls."""

import json
import threading
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from scripts.serve_tutor import TutorHandler
from spine_learn.tutor import LessonTutor


def test_local_api_boundaries(tmp_path: Path) -> None:
    """Reject cross-origin calls, oversized input, and secret-file requests."""
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("Public preview")
    key_file = tmp_path / ".gemini-api-key"
    key_file.write_text("test-secret")
    lesson = tmp_path / "lesson.md"
    lesson.write_text("Synthetic lesson")
    tutor = LessonTutor(lesson, key_file)

    class Handler(TutorHandler):
        """Isolate this test's tutor from other server instances."""

    Handler.tutor = tutor
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Handler, directory=str(site))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        with patch.object(tutor, "answer", return_value={"answer": "A hint"}) as answer:
            connection.request("GET", "/api/tutor/status")
            response = connection.getresponse()
            assert response.status == 200
            assert b"test-secret" not in response.read()

            connection.request(
                "POST",
                "/api/tutor/chat",
                body='{"question":"Hi"}',
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://foreign.example",
                },
            )
            response = connection.getresponse()
            assert response.status == 403
            response.read()
            answer.assert_not_called()

            connection.request(
                "POST",
                "/api/tutor/chat",
                body='{"question":"Hi"}',
                headers={"Content-Type": "application/json", "Host": "foreign.example"},
            )
            response = connection.getresponse()
            assert response.status == 403
            response.read()
            answer.assert_not_called()

            connection.request(
                "POST",
                "/api/tutor/chat",
                body="x" * 65537,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            assert response.status == 413
            response.read()
            answer.assert_not_called()

            connection.request("GET", "/../.gemini-api-key")
            response = connection.getresponse()
            assert response.status == 404
            assert b"test-secret" not in response.read()

            connection.request(
                "POST",
                "/api/tutor/chat",
                body='{"question":"Hi"}',
                headers={
                    "Content-Type": "application/json",
                    "Origin": f"http://127.0.0.1:{server.server_port}",
                },
            )
            response = connection.getresponse()
            assert response.status == 200
            assert json.loads(response.read())["answer"] == "A hint"
            answer.assert_called_once()

            # A connection test must exercise generation, not just key presence.
            answer.reset_mock()
            connection.request(
                "POST",
                "/api/tutor/check",
                body="{}",
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            assert response.status == 200
            assert json.loads(response.read())["connected"] is True
            answer.assert_called_once()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join()
