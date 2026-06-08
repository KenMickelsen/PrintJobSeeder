"""
launcher.py — Unified launcher for the Vasion print demo apps.

Presents a small checkbox window so the user can choose which apps to start:
Print Job Seeder, the Apex Industrial ERP Demo, or both.  At least one app must
be selected before launching. Each selected app runs in its own daemon thread
inside this single process, and its browser tab is opened automatically. After
launching, the window becomes a status panel with a Quit button that stops
everything.

This module is the entry point packaged into the standalone Windows .exe.

Adding a future app (e.g. an EMR demo) only requires appending an entry to
APP_REGISTRY below.
"""

import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import app as seeder_app
import app_erp as erp_app

# macOS ships Helvetica Neue; Windows ships Segoe UI.  Specifying a font that
# doesn't exist on the platform causes tkinter to fall back with rendering
# artefacts (flashing, doubled checkboxes, etc.).
_FONT_FAMILY = 'Helvetica Neue' if sys.platform == 'darwin' else 'Segoe UI'


def _font(size, *modifiers):
    """Return a tkinter font tuple for the current platform."""
    return (_FONT_FAMILY, size) + modifiers


def _maybe_attach_console():
    """If --console was passed on the command line, allocate a Windows console
    window and redirect stdout/stderr to it so server logs are visible.
    On macOS/Linux the terminal is always available when launched from one,
    so this is a no-op on those platforms."""
    if '--console' not in sys.argv:
        return
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.AllocConsole()
        # Re-open the standard streams so Python output reaches the new console.
        sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
        sys.stderr = open('CONOUT$', 'w', encoding='utf-8')
        sys.stdin  = open('CONIN$',  'r', encoding='utf-8')


# ---------------------------------------------------------------------------
# Registry of launchable apps — drives the checkboxes. Add new apps here.
# ---------------------------------------------------------------------------
APP_REGISTRY = [
    {
        'key': 'seeder',
        'label': 'Print Job Seeder',
        'description': 'Bulk print-job generator',
        'port': 5757,
        'url': 'http://localhost:5757',
        'run': seeder_app.run_server,
    },
    {
        'key': 'erp',
        'label': 'Apex Industrial ERP Demo',
        'description': 'Fake manufacturing ERP',
        'port': 5758,
        'url': 'http://localhost:5758',
        'run': erp_app.run_server,
    },
]


def _port_in_use(port):
    """Return True if something is already listening on localhost:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def _start_app(entry):
    """Start one app's server in a daemon thread."""
    thread = threading.Thread(
        target=entry['run'],
        kwargs={'open_browser': False},
        daemon=True,
        name=f"server-{entry['key']}",
    )
    thread.start()
    return thread


