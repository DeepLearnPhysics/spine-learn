"""Verify the HTTP range behavior required by the browser's audio seek control."""

import threading
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from scripts.serve_site import PreviewHandler


def test_media_byte_ranges(tmp_path: Path) -> None:
    """Serve exact bounded, open-ended, and suffix ranges without losing full GETs."""
    data = bytes(range(256)) * 4
    (tmp_path / "audio.wav").write_bytes(data)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(PreviewHandler, directory=str(tmp_path))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        cases = [
            ("bytes=100-199", 206, data[100:200], "bytes 100-199/1024"),
            ("bytes=900-", 206, data[900:], "bytes 900-1023/1024"),
            ("bytes=-24", 206, data[-24:], "bytes 1000-1023/1024"),
            ("bytes=1000-9999", 206, data[1000:], "bytes 1000-1023/1024"),
            ("bytes=2048-", 416, b"", "bytes */1024"),
            ("bytes=-0", 416, b"", "bytes */1024"),
            ("bytes=20-10", 416, b"", "bytes */1024"),
            ("invalid", 200, data, None),
            ("bytes=0-1,5-6", 200, data, None),
            ("", 200, data, None),
        ]
        for requested, status, expected, content_range in cases:
            connection.request("GET", "/audio.wav", headers={"Range": requested})
            response = connection.getresponse()
            assert response.status == status
            assert response.getheader("Accept-Ranges") == "bytes"
            assert response.getheader("Content-Range") == content_range
            assert int(response.getheader("Content-Length", "0")) == len(expected)
            assert response.read() == expected

        connection.request("HEAD", "/audio.wav")
        response = connection.getresponse()
        assert response.status == 200
        assert response.getheader("Content-Length") == str(len(data))
        assert response.read() == b""
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join()
