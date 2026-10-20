"""Exercise the hosted API and static-file boundaries without live Gemini calls."""

from pathlib import Path
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

from spine_learn.tutor import LessonTutor, TutorError
from spine_learn.web import create_app

ORIGIN = "https://spine-learn.slac.stanford.edu"


@pytest.fixture
def hosted(tmp_path: Path) -> tuple[FlaskClient, LessonTutor]:
    """Keep public assets, private lesson context, and credentials separate."""
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("Welcome")
    (site / "lesson").mkdir()
    (site / "lesson/index.html").write_text("Lesson")
    (site / "audio.wav").write_bytes(bytes(range(256)))
    lesson = tmp_path / "lesson.md"
    lesson.write_text("Private source context")
    key = tmp_path / ".gemini-api-key"
    key.write_text("secret-test-value")
    tutor = LessonTutor(lesson, key)
    app = create_app(site, tutor, ORIGIN)
    return app.test_client(), tutor


def test_static_pages_ranges_and_probes(
    hosted: tuple[FlaskClient, LessonTutor],
) -> None:
    """Allow kubelet probes and audio seeks while refusing files outside the site."""
    client, _ = hosted
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    assert client.get("/", base_url=ORIGIN).data == b"Welcome"
    assert client.get("/lesson", base_url=ORIGIN).data == b"Lesson"
    response = client.get(
        "/audio.wav", base_url=ORIGIN, headers={"Range": "bytes=20-39"}
    )
    assert response.status_code == 206
    assert response.data == bytes(range(20, 40))
    assert response.headers["Content-Range"] == "bytes 20-39/256"
    assert (
        client.get(
            "/audio.wav", base_url=ORIGIN, headers={"Range": "bytes=900-"}
        ).status_code
        == 416
    )
    for path in (
        "/../.gemini-api-key",
        "/%2e%2e/lesson.md",
        "/.gemini-api-key",
        "/api/unknown",
    ):
        response = client.get(path, base_url=ORIGIN)
        assert response.status_code == 404
        assert b"secret-test-value" not in response.data
    assert client.get("/", base_url="https://other.example").status_code == 403


def test_api_validation_and_origin(hosted: tuple[FlaskClient, LessonTutor]) -> None:
    """Reject malformed requests before any provider call, but permit same-site chat."""
    client, tutor = hosted
    with patch.object(tutor, "answer", return_value={"answer": "A hint"}) as answer:
        for headers in (
            {"Origin": "https://other.example"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            response = client.post(
                "/api/tutor/chat",
                base_url=ORIGIN,
                json={"question": "Hi"},
                headers=headers,
            )
            assert response.status_code == 403
        assert (
            client.post("/api/tutor/chat", base_url=ORIGIN, data="text").status_code
            == 415
        )
        assert (
            client.post(
                "/api/tutor/chat",
                base_url=ORIGIN,
                data="{",
                content_type="application/json",
            ).status_code
            == 400
        )
        assert (
            client.post("/api/tutor/chat", base_url=ORIGIN, json=[]).status_code == 400
        )
        assert (
            client.post(
                "/api/tutor/chat", base_url=ORIGIN, json={"question": "a" * 65536}
            ).status_code
            == 413
        )
        answer.assert_not_called()
        response = client.post(
            "/api/tutor/chat",
            base_url=ORIGIN,
            json={"question": "Hi"},
            headers={"Origin": ORIGIN},
        )
        assert response.json == {"answer": "A hint"}
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers.get("Access-Control-Allow-Origin") is None
        answer.assert_called_once()


def test_status_errors_and_limits(hosted: tuple[FlaskClient, LessonTutor]) -> None:
    """Keep status free of credentials and preserve the shared tutor's rate limit."""
    client, tutor = hosted
    response = client.get("/api/tutor/status", base_url=ORIGIN)
    assert response.json is not None
    assert response.json["configured"]
    assert b"secret-test-value" not in response.data
    with patch.object(tutor, "_generate", return_value={"answer": "OK"}) as generate:
        for _ in range(6):
            assert (
                client.post("/api/tutor/check", base_url=ORIGIN, json={}).status_code
                == 200
            )
        assert (
            client.post(
                "/api/tutor/chat", base_url=ORIGIN, json={"question": "Hi"}
            ).status_code
            == 429
        )
        assert generate.call_count == 6
    with patch.object(tutor, "answer", side_effect=TutorError("Unavailable", 503)):
        assert (
            client.post(
                "/api/tutor/chat", base_url=ORIGIN, json={"question": "Hi"}
            ).status_code
            == 503
        )
