"""
widgets.py

Reusable, self-contained GUI pieces used by the main app window:
- StatusIndicator: small colored dot + label showing scanner state.
- ResultPanel: displays the decoded QR content with type-aware formatting
  and Copy / Save / Open buttons.
- HistoryPanel: a scrollable table of past scans with clear/export controls.
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb

from core.content_parser import QRContent, QRType


class StatusIndicator(tb.Frame):
    """A colored dot + text label showing whether the scanner is idle,
    scanning, or has hit an error."""

    COLORS = {
        "idle": "secondary",
        "scanning": "success",
        "error": "danger",
    }

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._dot = tb.Label(self, text="\u25CF", bootstyle="secondary", font=("Segoe UI", 12))
        self._dot.pack(side="left", padx=(0, 4))
        self._text = tb.Label(self, text="Idle")
        self._text.pack(side="left")

    def set_state(self, state: str, text: str | None = None):
        style = self.COLORS.get(state, "secondary")
        self._dot.configure(bootstyle=style)
        self._text.configure(text=text or state.capitalize())


class ResultPanel(tb.Labelframe):
    """Shows the most recently decoded QR content, formatted based on type,
    with Copy / Save / Open actions wired up via callbacks."""

    def __init__(self, master, on_copy, on_save, on_open, **kwargs):
        super().__init__(master, text="Result", padding=12, **kwargs)
        self._on_copy = on_copy
        self._on_save = on_save
        self._on_open = on_open
        self._current_content: QRContent | None = None
        self._current_copy_text: str = ""

        self.type_badge = tb.Label(self, text="No scan yet", font=("Segoe UI", 11, "bold"), bootstyle="secondary")
        self.type_badge.pack(anchor="w", pady=(0, 6))

        self.text_box = tk.Text(self, height=10, wrap="word", relief="flat")
        self.text_box.pack(fill="both", expand=True)
        self.text_box.configure(state="disabled")

        btn_row = tb.Frame(self)
        btn_row.pack(fill="x", pady=(8, 0))

        self.copy_btn = tb.Button(btn_row, text="Copy", bootstyle="secondary-outline", command=self._copy, state="disabled")
        self.copy_btn.pack(side="left", padx=(0, 6))

        self.save_btn = tb.Button(btn_row, text="Save Result", bootstyle="secondary-outline", command=self._save, state="disabled")
        self.save_btn.pack(side="left", padx=(0, 6))

        self.open_btn = tb.Button(btn_row, text="Open", bootstyle="success-outline", command=self._open, state="disabled")
        self.open_btn.pack(side="left")

    def show(self, content: QRContent, action_message: str, can_open: bool):
        """Render a QRContent object into the panel."""
        self._current_content = content
        self.type_badge.configure(text=content.qr_type.value, bootstyle="info")

        body = self._format_body(content) + f"\n\n({action_message})"
        self._current_copy_text = self._format_copy_text(content)

        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", body)
        self.text_box.configure(state="disabled")

        self.copy_btn.configure(state="normal")
        self.save_btn.configure(state="normal")
        self.open_btn.configure(state="normal" if can_open else "disabled")

    def _format_body(self, content: QRContent) -> str:
        """Type-specific readable formatting for the text box."""
        f = content.fields
        if content.qr_type == QRType.WIFI:
            return (f"Network (SSID): {f.get('ssid')}\n"
                    f"Password: {f.get('password')}\n"
                    f"Security: {f.get('encryption')}\n"
                    f"Hidden: {'Yes' if f.get('hidden') else 'No'}")
        if content.qr_type == QRType.CONTACT:
            lines = [f"Name: {f.get('name', '')}"]
            if f.get("phone"):
                lines.append(f"Phone: {f['phone']}")
            if f.get("email"):
                lines.append(f"Email: {f['email']}")
            if f.get("org"):
                lines.append(f"Organization: {f['org']}")
            return "\n".join(lines)
        if content.qr_type == QRType.CALENDAR_EVENT:
            return (f"Event: {f.get('summary', '')}\n"
                    f"Start: {f.get('start', '')}\n"
                    f"End: {f.get('end', '')}\n"
                    f"Location: {f.get('location', '')}\n"
                    f"Details: {f.get('description', '')}")
        if content.qr_type == QRType.GEO:
            return f"Latitude: {f.get('lat')}\nLongitude: {f.get('lon')}"
        if content.qr_type == QRType.CRYPTO:
            return f"Currency: {f.get('currency', '').capitalize()}\nAddress: {f.get('address')}\nAmount: {f.get('amount') or 'Not specified'}"
        if content.qr_type == QRType.EMAIL:
            return f"To: {f.get('address')}\nSubject: {f.get('subject') or '(none)'}\nBody: {f.get('body') or '(none)'}"
        if content.qr_type == QRType.SMS:
            return f"Number: {f.get('number')}\nMessage: {f.get('message') or '(none)'}"
        if content.qr_type == QRType.PHONE:
            return f"Phone Number: {f.get('number')}"
        # URL, TEXT, UNKNOWN fall back to raw content
        return content.display_text or content.raw

    def _format_copy_text(self, content: QRContent) -> str:
        """What gets copied to the clipboard for this content type."""
        f = content.fields
        if content.qr_type == QRType.WIFI:
            return f.get("password", "")
        if content.qr_type == QRType.CRYPTO:
            return f.get("address", "")
        if content.qr_type == QRType.GEO:
            return f"{f.get('lat')}, {f.get('lon')}"
        return content.raw

    def _copy(self):
        if self._current_content:
            self._on_copy(self._current_copy_text)

    def _save(self):
        if self._current_content:
            self._on_save(self._current_content)

    def _open(self):
        if self._current_content:
            self._on_open(self._current_content)


class HistoryPanel(tb.Labelframe):
    """Scrollable table of past scans, with Clear and Export controls."""

    def __init__(self, master, on_clear, on_export, **kwargs):
        super().__init__(master, text="Scan History", padding=12, **kwargs)
        self._on_clear = on_clear
        self._on_export = on_export

        columns = ("time", "type", "summary")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=8)
        self.tree.heading("time", text="Time")
        self.tree.heading("type", text="Type")
        self.tree.heading("summary", text="Summary")
        self.tree.column("time", width=130, anchor="w")
        self.tree.column("type", width=110, anchor="w")
        self.tree.column("summary", width=260, anchor="w")
        self.tree.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")

        btn_row = tb.Frame(self)
        btn_row.pack(fill="x", pady=(8, 0))

        tb.Button(btn_row, text="Clear History", bootstyle="danger-outline", command=self._on_clear).pack(side="left")

        self.export_var = tk.StringVar(value="Export...")
        export_menu = tb.Menubutton(btn_row, text="Export", bootstyle="secondary-outline")
        menu = tk.Menu(export_menu, tearoff=False)
        for fmt in ("TXT", "CSV", "JSON"):
            menu.add_command(label=fmt, command=lambda f=fmt: self._on_export(f.lower()))
        export_menu["menu"] = menu
        export_menu.pack(side="right")

    def add_row(self, timestamp: str, qr_type: str, summary: str):
        display_summary = summary if len(summary) <= 60 else summary[:57] + "..."
        self.tree.insert("", "end", values=(timestamp, qr_type, display_summary))
        children = self.tree.get_children()
        if children:
            self.tree.see(children[-1])

    def clear_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
