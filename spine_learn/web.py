"""Serve the built lessons and bounded Gemini API behind the S3DF HTTPS gateway."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, Response, abort, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from .tutor import LESSON, ROOT, LessonTutor, TutorError


def create_app(
    site_directory: Path | None = None,
    tutor: LessonTutor | None = None,
    public_origin: str | None = None,
) -> Flask:
    """Create the production WSGI application with explicit serving boundaries.

    Only the generated site directory is exposed. The lesson context and API key
    stay outside it. Use one Gunicorn worker and one replica: the tutor's request
    limits and concurrency lock are process-local safeguards, not billing caps.
    """
    site = (
        site_directory
        or Path(os.getenv("SPINE_SITE_DIR", str(ROOT / "_build/site/_build/html")))
    ).resolve()
    origin = public_origin or os.getenv(
        "SPINE_PUBLIC_ORIGIN", "https://spine-learn.slac.stanford.edu"
    )
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "SPINE_PUBLIC_ORIGIN must be an origin without a trailing slash."
        )

    companion = tutor or LessonTutor(Path(os.getenv("SPINE_LESSON", str(LESSON))))
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 65536

    @app.before_request
    def validate_request() -> None:
        """Accept health probes internally and API requests from the configured site."""
        if request.path in {"/healthz", "/readyz"}:
            return
        if request.host != parsed.netloc:
            abort(403, description="Unrecognized website host.")
        if request.path.startswith("/api/"):
            supplied_origin = request.headers.get("Origin")
            if supplied_origin is not None and supplied_origin != origin:
                abort(403, description="Cross-origin API requests are not allowed.")
            if request.headers.get("Sec-Fetch-Site") == "cross-site":
                abort(403, description="Cross-site API requests are not allowed.")

    @app.after_request
    def response_headers(response: Response) -> Response:
        """Prevent API caching and keep embedded controls on the same origin."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.path.startswith("/api/") or request.path in {"/healthz", "/readyz"}:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException) -> tuple[Response, int]:
        """Return readable JSON errors, including malformed or oversized requests."""
        return jsonify(error=error.description), error.code or 500

    @app.errorhandler(TutorError)
    def tutor_error(error: TutorError) -> tuple[Response, int]:
        """Expose only the deliberately sanitized tutor error message."""
        return jsonify(error=str(error)), error.status

    @app.get("/healthz")
    def health() -> Response:
        """Check the worker without consuming Gemini requests."""
        return jsonify(status="ok")

    @app.get("/readyz")
    def ready() -> tuple[Response, int]:
        """Require page and lesson assets without depending on Gemini availability."""
        available = (site / "index.html").is_file() and companion.lesson.is_file()
        return jsonify(ready=available), 200 if available else 503

    @app.get("/api/tutor/status")
    def tutor_status() -> Response:
        """Report configuration, never the key or a live provider request."""
        return jsonify(companion.status())

    @app.post("/api/tutor/chat")
    @app.post("/api/tutor/check")
    def tutor_request() -> Response | tuple[Response, int]:
        """Validate JSON before entering the shared concurrency and request limits."""
        if request.mimetype != "application/json":
            abort(415, description="Expected application/json.")
        payload = request.get_json()
        if not isinstance(payload, dict):
            abort(400, description="Expected a JSON object.")
        try:
            if request.path.endswith("/check"):
                return jsonify(companion.check_connection())
            return jsonify(companion.answer(payload))
        except OSError:
            # Do not expose filesystem paths or provider/configuration details.
            return jsonify(
                error="The lesson assistant is temporarily unavailable."
            ), 503

    @app.get("/", defaults={"asset": ""})
    @app.get("/<path:asset>")
    def static_asset(asset: str) -> Response:
        """Serve static MyST pages with conditional and byte-range audio responses."""
        if asset.startswith("api/") or any(
            part.startswith(".") for part in asset.split("/") if part
        ):
            abort(404)
        candidate = (site / asset).resolve()
        if not candidate.is_relative_to(site):
            abort(404)
        if candidate.is_dir():
            asset = f"{asset.rstrip('/')}/index.html".lstrip("/")
        return send_from_directory(site, asset, conditional=True, max_age=0)

    return app
