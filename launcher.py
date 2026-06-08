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

import queue
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import app as seeder_app
import app_erp as erp_app
import virtual_printer as vprinter

# Font family used for *labels* only.  macOS ships Helvetica Neue; Windows ships
# Segoe UI.  Buttons and checkbuttons deliberately do NOT take a custom font:
# on macOS, setting a font on a classic tk.Button/tk.Checkbutton forces Tk to
# stop using the native Aqua control and draw it manually, which flickers on
# hover and leaves "ghost" duplicate controls.  Those interactive controls use
# ttk widgets instead, which always render through the native theme.
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
    {
        'key': 'vprinter',
        'label': 'Virtual Printer (JetDirect)',
        'description': 'Accepts raw print jobs on port 9100',
        'port': 9100,
        'url': None,
        'run': vprinter.run_server,
    },
]


def _port_in_use(port):
    """Return True if something is already listening on localhost:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def _start_app(entry, extra_kwargs=None):
    """Start one app's server in a daemon thread."""
    kwargs = {'open_browser': False}
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    thread = threading.Thread(
        target=entry['run'],
        kwargs=kwargs,
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
        self._vprinter_log_queue = queue.Queue()
        self._log_win  = None   # Toplevel for the virtual printer log
        self._log_text = None   # Text widget inside that Toplevel

        root.title('PrinterLogic Output Demo Launcher')
        root.resizable(False, False)

        # Force the Tk-drawn 'clam' theme instead of the native 'aqua' theme.
        # macOS still ships the deprecated Tk 8.5.9, whose Aqua ttk theme draws
        # buttons/checkbuttons blank (invisible) and whose classic widgets
        # flicker/ghost on hover.  'clam' is rendered by Tk itself, so it looks
        # consistent and renders reliably on every Tk we might be bundled with.
        style = ttk.Style(root)
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        outer = tk.Frame(root, padx=24, pady=20)
        outer.pack(fill='both', expand=True)

        # Two frames pre-built; only one is visible at a time (pack/pack_forget
        # is more reliable than destroy-and-rebuild, especially on macOS).
        self._sel_frame = tk.Frame(outer)
        self._run_frame = tk.Frame(outer)

        self._build_selection_view()
        self._build_status_frame()   # build now but don't show yet

        self._sel_frame.pack(fill='both', expand=True)

        # Start the periodic queue poll so virtual printer log lines are
        # captured and displayed as soon as the log window is opened.
        self.root.after(200, self._poll_log_queue)

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
            # multiple times per click and cause visual doubling.  ttk.Checkbutton
            # renders natively on Aqua (no hover flicker / doubled checkboxes).
            ttk.Checkbutton(
                row,
                text=entry['label'],
                variable=var,
                command=self._update_launch_state,
            ).pack(side='left')

            tk.Label(
                row,
                text=f"— {entry['description']} (port {entry['port']})",
                font=_font(8),
                fg='#888888',
            ).pack(side='left', padx=(4, 0))

        self.launch_btn = ttk.Button(
            f,
            text='Launch',
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

        ttk.Button(
            f,
            text='Quit',
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

            if entry.get('url'):
                link = tk.Label(
                    row,
                    text=entry['url'],
                    font=_font(9, 'underline'),
                    fg='#0969da',
                    cursor='hand2',
                )
                link.pack(side='left', padx=(8, 0))
                link.bind('<Button-1>', lambda _e, url=entry['url']: self._open(url))
            else:
                tk.Label(
                    row,
                    text=f"  Listening on 127.0.0.1:{entry['port']}",
                    font=_font(9),
                    fg='#888888',
                ).pack(side='left', padx=(8, 0))
                ttk.Button(
                    row,
                    text='View Logs',
                    width=10,
                    command=self._show_log_window,
                ).pack(side='left', padx=(8, 0))

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
            extra = {}
            if entry['key'] == 'vprinter':
                extra = {'log_queue': self._vprinter_log_queue}
            _start_app(entry, extra_kwargs=extra)
            self.running.append(entry)

        # Stagger browser opens so the servers have a moment to come up.
        # Entries without a URL (e.g. Virtual Printer) are skipped.
        def _open_browsers():
            import webbrowser
            time.sleep(1.5)
            for entry in self.running:
                if entry.get('url'):
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

    def _show_log_window(self):
        """Open (or raise) the virtual printer connection log window."""
        if self._log_win is not None and self._log_win.winfo_exists():
            self._log_win.deiconify()
            self._log_win.lift()
            return

        win = tk.Toplevel(self.root)
        win.title('Virtual Printer — Connection Log')
        win.geometry('600x300')
        # Hide instead of destroy on close so the window can be re-opened
        # and the log history is preserved.
        win.protocol('WM_DELETE_WINDOW', win.withdraw)
        self._log_win = win

        txt = tk.Text(
            win,
            state='disabled',
            wrap='none',
            font=(_FONT_FAMILY, 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            relief='flat',
            padx=8,
            pady=6,
        )
        sb = tk.Scrollbar(win, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        txt.pack(side='top', fill='both', expand=True)
        self._log_text = txt

        btn_row = tk.Frame(win, padx=8, pady=4)
        btn_row.pack(fill='x')
        ttk.Button(
            btn_row, text='Clear', width=8, command=self._clear_log
        ).pack(side='right')
        tk.Label(
            btn_row,
            text='Each line = one completed print job received on port 9100.',
            font=_font(8),
            fg='#888888',
        ).pack(side='left')

    def _clear_log(self):
        if self._log_text is not None:
            self._log_text.config(state='normal')
            self._log_text.delete('1.0', 'end')
            self._log_text.config(state='disabled')

    def _poll_log_queue(self):
        """Drain the virtual printer queue and append lines to the log window."""
        try:
            while True:
                line = self._vprinter_log_queue.get_nowait()
                if self._log_text is not None and self._log_text.winfo_exists():
                    self._log_text.config(state='normal')
                    self._log_text.insert('end', line + '\n')
                    self._log_text.see('end')
                    self._log_text.config(state='disabled')
        except queue.Empty:
            pass
        self.root.after(200, self._poll_log_queue)

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
