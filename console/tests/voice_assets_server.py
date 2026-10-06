"""A local, range-capable HTTP server for the voice-asset downloader tests.

Test helper, not a test (pytest only collects `test_*.py`); imported as
`from voice_assets_server import ...` like `evals_support`. It listens on
127.0.0.1 in a thread, so no test touches the internet and no process is
spawned (T-031 plan, evidence conventions).

What it can do, all settable per instance and changeable while it runs:

- `ignore_range`   answer 200 with the whole body even when asked for a range
- `status_script`  a list consumed one entry per request: an int answers with
                   that status and no body, `None` serves normally
- `drop_after`     a list consumed one entry per request: send that many body
                   bytes then slam the connection shut (a mid-body drop)
- `wrong_total`    lie about the total in `Content-Range`
- `redirect_to`    answer 302 with this Location
- `gate(sent)`     called before every body chunk; a test blocks in it to pace
                   the transfer deterministically (no sleeps)

Large bodies come from one reused block (`GeneratedBody`), so serving 32 MiB
never holds 32 MiB, which is what lets a test measure the CLIENT's memory.
"""

import hashlib
import http.server
import random
import threading

_BLOCK_LEN = (1 << 20) + 17     # not a multiple of any chunk size, so a chunk
                                # written at the wrong offset changes the bytes


class Body:
    """A small body held in memory."""

    def __init__(self, data):
        self.data = bytes(data)
        self.size = len(self.data)

    def iter_range(self, start, stop, chunk):
        for pos in range(start, stop, chunk):
            yield self.data[pos:min(pos + chunk, stop)]

    def sha256(self):
        return hashlib.sha256(self.data).hexdigest()


class GeneratedBody:
    """`size` bytes tiled from one pseudo-random block; never fully in memory."""

    def __init__(self, size, seed=1):
        self.size = size
        self._block = random.Random(seed).randbytes(_BLOCK_LEN)

    def iter_range(self, start, stop, chunk):
        pos = start
        while pos < stop:
            n = min(chunk, stop - pos)
            offset = pos % _BLOCK_LEN
            piece = self._block[offset:offset + n]
            while len(piece) < n:
                piece += self._block[:n - len(piece)]
            yield piece
            pos += n

    def sha256(self):
        digest = hashlib.sha256()
        for piece in self.iter_range(0, self.size, 1 << 20):
            digest.update(piece)
        return digest.hexdigest()


class _Handler(http.server.BaseHTTPRequestHandler):
    # HTTP/1.0: one request per connection, so "connection closed" is exactly
    # "this transfer ended", which is what the pause/cancel tests count.
    server_version = "VoiceAssetsTestServer"

    def setup(self):
        super().setup()
        self.server.owner._connection_opened()

    def finish(self):
        try:
            super().finish()
        finally:
            self.server.owner._connection_closed()

    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self._serve(head=True)

    def do_GET(self):
        self._serve(head=False)

    def _serve(self, head):
        owner = self.server.owner
        record = {"method": "HEAD" if head else "GET", "path": self.path,
                  "range": self.headers.get("Range"),
                  "headers": {k.lower(): v for k, v in self.headers.items()},
                  "sent": 0}
        scripted, drop_after = owner._next_request(record)
        try:
            self._respond(owner, record, head, scripted, drop_after)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            record["client_closed"] = True

    def _respond(self, owner, record, head, scripted, drop_after):
        if owner.redirect_to:
            self.send_response(302)
            self.send_header("Location", owner.redirect_to)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if scripted:
            self.send_response(scripted)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = owner.files.get(self.path.split("?", 1)[0])
        if body is None:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        size = body.size
        start, stop, status = 0, size, 200
        wanted = record["range"]
        if wanted and not owner.ignore_range and wanted.startswith("bytes="):
            first = wanted[6:].split("-", 1)[0]
            start = int(first) if first.isdigit() else 0
            if start >= size:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            status = 206
        self.send_response(status)
        self.send_header("Content-Length", str(stop - start))
        if status == 206:
            total = owner.wrong_total if owner.wrong_total is not None else size
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, stop - 1, total))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        if head:
            return
        sent = 0
        for piece in body.iter_range(start, stop, owner.chunk):
            if drop_after is not None and sent + len(piece) > drop_after:
                piece = piece[:max(drop_after - sent, 0)]
                if piece:
                    self.wfile.write(piece)
                    sent += len(piece)
                    record["sent"] = sent
                self.wfile.flush()
                record["dropped"] = True
                self.close_connection = True
                return
            if owner.gate is not None:
                owner.gate(sent)
            self.wfile.write(piece)
            sent += len(piece)
            record["sent"] = sent


class RangeServer:
    def __init__(self, files, *, ignore_range=False, status_script=None,
                 drop_after=None, wrong_total=None, redirect_to=None,
                 chunk=64 * 1024, gate=None):
        self.files = dict(files)
        self.ignore_range = ignore_range
        self.status_script = list(status_script or [])
        self.drop_after = list(drop_after or [])
        self.wrong_total = wrong_total
        self.redirect_to = redirect_to
        self.chunk = chunk
        self.gate = gate
        self.requests = []
        self.connections_total = 0
        self.connections_open = 0
        self._lock = threading.Lock()
        self._httpd = None
        self._thread = None

    # -- bookkeeping, called from handler threads ---------------------------
    def _connection_opened(self):
        with self._lock:
            self.connections_total += 1
            self.connections_open += 1

    def _connection_closed(self):
        with self._lock:
            self.connections_open -= 1

    def _next_request(self, record):
        with self._lock:
            self.requests.append(record)
            scripted = self.status_script.pop(0) if self.status_script else None
            drop = self.drop_after.pop(0) if self.drop_after else None
        return scripted, drop

    # -- lifecycle -----------------------------------------------------------
    def start(self):
        self._httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._httpd.daemon_threads = True
        self._httpd.owner = self
        # A short poll interval makes `shutdown()` return in ~50 ms, not 500.
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, kwargs={"poll_interval": 0.05},
            name="voice-assets-test-server", daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._thread.join(timeout=5)
            self._httpd = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    @property
    def base(self):
        return "http://127.0.0.1:%d" % self._httpd.server_address[1]

    def url(self, path):
        return self.base + path

    def gets(self):
        return [r for r in self.requests if r["method"] == "GET"]
