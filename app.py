"""
app.py

Entry point for the QR Code Scanner Pro web application (Flask).
Run with:  python app.py   (or  python main.py)
"""

import os

from flask import Flask

from routes import routes_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload cap
    app.config["JSON_SORT_KEYS"] = False
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
