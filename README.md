# QR Code Scanner Pro

A full-featured QR code scanner with both a **modern web app** and the
original **desktop GUI**. Scans QR codes from images or a live webcam feed,
automatically recognizes what kind of content it holds, and performs the
right action. Both frontends reuse the exact same `core/` scanning, parsing,
action, and history logic.

## Features

- **Universal content support**: URLs, plain text, email (`mailto:`), phone
  numbers (`tel:`), SMS (`sms:`/`smsto:`), Wi-Fi credentials (`WIFI:`), GPS
  coordinates (`geo:`), calendar events (`VEVENT`), contact cards
  (`VCARD`/`MECARD`), and cryptocurrency addresses (`bitcoin:`, `ethereum:`, etc.)
- **Smart actions**: opens URLs/maps/mail client automatically, generates
  `.ics` files for calendar events, and surfaces copy-ready text for
  everything else (Wi-Fi passwords, phone numbers, crypto addresses...)
- **Image scanning**: supports PNG, JPG, JPEG, BMP, GIF, WebP, TIFF, and
  detects multiple QR codes in a single image
- **Live camera scanning**: real-time detection with a green bounding box
  around detected codes, and duplicate-scan prevention (a code won't
  re-trigger its action until it disappears and reappears)
- **Web app**: browser UI served by Flask with live MJPEG camera streaming,
  drag-and-drop upload, scan history with search/filter/sort, one-click
  copy/open, and TXT/CSV/JSON export
- **Desktop GUI**: ttkbootstrap window with dark/light theme toggle, scan
  history table, and TXT/CSV/JSON export

## Project Structure

```
qr_scanner/
├── main.py                 # Web entry point - python main.py
├── app.py                  # Flask app factory (registers the routes blueprint)
├── routes.py               # HTTP endpoints (thin layer over services.py)
├── services.py             # Web orchestration: camera loop, persistence, actions
├── templates/
│   └── index.html          # Single-page frontend
├── static/
│   ├── css/style.css       # Theme + layout
│   ├── js/app.js           # Camera, upload, history, copy/open/save logic
│   └── images/             # favicon + logo
├── requirements.txt
├── core/
│   ├── detector.py         # Image + camera QR detection (pyzbar/OpenCV)
│   ├── content_parser.py   # Classifies raw decoded text into a QRType
│   ├── actions.py          # Performs the right real-world action per type
│   └── history.py          # Scan history log + TXT/CSV/JSON export
├── gui/                    # Original desktop GUI (kept)
│   ├── app.py              # Main window, wires everything together
│   └── widgets.py          # ResultPanel, HistoryPanel, StatusIndicator
├── utils/
│   └── helpers.py          # Small shared helpers
└── data/                   # Runtime history.json persistence (created on use)
```

## Module Overview

- **`core/detector.py`** — `QRDetector` reads an image file or a single
  camera frame and returns every QR code found (data + bounding polygon),
  using `pyzbar` for decoding. `CameraManager` wraps `cv2.VideoCapture` with
  simple open/read/close methods and camera discovery.
- **`core/content_parser.py`** — `ContentParser.parse()` takes the raw
  decoded string and tries each known format (Wi-Fi, vCard, MECARD, mailto,
  tel, sms, geo, crypto URI schemes, calendar, then generic URL) until one
  matches, returning a structured `QRContent` object. Anything that matches
  nothing becomes plain `TEXT`.
- **`core/actions.py`** — `ActionHandler.perform()` looks at a `QRContent`'s
  type and does the appropriate thing (open browser, open mail client, open
  Maps, write + open an `.ics` file, or just prepare text for copying).
- **`core/history.py`** — `HistoryManager` stores a list of scans and can
  dump them to `.txt`, `.csv`, or `.json`. The web layer persists it to
  `data/history.json` so history survives restarts.
- **`services.py`** — `QRScannerService` bridges the browser to `core/`:
  the decode → parse → action → history pipeline, the live camera
  detection loop with duplicate suppression, MJPEG streaming, annotated
  image previews, and disk persistence.
- **`routes.py`** — All HTTP endpoints: `GET /`, `POST /scan`,
  `GET /camera` (MJPEG stream), `POST /api/camera/start|stop|switch`,
  `GET /api/camera/status|list|events`, `GET /history`,
  `POST /history/clear|delete`, `GET /export/txt|csv|json`,
  `POST /copy`, `POST /open`.
- **`gui/widgets.py`** — `StatusIndicator` (idle/scanning/error dot),
  `ResultPanel` (type-aware formatted display with Copy/Save/Open buttons),
  and `HistoryPanel` (Treeview table with Clear/Export).
- **`gui/app.py`** — `QRScannerApp` (a `ttkbootstrap.Window`) builds the
  layout and connects image upload, the camera polling loop, and all button
  callbacks to the `core` modules above.

## Installation

1. Make sure you have **Python 3.11+** installed.
2. (Recommended) create a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   > **Windows note:** `pyzbar` needs the Visual C++ Redistributable for
   > Visual Studio 2013, which most systems already have. If you get a
   > `zbar shared library not found` error, download and install it from
   > Microsoft, then retry.
   >
   > **Linux note:** you may need the system zbar library:
   > `sudo apt install libzbar0`

## Running the Web App

From the project root:

```bash
python main.py
```

Then open **http://127.0.0.1:5000** in your browser.

- **Start Camera** — begins live scanning from your webcam. The feed
  streams into the page and detected codes pop up as scan results with
  green bounding boxes drawn server-side.
- **Upload Image** — pick or drag-and-drop an image file to scan (multiple
  QR codes in one image are supported).
- **Copy / Open / Save** — copy the raw content (or the useful part, like
  a Wi-Fi password), open URLs / email drafts / map locations / download
  calendar `.ics` files, or save the result to a `.txt` file.
- Every scan is logged in **Scan History** with search, type filter, and
  sort. Clear individual entries, clear all, or export to TXT/CSV/JSON.
- History is persisted to `data/history.json` and restored on the next start.

Override the address/port with environment variables if needed:

```bash
HOST=0.0.0.0 PORT=8080 python main.py
```

## Running the Desktop GUI (legacy)

```bash
python -m gui.app
```

- **Upload Image** — pick an image file to scan.
- **Start Camera** — begin live scanning from your default webcam (click
  again to stop).
- **Toggle Theme** — switch between dark and light mode.
- Results appear in the **Result** panel on the right, with buttons to
  **Copy**, **Save Result** to a `.txt` file, or **Open** (for URLs, email,
  maps, calendar events).
- Every scan is logged in **Scan History**, which you can clear or export
  to TXT/CSV/JSON.

## Known Limitations

- SMS and phone actions can't dial/text directly from a desktop OS — the
  app surfaces the number/message so you can copy it to your phone.
- Calendar events are handled by generating an `.ics` file and opening it
  with your system's default calendar app.
- Camera scanning uses whatever webcam OpenCV finds first; use the switch
  button to cycle through multiple cameras.
