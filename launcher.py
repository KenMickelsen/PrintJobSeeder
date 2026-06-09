"""
launcher.py — Unified launcher for the Vasion print demo apps.

On **Windows** (and Linux) a native Tkinter window is used — checkboxes to
select apps, a Launch button, and a status view with clickable links.
On **macOS** the system Tcl/Tk 8.5.9 panics in TkpInit under recent OS
versions, so a small browser-based control panel is served instead (Flask,
port 5750).  Both paths share the same APP_REGISTRY, port helpers, and
thread-start logic below.

Adding a future app only requires appending an entry to APP_REGISTRY below.
"""

import collections
import queue
import socket
import sys
import threading
import time
import webbrowser

import app as seeder_app
import app_erp as erp_app
import app_emr as emr_app
import virtual_printer as vprinter

# macOS ships Helvetica Neue; Windows ships Segoe UI.
_FONT_FAMILY = 'Helvetica Neue' if sys.platform == 'darwin' else 'Segoe UI'


def _font(size, *modifiers):
    """Return a tkinter font tuple for the current platform."""
    return (_FONT_FAMILY, size) + modifiers


def _maybe_attach_console():
    """Allocate a Windows console if --console was passed on the command line."""
    if '--console' not in sys.argv:
        return
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.AllocConsole()
        sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
        sys.stderr = open('CONOUT$', 'w', encoding='utf-8')
        sys.stdin  = open('CONIN$',  'r', encoding='utf-8')


# ---------------------------------------------------------------------------
# Registry of launchable apps — drives both the Tkinter and browser UIs.
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
        'key': 'emr',
        'label': 'Meridian Health EMR Demo',
        'description': 'Fake healthcare EMR',
        'port': 5759,
        'url': 'http://localhost:5759',
        'run': emr_app.run_server,
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

# Registry lookup by key for the browser-launcher API handlers.
_REGISTRY_BY_KEY = {entry['key']: entry for entry in APP_REGISTRY}

# Virtual printer connection log shared between both UI paths.
_vprinter_log_queue = queue.Queue()
_printer_log = collections.deque(maxlen=1000)
_printer_log_lock = threading.Lock()


