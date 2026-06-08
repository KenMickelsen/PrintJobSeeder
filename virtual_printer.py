"""
virtual_printer.py — JetDirect (AppSocket) virtual printer on port 9100.

Listens for raw print data on 127.0.0.1:9100, reads and discards all bytes,
then closes the connection cleanly.

For the JetDirect/AppSocket (raw port 9100) protocol a clean TCP close is the
success signal — the output/routing service considers the job delivered when
the connection terminates without a TCP RST.  No response bytes are sent back;
that is correct behaviour for this protocol.

This module has no external dependencies; it uses only the Python stdlib.
"""

import logging
import queue
import socketserver
import time

logger = logging.getLogger(__name__)

_HOST = '127.0.0.1'
_PORT = 9100
_CHUNK = 4096   # bytes per recv call


class _VirtualPrinterServer(socketserver.ThreadingTCPServer):
    """ThreadingTCPServer with sensible defaults for the virtual printer."""

    # Allow the port to be reused immediately after the server stops (avoids
    # "Address already in use" if the process is restarted quickly).
    allow_reuse_address = True

    # Each connection is handled in its own daemon thread so the server never
    # blocks on a slow or stalled client.
    daemon_threads = True

    # Set to a queue.Queue by run_server() before serve_forever() is called.
    _log_queue = None


class _PrintHandler(socketserver.BaseRequestHandler):
    """Handle one incoming JetDirect connection."""

    def handle(self):
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        total = 0
        try:
            while True:
                chunk = self.request.recv(_CHUNK)
                if not chunk:
                    break
                total += len(chunk)
        except OSError:
            # Connection reset by peer or other socket error — not a problem.
            pass

        ts = time.strftime('%H:%M:%S')
        msg = f"[{ts}]  {peer}  —  {total:,} bytes received"
        logger.info("Virtual Printer: %s", msg)

        lq = getattr(self.server, '_log_queue', None)
        if lq is not None:
            try:
                lq.put_nowait(msg)
            except queue.Full:
                pass   # drop the line rather than block the handler thread


def run_server(open_browser=False, log_queue=None):
    """Start the virtual printer TCP server.  Blocks until the process exits.

    Args:
        open_browser: Accepted for API compatibility with other registry
            entries; has no effect — there is no web UI for this service.
        log_queue: Optional ``queue.Queue``.  A one-line string is appended
            for each completed print job so the launcher UI can display a
            live connection log.
    """
    with _VirtualPrinterServer((_HOST, _PORT), _PrintHandler) as server:
        server._log_queue = log_queue
        logger.info("Virtual Printer listening on %s:%d", _HOST, _PORT)
        server.serve_forever()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    print(f"Virtual Printer listening on {_HOST}:{_PORT} — press Ctrl+C to stop")
    run_server()
