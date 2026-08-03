"""
app.py

Main application window. Wires together:
- core.detector   (finding QR codes in images/camera frames)
- core.content_parser (classifying decoded content)
- core.actions    (doing the right thing with that content)
- core.history    (logging + exporting scans)
- gui.widgets     (the visual pieces)

Run via main.py at the project root.
"""

import os
import cv2
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb

import pyperclip

from core.detector import QRDetector, CameraManager, ImageLoadError
from core.content_parser import ContentParser, QRType
from core.actions import ActionHandler
from core.history import HistoryManager
from gui.widgets import StatusIndicator, ResultPanel, HistoryPanel

PREVIEW_W, PREVIEW_H = 480, 360
CAMERA_POLL_MS = 30
# How many consecutive frames without a match before we allow the same
# QR code to trigger its action again (prevents rapid re-triggering while
# a code just sits in front of the camera).
ABSENCE_RESET_FRAMES = 10


class QRScannerApp(tb.Window):
    def __init__(self):
        super().__init__(title="QR Code Scanner Pro", themename="darkly", size=(980, 620), resizable=(True, True))

        self.detector = QRDetector()
        self.camera = CameraManager()
        self.parser = ContentParser()
        self.action_handler = ActionHandler()
        self.history = HistoryManager()

        self._camera_running = False
        self._last_triggered_data: str | None = None
        self._absence_counter = 0
        self._dark_mode = True

        self._build_layout()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _build_layout(self):
        toolbar = tb.Frame(self, padding=10)
        toolbar.pack(fill="x")

        tb.Button(toolbar, text="Upload Image", bootstyle="primary", command=self.upload_image).pack(side="left", padx=(0, 8))
        self.camera_btn = tb.Button(toolbar, text="Start Camera", bootstyle="success", command=self.toggle_camera)
        self.camera_btn.pack(side="left", padx=(0, 8))
        tb.Button(toolbar, text="Toggle Theme", bootstyle="secondary-outline", command=self.toggle_theme).pack(side="left")

        self.status = StatusIndicator(toolbar)
        self.status.pack(side="right")

        main = tb.Frame(self, padding=(10, 0, 10, 10))
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Left: preview
        left = tb.Labelframe(main, text="Preview", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.preview_label = tb.Label(left, text="No image or camera feed yet", anchor="center")
        self.preview_label.pack(fill="both", expand=True)

        # Right: result + history stacked
        right = tb.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self.result_panel = ResultPanel(right, on_copy=self.copy_text, on_save=self.save_result, on_open=self.open_result)
        self.result_panel.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.history_panel = HistoryPanel(right, on_clear=self.clear_history, on_export=self.export_history)
        self.history_panel.grid(row=1, column=0, sticky="nsew")

        self._set_preview_placeholder("No image or camera feed yet")

    # ------------------------------------------------------------------ #
    # Image upload flow
    # ------------------------------------------------------------------ #

    def upload_image(self):
        if self._camera_running:
            self.toggle_camera()  # stop camera before switching to an image

        filetypes = [("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff"), ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Select a QR code image", filetypes=filetypes)
        if not path:
            return

        self.status.set_state("scanning", "Scanning image...")
        try:
            codes = self.detector.scan_image_file(path)
        except ImageLoadError as exc:
            messagebox.showerror("Error", str(exc))
            self.status.set_state("error", "Failed to load image")
            return
        except Exception as exc:
            messagebox.showerror("Error", f"Unexpected error while scanning: {exc}")
            self.status.set_state("error", "Scan error")
            return

        self._show_image_preview(path, codes)

        if not codes:
            messagebox.showinfo("No QR Code Found", "No QR code was detected in that image.")
            self.status.set_state("idle", "No QR code found")
            return

        self.status.set_state("idle", f"Found {len(codes)} QR code(s)")
        # Process each detected code (an image can contain more than one).
        for code in codes:
            self._process_decoded_data(code.data)

    def _show_image_preview(self, path, codes):
        frame = cv2.imread(path)
        if frame is None:
            return
        for code in codes:
            if code.points:
                pts = code.points
                for i in range(len(pts)):
                    cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], (0, 200, 0), 3)
        self._set_preview_frame(frame)

    # ------------------------------------------------------------------ #
    # Camera flow
    # ------------------------------------------------------------------ #

    def toggle_camera(self):
        if self._camera_running:
            self._camera_running = False
            self.camera.close()
            self.camera_btn.configure(text="Start Camera", bootstyle="success")
            self.status.set_state("idle", "Camera stopped")
            self._set_preview_placeholder("No image or camera feed yet")
            return

        available = self.camera.list_available_cameras()
        if not available:
            messagebox.showerror("Camera Unavailable", "No camera was detected on this system.")
            self.status.set_state("error", "No camera found")
            return

        if not self.camera.open(available[0]):
            messagebox.showerror("Camera Error", "Could not open the camera. It may be in use by another app.")
            self.status.set_state("error", "Camera error")
            return

        self._camera_running = True
        self._last_triggered_data = None
        self._absence_counter = 0
        self.camera_btn.configure(text="Stop Camera", bootstyle="danger")
        self.status.set_state("scanning", "Camera scanning...")
        self._camera_loop()

    def _camera_loop(self):
        if not self._camera_running:
            return

        success, frame = self.camera.read_frame()
        if success and frame is not None:
            try:
                codes = self.detector.scan_frame(frame)
            except Exception:
                codes = []

            if codes:
                self._absence_counter = 0
                for code in codes:
                    if code.points:
                        pts = code.points
                        for i in range(len(pts)):
                            cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], (0, 200, 0), 3)

                newest = codes[0].data
                if newest != self._last_triggered_data:
                    self._last_triggered_data = newest
                    self._process_decoded_data(newest)
            else:
                self._absence_counter += 1
                if self._absence_counter > ABSENCE_RESET_FRAMES:
                    self._last_triggered_data = None

            self._set_preview_frame(frame)

        self.after(CAMERA_POLL_MS, self._camera_loop)

    # ------------------------------------------------------------------ #
    # Shared decode -> parse -> action -> history -> display pipeline
    # ------------------------------------------------------------------ #

    def _process_decoded_data(self, raw_data: str):
        content = self.parser.parse(raw_data)
        result = self.action_handler.perform(content)
        self.history.add(content, result.message)
        self.history_panel.add_row(self.history.all()[-1].timestamp, content.qr_type.value, content.display_text)

        can_open = content.qr_type in (QRType.URL, QRType.EMAIL, QRType.GEO, QRType.CALENDAR_EVENT)
        self.result_panel.show(content, result.message, can_open)

    # ------------------------------------------------------------------ #
    # Result panel callbacks
    # ------------------------------------------------------------------ #

    def copy_text(self, text: str):
        try:
            pyperclip.copy(text)
            self.status.set_state("idle", "Copied to clipboard")
        except Exception as exc:
            messagebox.showerror("Copy Failed", str(exc))

    def save_result(self, content):
        path = filedialog.asksaveasfilename(
            title="Save Result",
            defaultextension=".txt",
            filetypes=[("Text file", "*.txt")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.raw)
        self.status.set_state("idle", "Result saved")

    def open_result(self, content):
        result = self.action_handler.perform(content)
        self.status.set_state("idle", result.message)

    # ------------------------------------------------------------------ #
    # History panel callbacks
    # ------------------------------------------------------------------ #

    def clear_history(self):
        if self.history.is_empty():
            return
        if messagebox.askyesno("Clear History", "Remove all scan history?"):
            self.history.clear()
            self.history_panel.clear_rows()

    def export_history(self, fmt: str):
        if self.history.is_empty():
            messagebox.showinfo("Nothing to Export", "Scan history is empty.")
            return

        ext_map = {"txt": ".txt", "csv": ".csv", "json": ".json"}
        path = filedialog.asksaveasfilename(
            title=f"Export History as {fmt.upper()}",
            defaultextension=ext_map[fmt],
            filetypes=[(f"{fmt.upper()} file", f"*{ext_map[fmt]}")],
        )
        if not path:
            return

        try:
            {"txt": self.history.export_txt, "csv": self.history.export_csv, "json": self.history.export_json}[fmt](path)
            self.status.set_state("idle", f"History exported to {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    # ------------------------------------------------------------------ #
    # Preview helpers
    # ------------------------------------------------------------------ #

    def _set_preview_frame(self, bgr_frame):
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail((PREVIEW_W, PREVIEW_H))
        photo = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=photo, text="")
        self.preview_label.image = photo  # keep a reference to avoid garbage collection

    def _set_preview_placeholder(self, text):
        self.preview_label.configure(image="", text=text)
        self.preview_label.image = None

    def toggle_theme(self):
        self._dark_mode = not self._dark_mode
        self.style.theme_use("darkly" if self._dark_mode else "flatly")

    def on_close(self):
        self.camera.close()
        self.destroy()
