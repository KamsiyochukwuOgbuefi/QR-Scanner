"""
app.py

Entry point for the QR Code Scanner Pro web application (Flask).
Run with:  python app.py   (or  python main.py)
"""

import logging
import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from routes import routes_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload cap
    app.config["JSON_SORT_KEYS"] = False

    # Forward Flask logs to gunicorn's logger so they appear in the
    # Render dashboard logs when running under gunicorn.
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level if gunicorn_logger.handlers else logging.INFO)

    @app.errorhandler(Exception)
    def handle_unhandled(exc):
        # Let Werkzeug HTTP errors (404, 405, 413...) pass through.
        if isinstance(exc, HTTPException):
            return exc
        app.logger.error("Unhandled exception", exc_info=exc)
        try:
            return jsonify(success=False, message=f"Server error: {exc}"), 500
        except Exception:
            return jsonify(success=False, message="Server error"), 500

    app.register_blueprint(routes_bp)
    return app


app = create_app()


if __name__ == "__main__":
    # debug=False avoids the reloader spawning a second process, which
    # would fight over the webcam and duplicate the history singleton.
    # Host/port come from the environment (Render assigns PORT).
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False, threaded=True)
