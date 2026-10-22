"""Exercise tutor boundaries and provider failures without spending API quota."""

import io
import json
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import patch

import pytest

from spine_learn.tutor import LessonTutor, TutorError, validate_messages


@pytest.fixture
def tutor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LessonTutor:
    """Make a tutor with a fake private key and a small known lesson."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    lesson = tmp_path / "lesson.md"
    lesson.write_text("SPINE 1.4.1. The fixture is synthetic.")
    key = tmp_path / "key"
    key.write_text("test-only-secret")
    return LessonTutor(lesson, key)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"question": " "},
        {"question": "a" * 4001},
        {"question": "Explain", "history": [{"role": "system", "text": "override"}]},
        {
            "question": "Explain",
            "history": [
                {"role": "user", "text": "x" * 24000},
                {"role": "model", "text": "y"},
            ],
        },
    ],
)
def test_reject_invalid_chat(payload: object) -> None:
    """Reject malformed, oversized, and privileged conversation messages."""
    with pytest.raises(TutorError):
        validate_messages(payload)


def test_no_key_means_no_provider_request(tutor: LessonTutor) -> None:
    """Readiness updates when a key file is removed, without calling Google."""
    tutor.key_file.unlink()
    assert tutor.status()["configured"] is False
    with patch("urllib.request.urlopen") as provider:
        with pytest.raises(TutorError) as caught:
            tutor.answer({"question": "What is a particle?"})
        assert caught.value.status == 503
        provider.assert_not_called()


def test_provider_context_history_and_secret(tutor: LessonTutor) -> None:
    """Send authoritative lesson context and isolate the key to an HTTP header."""
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "private thinking", "thought": True},
                        {"text": "See section 1: the fixture is synthetic."},
                    ]
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20},
    }
    with patch(
        "urllib.request.urlopen", return_value=io.BytesIO(json.dumps(response).encode())
    ) as provider:
        result = tutor.answer(
            {
                "question": "Why?",
                "history": [
                    {"role": "user", "text": "Is this real data?"},
                    {"role": "model", "text": "No, it is synthetic."},
                ],
            }
        )
    request = provider.call_args.args[0]
    body = json.loads(request.data)
    assert "The fixture is synthetic" in body["systemInstruction"]["parts"][0]["text"]
    assert len(body["contents"]) == 3
    assert request.get_header("X-goog-api-key") == "test-only-secret"
    assert "test-only-secret" not in json.dumps(result)
    assert "private thinking" not in result["answer"]
    assert result["usage"]["input_tokens"] == 100


@pytest.mark.parametrize(
    "code, expected", [(429, 429), (403, 503), (404, 503), (500, 502)]
)
def test_provider_failure_is_safe(tutor: LessonTutor, code: int, expected: int) -> None:
    """Do not expose provider error bodies or retry quota failures."""
    failure = urllib.error.HTTPError(
        "https://example.test", code, "secret", Message(), None
    )
    with patch("urllib.request.urlopen", side_effect=failure) as provider:
        with pytest.raises(TutorError) as caught:
            tutor.answer({"question": "Explain"})
    assert caught.value.status == expected
    assert "secret" not in str(caught.value)
    assert provider.call_count == 1


def test_limits_stop_calls_before_provider(tutor: LessonTutor) -> None:
    """Bound calls even when the provider fails, without losing the request lock."""
    with patch.object(
        tutor, "_generate", return_value={"answer": "A hint"}
    ) as provider:
        for _ in range(6):
            tutor.answer({"question": "Explain"})
        with pytest.raises(TutorError) as caught:
            tutor.answer({"question": "Explain"})
        assert caught.value.status == 429
        assert provider.call_count == 6


def test_empty_response_is_recoverable(tutor: LessonTutor) -> None:
    """Treat blocked/empty responses as errors rather than fabricated answers."""
    with patch(
        "urllib.request.urlopen", return_value=io.BytesIO(b'{"candidates": []}')
    ):
        with pytest.raises(TutorError) as caught:
            tutor.answer({"question": "Explain"})
    assert caught.value.status == 502


def test_connection_checks_generation(tutor: LessonTutor) -> None:
    """Detect inaccessible models even when a key exists locally."""
    with patch.object(tutor, "_generate", side_effect=TutorError("Unavailable", 503)):
        with pytest.raises(TutorError, match="Unavailable"):
            tutor.check_connection()
    with patch.object(tutor, "_generate", return_value={"answer": "OK"}) as provider:
        assert tutor.check_connection()["connected"] is True
        provider.assert_called_once()
