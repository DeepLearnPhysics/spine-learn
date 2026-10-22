"""Exercise tutor boundaries and provider failures without spending API quota."""

import io
import json
import time
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
    "code, expected", [(400, 503), (401, 503), (429, 429), (403, 503), (404, 503)]
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


@pytest.mark.parametrize("code", [500, 502, 503, 504])
def test_transient_error_recovers_once(tutor: LessonTutor, code: int) -> None:
    """A transient failure is hidden if the one allowed retry succeeds."""
    failure = urllib.error.HTTPError(
        "https://example.test", code, "secret", Message(), None
    )
    reply = io.BytesIO(b'{"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}')
    with (
        patch("urllib.request.urlopen", side_effect=[failure, reply]) as provider,
        patch("spine_learn.tutor.time.sleep") as sleep,
    ):
        assert tutor.check_connection()["connected"] is True
    assert provider.call_count == 2
    assert provider.call_args_list[0].args == provider.call_args_list[1].args
    sleep.assert_called_once_with(1.0)
    assert tutor._daily_count == 2
    assert not tutor._lock.locked()


def test_persistent_transient_error_stops(tutor: LessonTutor) -> None:
    """Repeated failures stop after two attempts and release the request lock."""
    failure = urllib.error.HTTPError(
        "https://example.test", 503, "secret", Message(), None
    )
    with (
        patch("urllib.request.urlopen", side_effect=failure) as provider,
        patch("spine_learn.tutor.time.sleep") as sleep,
    ):
        with pytest.raises(TutorError) as caught:
            tutor.answer({"question": "Explain"})
    assert caught.value.status == 502
    assert "secret" not in str(caught.value)
    assert provider.call_count == 2
    sleep.assert_called_once()
    assert not tutor._lock.locked()


@pytest.mark.parametrize("limit", ["minute", "day"])
def test_retry_respects_remaining_quota(tutor: LessonTutor, limit: str) -> None:
    """The retry cannot bypass either local provider-attempt allowance."""
    if limit == "minute":
        tutor._requests.extend([time.monotonic()] * 5)
    else:
        tutor._day = time.strftime("%Y-%m-%d", time.gmtime())
        tutor._daily_count = 199
    failure = urllib.error.HTTPError(
        "https://example.test", 503, "secret", Message(), None
    )
    with (
        patch("urllib.request.urlopen", side_effect=failure) as provider,
        patch("spine_learn.tutor.time.sleep"),
    ):
        with pytest.raises(TutorError) as caught:
            tutor.answer({"question": "Explain"})
    assert caught.value.status == 429
    assert provider.call_count == 1
    assert not tutor._lock.locked()


@pytest.mark.parametrize("elapsed", [10.0, 44.5])
def test_retry_uses_remaining_timeout(tutor: LessonTutor, elapsed: float) -> None:
    """A retry does not reset the timeout or start after the budget is spent."""
    clock = [100.0]
    calls = []

    def provider(request, timeout):
        """Advance a fake clock before reporting the first attempt's failure."""
        calls.append(timeout)
        if len(calls) == 1:
            clock[0] += elapsed
            raise urllib.error.HTTPError(
                "https://example.test", 503, "secret", Message(), None
            )
        return io.BytesIO(b'{"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}')

    def sleep(delay):
        """Advance the fake clock without making the test wait."""
        clock[0] += delay

    with (
        patch("urllib.request.urlopen", side_effect=provider),
        patch("spine_learn.tutor.time.monotonic", side_effect=lambda: clock[0]),
        patch("spine_learn.tutor.time.sleep", side_effect=sleep),
    ):
        if elapsed == 10.0:
            assert tutor.answer({"question": "Explain"})["answer"] == "OK"
            assert calls == [45.0, 34.0]
        else:
            with pytest.raises(TutorError):
                tutor.answer({"question": "Explain"})
            assert calls == [45.0]


def test_timeout_does_not_duplicate_generation(tutor: LessonTutor) -> None:
    """A lost response may still be generating upstream, so do not resend it."""
    with patch("urllib.request.urlopen", side_effect=TimeoutError) as provider:
        with pytest.raises(TutorError) as caught:
            tutor.answer({"question": "Explain"})
    assert caught.value.status == 504
    provider.assert_called_once()