class LauncherWindow:
    """The Tkinter launcher / status window."""

    def __init__(self, root):
        self.root = root
        self.vars = {}
        self.running = []  # entries that have been started

        root.title('PrinterLogic Output Demo Launcher')
        root.resizable(False, False)

        outer = tk.Frame(root, padx=24, pady=20)
        outer.pack(fill='both', expand=True)

        # Two frames pre-built; only one is visible at a time (pack/pack_forget
        # is more reliable than destroy-and-rebuild, especially on macOS).
        self._sel_frame = tk.Frame(outer)
        self._run_frame = tk.Frame(outer)

        self._build_selection_view()
        self._build_status_frame()   # build now but don't show yet

        self._sel_frame.pack(fill='both', expand=True)

    # -- Selection view ----------------------------------------------------
    def _build_selection_view(self):
        f = self._sel_frame

        tk.Label(
            f,
            text='PrinterLogic Output Demo Launcher',
            font=_font(14, 'bold'),
        ).pack(anchor='w')

        tk.Label(
            f,
            text='Select which apps to launch, then click Launch.',
            font=_font(9),
            fg='#555555',
        ).pack(anchor='w', pady=(2, 14))

        for entry in APP_REGISTRY:
            var = tk.IntVar(value=0)
            self.vars[entry['key']] = var

            row = tk.Frame(f)
            row.pack(fill='x', anchor='w', pady=2)

            # Use command= instead of trace_add — on macOS, traces can fire
            # multiple times per click and cause visual doubling.
            tk.Checkbutton(
                row,
                text=entry['label'],
                variable=var,
                font=_font(10),
                command=self._update_launch_state,
            ).pack(side='left')

            tk.Label(
                row,
                text=f"— {entry['description']} (port {entry['port']})",
                font=_font(8),
                fg='#888888',
            ).pack(side='left', padx=(4, 0))

        self.launch_btn = tk.Button(
            f,
            text='Launch',
            font=_font(10, 'bold'),
            width=14,
            state='disabled',
            command=self._on_launch,
        )
        self.launch_btn.pack(anchor='e', pady=(16, 0))

    def _update_launch_state(self):
        any_selected = any(v.get() for v in self.vars.values())
        self.launch_btn.config(state='normal' if any_selected else 'disabled')

    # -- Status frame (pre-built, shown after launch) ----------------------
    def _build_status_frame(self):
        f = self._run_frame

        tk.Label(
            f,
            text='Running',
            font=_font(14, 'bold'),
        ).pack(anchor='w')

        tk.Label(
            f,
            text='These apps are live. Keep this window open while in use.',
            font=_font(9),
            fg='#555555',
        ).pack(anchor='w', pady=(2, 14))

        # Placeholder frame for per-app status rows, populated on launch.
        self._status_rows = tk.Frame(f)
        self._status_rows.pack(fill='x')

        tk.Button(
            f,
            text='Quit',
            font=_font(10, 'bold'),
            width=14,
            command=self._on_quit,
        ).pack(anchor='e', pady=(16, 0))

    def _populate_status_rows(self):
        for entry in self.running:
            row = tk.Frame(self._status_rows)
            row.pack(fill='x', anchor='w', pady=2)

            tk.Label(
                row,
                text=f"● {entry['label']}",
                font=_font(10),
                fg='#1a7f37',
            ).pack(side='left')

            link = tk.Label(
                row,
                text=entry['url'],
                font=_font(9, 'underline'),
                fg='#0969da',
                cursor='hand2',
            )
            link.pack(side='left', padx=(8, 0))
            link.bind('<Button-1>', lambda _e, url=entry['url']: self._open(url))

    # -- Launch ------------------------------------------------------------
    def _on_launch(self):
        selected = [e for e in APP_REGISTRY if self.vars[e['key']].get()]
        if not selected:
            return

        in_use = [e for e in selected if _port_in_use(e['port'])]
        if in_use:
            names = '\n'.join(f"  • {e['label']} (port {e['port']})" for e in in_use)
            messagebox.showerror(
                'Port already in use',
                'These apps appear to already be running:\n\n'
                f'{names}\n\nClose the existing instance and try again.',
            )
            return

        for entry in selected:
            _start_app(entry)
            self.running.append(entry)

        # Stagger browser opens so the servers have a moment to come up.
        def _open_browsers():
            import webbrowser
            time.sleep(1.5)
            for entry in self.running:
                webbrowser.open(entry['url'])
                time.sleep(0.4)

        threading.Thread(target=_open_browsers, daemon=True).start()

        self._populate_status_rows()
        # Swap frames — no destroy/rebuild, avoids macOS repaint overlap.
        self._sel_frame.pack_forget()
        self._run_frame.pack(fill='both', expand=True)

    # -- Helpers -----------------------------------------------------------
    @staticmethod
    def _open(url):
        import webbrowser
        webbrowser.open(url)

    def _on_quit(self):
        # Servers run as daemon threads, so they exit when the process exits.
        self.root.destroy()


def main():
    _maybe_attach_console()
    root = tk.Tk()
    LauncherWindow(root)
    root.mainloop()


if __name__ == '__main__':
    main()