def _port_in_use(port):
    """Return True if something is already listening on localhost:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def _start_app(entry):
    """Start one app server in a daemon thread."""
    kwargs = {'open_browser': False}
    if entry['key'] == 'vprinter':
        kwargs['log_queue'] = _vprinter_log_queue
    thread = threading.Thread(
        target=entry['run'],
        kwargs=kwargs,
        daemon=True,
        name=f"server-{entry['key']}",
    )
    thread.start()
    return thread


def _drain_printer_log():
    """Background worker: move virtual printer log lines into the shared list."""
    while True:
        line = _vprinter_log_queue.get()
        with _printer_log_lock:
            _printer_log.append(line)


# ===========================================================================
# Tkinter launcher  (Windows / Linux)
# ===========================================================================

class LauncherWindow:
    """Native Tkinter launcher / status window."""

    def __init__(self, root):
        self.root = root
        self.vars = {}
        self.running = []

        root.title('PrinterLogic Output Demo Launcher')
        root.resizable(False, False)

        outer = tk.Frame(root, padx=24, pady=20)
        outer.pack(fill='both', expand=True)

        # Pre-build both frames; swap with pack/pack_forget to avoid flicker.
        self._sel_frame = tk.Frame(outer)
        self._run_frame = tk.Frame(outer)

        self._build_selection_view()
        self._build_status_frame()

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

            # Use command= instead of trace_add — avoids macOS visual doubling.
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

        # ttk.Button uses native rendering on Windows.
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
                    text=f"— listening on 127.0.0.1:{entry['port']}",
                    font=_font(9),
                    fg='#888888',
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
            _start_app(entry)
            self.running.append(entry)

        def _open_browsers():
            time.sleep(1.5)
            for entry in self.running:
                if entry.get('url'):
                    webbrowser.open(entry['url'])
                    time.sleep(0.4)

        threading.Thread(target=_open_browsers, daemon=True).start()

        self._populate_status_rows()
        # Swap frames — no destroy/rebuild, avoids repaint overlap.
        self._sel_frame.pack_forget()
        self._run_frame.pack(fill='both', expand=True)

    # -- Helpers -----------------------------------------------------------
    @staticmethod
    def _open(url):
        webbrowser.open(url)

    def _on_quit(self):
        self.root.destroy()


def _run_tkinter_launcher():
    import tkinter as tk
    from tkinter import ttk, messagebox
    # Inject into module scope so LauncherWindow methods can reference them.
    globals()['tk'] = tk
    globals()['ttk'] = ttk
    globals()['messagebox'] = messagebox

    root = tk.Tk()
    LauncherWindow(root)
    root.mainloop()


# ===========================================================================
# Browser launcher  (macOS)
# ===========================================================================

from flask import Flask, jsonify, render_template_string, request  # noqa: E402

LAUNCHER_PORT = 5750
LAUNCHER_URL  = f'http://localhost:{LAUNCHER_PORT}'

# Keys of apps started this session (browser path only).
_running      = set()
_running_lock = threading.Lock()

launcher_app  = Flask(__name__)

_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PrinterLogic Output Demo Launcher</title>
  <style>
    :root { --accent:#0969da; --green:#1a7f37; --bg:#f6f8fa; --card:#fff;
            --border:#d0d7de; --muted:#656d76; }
    * { box-sizing: border-box; }
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",
           Helvetica,Arial,sans-serif; background:var(--bg); color:#1f2328; }
    .wrap { max-width:640px; margin:0 auto; padding:32px 20px 48px; }
    h1 { font-size:22px; margin:0 0 4px; }
    .sub { color:var(--muted); margin:0 0 24px; font-size:14px; }
    .card { background:var(--card); border:1px solid var(--border);
            border-radius:10px; padding:16px 18px; margin-bottom:12px;
            display:flex; align-items:flex-start; gap:12px; }
    .card input[type=checkbox] { width:18px; height:18px; margin-top:2px;
            flex:0 0 auto; cursor:pointer; }
    .card .meta { flex:1 1 auto; min-width:0; }
    .card .name { font-weight:600; font-size:15px; }
    .card .desc { color:var(--muted); font-size:13px; margin-top:2px; }
    .card .state { font-size:13px; margin-top:6px; }
    .card .state a { color:var(--accent); text-decoration:none; }
    .card .state a:hover { text-decoration:underline; }
    .dot { color:var(--green); font-weight:700; }
    .actions { display:flex; justify-content:flex-end; gap:10px;
               margin-top:20px; }
    button { font:inherit; font-size:14px; font-weight:600; padding:9px 18px;
             border-radius:8px; border:1px solid var(--border);
             background:#fff; cursor:pointer; }
    button.primary { background:var(--accent); border-color:var(--accent);
             color:#fff; }
    button.primary:disabled { opacity:.45; cursor:not-allowed; }
    button.danger { color:#cf222e; }
    .log { background:#1e1e1e; color:#d4d4d4; border-radius:8px; padding:12px;
           font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
           font-size:12.5px; height:180px; overflow:auto; white-space:pre-wrap;
           margin-top:8px; }
    .loghdr { display:flex; justify-content:space-between; align-items:center;
              margin-top:20px; }
    .hidden { display:none; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>PrinterLogic Output Demo Launcher</h1>
    <p class="sub">Select which apps to launch, then click Launch. Keep this
      tab open while the apps are in use.</p>

    <div id="cards"></div>

    <div class="actions">
      <button id="launch" class="primary" disabled>Launch</button>
      <button id="quit" class="danger">Quit</button>
    </div>

    <div id="logwrap" class="hidden">
      <div class="loghdr">
        <strong>Virtual Printer — Connection Log</strong>
        <span class="sub" style="margin:0">Each line = one print job on port 9100</span>
      </div>
      <div id="log" class="log"></div>
    </div>
  </div>

<script>
let logLen = 0;

function render(apps) {
  const prevChecked = new Set(
    [...document.querySelectorAll('input[type=checkbox]:checked:not(:disabled)')]
      .map(cb => cb.dataset.key)
  );

  const cards = document.getElementById('cards');
  cards.innerHTML = '';
  let anyVprinter = false;
  apps.forEach(a => {
    if (a.key === 'vprinter' && a.running) anyVprinter = true;
    const card = document.createElement('div');
    card.className = 'card';
    let state = '';
    if (a.running) {
      if (a.url) {
        state = `<div class="state"><span class="dot">&#x25CF;</span> Running \u2014
                 <a href="${a.url}" target="_blank">${a.url}</a></div>`;
      } else {
        state = `<div class="state"><span class="dot">&#x25CF;</span> Running \u2014
                 listening on 127.0.0.1:${a.port}</div>`;
      }
    }
    const cbAttr = a.running
      ? 'checked disabled'
      : (prevChecked.has(a.key) ? 'checked' : '');
    card.innerHTML = `
      <input type="checkbox" data-key="${a.key}" ${cbAttr}>
      <div class="meta">
        <div class="name">${a.label}</div>
        <div class="desc">${a.description} (port ${a.port})</div>
        ${state}
      </div>`;
    cards.appendChild(card);
  });
  cards.querySelectorAll('input[type=checkbox]').forEach(cb => {
    cb.addEventListener('change', updateLaunchState);
  });
  updateLaunchState();
  document.getElementById('logwrap').classList.toggle('hidden', !anyVprinter);
}

function selectedKeys() {
  return [...document.querySelectorAll('input[type=checkbox]:checked:not(:disabled)')]
    .map(cb => cb.dataset.key);
}

function updateLaunchState() {
  document.getElementById('launch').disabled = selectedKeys().length === 0;
}

async function refresh() {
  const r = await fetch('/api/status');
  const data = await r.json();
  render(data.apps);
}

document.getElementById('launch').addEventListener('click', async () => {
  const keys = selectedKeys();
  if (!keys.length) return;
  const btn = document.getElementById('launch');
  btn.disabled = true;
  const r = await fetch('/api/launch', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({keys})
  });
  const data = await r.json();
  if (data.errors && data.errors.length) {
    alert('Could not start:\n\n' + data.errors.join('\n') +
          '\n\nClose the existing instance and try again.');
  }
  render(data.apps);
});

document.getElementById('quit').addEventListener('click', async () => {
  if (!confirm('Quit and stop all running apps?')) return;
  document.body.innerHTML =
    '<div class="wrap"><h1>Stopped</h1>' +
    '<p class="sub">All apps have been shut down. You can close this tab.</p></div>';
  fetch('/api/quit', {method: 'POST'}).catch(() => {});
});

async function pollLog() {
  try {
    const r = await fetch('/api/printer-log?since=' + logLen);
    const data = await r.json();
    if (data.lines && data.lines.length) {
      const log = document.getElementById('log');
      data.lines.forEach(line => { log.textContent += line + '\n'; });
      log.scrollTop = log.scrollHeight;
      logLen = data.total;
    }
  } catch (e) { /* ignore transient errors */ }
}

refresh();
setInterval(refresh, 2000);
setInterval(pollLog, 1000);
</script>
</body>
</html>"""


