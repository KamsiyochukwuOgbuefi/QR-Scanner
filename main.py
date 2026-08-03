"""
main.py

Entry point for the QR Code Scanner Pro web application.
Run with:  python main.py
"""

import os

from app import create_app

app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, threaded=True)
