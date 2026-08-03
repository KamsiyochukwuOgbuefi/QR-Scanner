"""
routes.py

All HTTP endpoints for the web QR scanner. Thin request/response layer
that delegates to services.py (which wraps the existing core modules).
"""

import os
import tempfile

import cv2
from flask import Blueprint, Response, jsonify, render_template, request

from core.detector import ImageLoadError, QRDetector
from services import services

routes_bp = Blueprint("main", __name__)

MJPEG_MIMETYPE = "multipart/x-mixed-replace; boundary=frame"


# ------------------------------------------------------------------ #
# Pages
# ------------------------------------------------------------------ #

@routes_bp.get("/")
def index():
    # Note: camera availability is fetched asynchronously by the frontend
    # (/api/camera/list); probing here would block page load on machines
    # whose camera driver makes cv2.VideoCapture() hang.
    return render_template("index.html")


# ------------------------------------------------------------------ #
# Image scanning
# ------------------------------------------------------------------ #

@routes_bp.post("/scan")
def scan_upload():
    """Process an uploaded image and return any QR codes found."""
    if "image" not in request.files:
        return jsonify(success=False, message="No image file provided."), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify(success=False, message="No image selected."), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in QRDetector.SUPPORTED_EXTENSIONS:
        return jsonify(success=False, message="Unsupported image type."), 400

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        frame = cv2.imread(tmp_path)
        if frame is None:
            return jsonify(success=False, message=f"Could not load image: {file.filename}"), 400
        codes = services.detector.scan_frame(frame)
    except ImageLoadError as exc:
        return jsonify(success=False, message=str(exc)), 400
    except Exception as exc:
        return jsonify(success=False, message=f"Unexpected error while scanning: {exc}"), 500
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    preview = services.annotate_image(frame)
    scans = [services.process_scan(code.data) for code in codes]

    return jsonify(
        success=True,
        count=len(scans),
        scans=scans,
        preview=preview,
    )


# ------------------------------------------------------------------ #
# Camera
# ------------------------------------------------------------------ #

@routes_bp.get("/camera")
def camera_stream():
    return Response(services.camera_stream(), mimetype=MJPEG_MIMETYPE)


@routes_bp.post("/api/camera/start")
def camera_start():
    body = request.get_json(silent=True) or {}
    index = body.get("index")
    return jsonify(services.start_camera(index))


@routes_bp.post("/api/camera/stop")
def camera_stop():
    return jsonify(services.stop_camera())


@routes_bp.post("/api/camera/switch")
def camera_switch():
    return jsonify(services.switch_camera())


@routes_bp.get("/api/camera/status")
def camera_status():
    return jsonify(services.camera_status())


@routes_bp.get("/api/camera/list")
def camera_list():
    return jsonify({"cameras": services.list_cameras()})


@routes_bp.get("/api/camera/events")
def camera_events():
    after = request.args.get("after", "0")
    try:
        after = float(after)
    except ValueError:
        after = 0.0
    return jsonify({"events": services.events_after(after)})


# ------------------------------------------------------------------ #
# History
# ------------------------------------------------------------------ #

@routes_bp.get("/history")
def history_list():
    q = request.args.get("q", "").strip()
    type_filter = request.args.get("type", "").strip()
    sort = request.args.get("sort", "desc").strip()
    limit = request.args.get("limit", type=int, default=100)
    entries = services.list_history(q=q, type_filter=type_filter, sort=sort, limit=limit)
    return jsonify({"entries": entries, "count": len(entries)})


@routes_bp.post("/history/clear")
def history_clear():
    cleared = services.clear_history()
    return jsonify(success=True, message="History cleared.", cleared=cleared)


@routes_bp.post("/history/delete")
def history_delete():
    body = request.get_json(silent=True) or {}
    entry_id = body.get("id", "")
    if not entry_id:
        return jsonify(success=False, message="Missing entry id."), 400
    removed = services.delete_history_entry(entry_id)
    if not removed:
        return jsonify(success=False, message="Entry not found."), 404
    return jsonify(success=True, message="Entry removed.", removed=removed)


# ------------------------------------------------------------------ #
# Export
# ------------------------------------------------------------------ #

@routes_bp.get("/export/txt")
def export_txt():
    if services.history.is_empty():
        return jsonify(success=False, message="Scan history is empty."), 400
    return Response(
        services.history.export_txt_str(),
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=qr_history.txt"},
    )


@routes_bp.get("/export/csv")
def export_csv():
    if services.history.is_empty():
        return jsonify(success=False, message="Scan history is empty."), 400
    return Response(
        services.history.export_csv_str(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=qr_history.csv"},
    )


@routes_bp.get("/export/json")
def export_json():
    if services.history.is_empty():
        return jsonify(success=False, message="Scan history is empty."), 400
    return Response(
        services.history.export_json_str(),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=qr_history.json"},
    )


# ------------------------------------------------------------------ #
# Result actions
# ------------------------------------------------------------------ #

@routes_bp.post("/copy")
def copy_text():
    """API parity endpoint; the browser performs the real clipboard copy."""
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    return jsonify(success=True, message="Copied to clipboard.", text=text)


@routes_bp.post("/open")
def open_content():
    """Prepare a browser action (open URL / download .ics) for raw data."""
    body = request.get_json(silent=True) or {}
    raw = body.get("raw", "")
    if not raw:
        return jsonify(success=False, message="No content provided."), 400
    return jsonify(services.open_action(raw))