@launcher_app.route('/')
def index():
    return render_template_string(_PAGE)


def _status_payload():
    with _running_lock:
        running = set(_running)
    return [
        {
            'key': e['key'],
            'label': e['label'],
            'description': e['description'],
            'port': e['port'],
            'url': e['url'],
            'running': e['key'] in running,
        }
        for e in APP_REGISTRY
    ]


@launcher_app.route('/api/status')
def api_status():
    return jsonify({'apps': _status_payload()})


@launcher_app.route('/api/launch', methods=['POST'])
def api_launch():
    body = request.get_json(silent=True) or {}
    keys = [k for k in body.get('keys', []) if k in _REGISTRY_BY_KEY]

    errors = []
    to_start = []
    for key in keys:
        with _running_lock:
            already = key in _running
        if already:
            continue
        entry = _REGISTRY_BY_KEY[key]
        if _port_in_use(entry['port']):
            errors.append(f"  \u2022 {entry['label']} (port {entry['port']}) is already in use")
            continue
        to_start.append(entry)

    started_urls = []
    for entry in to_start:
        _start_app(entry)
        with _running_lock:
            _running.add(entry['key'])
        if entry.get('url'):
            started_urls.append(entry['url'])

    if started_urls:
        def _open_browsers(urls):
            time.sleep(1.5)
            for url in urls:
                webbrowser.open(url)
                time.sleep(0.4)
        threading.Thread(
            target=_open_browsers, args=(started_urls,), daemon=True
        ).start()

    return jsonify({'apps': _status_payload(), 'errors': errors})


@launcher_app.route('/api/printer-log')
def api_printer_log():
    try:
        since = int(request.args.get('since', 0))
    except (TypeError, ValueError):
        since = 0
    with _printer_log_lock:
        lines = list(_printer_log)
    total = len(lines)
    new_lines = lines[since:] if 0 <= since <= total else lines
    return jsonify({'lines': new_lines, 'total': total})


@launcher_app.route('/api/quit', methods=['POST'])
def api_quit():
    def _shutdown():
        time.sleep(0.3)
        import os
        os._exit(0)
    threading.Thread(target=_shutdown, daemon=True).start()
    return jsonify({'ok': True})


def _run_browser_launcher():
    threading.Thread(target=_drain_printer_log, daemon=True).start()

    def _open_panel():
        time.sleep(1.0)
        webbrowser.open(LAUNCHER_URL)
    threading.Thread(target=_open_panel, daemon=True).start()

    print(f"PrinterLogic Output Demo Launcher running at {LAUNCHER_URL}")
    launcher_app.run(debug=False, host='localhost', port=LAUNCHER_PORT,
                     threaded=True, use_reloader=False)


# ===========================================================================
# Entry point
# ===========================================================================

def main():
    _maybe_attach_console()
    if sys.platform == 'darwin':
        _run_browser_launcher()
    else:
        _run_tkinter_launcher()


if __name__ == '__main__':
    main()