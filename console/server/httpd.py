"""Stdlib-only local web server for the Delivery Console.

This layer owns *transport only* — sockets, headers, status codes, CSRF, and
static files. It knows nothing about boards, tickets, agents or any other
feature: it asks the router (filled by whichever plugins loaded) which
handler serves a path. Adding a feature therefore never edits this file.

Binds 127.0.0.1 only. Every write (POST) must carry the
`X-Console-Request: 1` header — a lightweight CSRF mitigation, since a
same-origin-policy-respecting browser won't let a cross-site page attach a
custom header to a form submission or a no-cors fetch, so a malicious page
can't silently drive this API just because it's reachable on localhost.
"""

import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from . import boards as boards_mod
from .paths import find_repo_root
from .plugins import PluginError, build

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


class EventSource:
    """Marker wrapper: a handler returns one of these to say "the answer is a
    stream, not a value".

    `chunks` is any iterable of already-formatted SSE text. Keeping the
    formatting in the producer (agent_events.Stream) rather than here means
    this layer stays pure transport and doesn't need to know what an agent
    event looks like.
    """

    __slots__ = ("chunks", "_closer")

    def __init__(self, chunks, closer=None):
        self.chunks = chunks
        self._closer = closer

    def __iter__(self):
        return iter(self.chunks)

    def close(self):
        if self._closer is not None:
            self._closer()


class Request:
    """What a plugin handler receives. Narrow on purpose — a handler that
    needs the raw socket is doing transport work in the wrong layer."""

    __slots__ = ("method", "path", "query", "body", "repo_root",
                 "client_addr", "user_agent")

    def __init__(self, method, path, query, body, repo_root,
                 client_addr="", user_agent=""):
        self.method = method
        self.path = path
        self.query = query
        self.body = body
        self.repo_root = repo_root
        # Who is asking. Only used for the audit trail — never for a decision.
        # Behind a tailnet the peer address is the identity in any practical
        # sense; treating a client-controlled header as one would be theatre.
        self.client_addr = client_addr
        self.user_agent = user_agent


class Handler(BaseHTTPRequestHandler):
    repo_root = None  # set by serve()
    router = None  # set by serve()

    def log_message(self, fmt, *args):  # quieter default logging
        pass

    def _send_json(self, status, payload):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path):
        rel = path.lstrip("/") or "index.html"
        full = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not full.startswith(STATIC_DIR):
            self._send_json(403, {"error": "forbidden"})
            return
        if not os.path.isfile(full):
            # SPA fallback: unknown non-API paths render the shell, which then
            # routes on the hash.
            full = os.path.join(STATIC_DIR, "index.html")
        content_type, _ = mimetypes.guess_type(full)
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        # This server exists to develop against, so a stale cached .js/.css
        # after an edit is a bug factory. Revalidate every time; it's
        # localhost, the cost is nil.
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _dispatch(self, method, body):
        split = urlsplit(self.path)
        path = split.path
        query = {k: v[0] for k, v in parse_qs(split.query).items()}

        handler, groups = self.router.resolve(method, path)
        if handler is None:
            if path.startswith("/api/"):
                self._send_json(404, {"error": f"no route for {method} {path}"})
            elif method == "GET":
                self._send_static(path)
            else:
                self._send_json(404, {"error": "no such route"})
            return

        req = Request(method, path, query, body, self.repo_root,
                      client_addr=(self.client_address[0]
                                   if self.client_address else ""),
                      user_agent=self.headers.get("User-Agent", "") or "")
        try:
            result = handler(req, *groups)
        except FileNotFoundError as exc:
            self._send_json(404, {"error": str(exc)})
        except (ValueError, KeyError) as exc:
            self._send_json(400, {"error": str(exc)})
        except PluginError as exc:
            self._send_json(503, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - never leak a stack trace
            self._send_json(500, {"error": str(exc)})
        else:
            # A handler may return an EventSource instead of a JSON body when
            # the answer is a live stream rather than a value. Kept as a
            # marker type so the plugin layer never touches sockets itself.
            if isinstance(result, EventSource):
                self._send_sse(result)
            else:
                self._send_json(201 if method == "POST" else 200, result)

    def _send_sse(self, source):
        """Stream Server-Sent Events until the source is exhausted or the
        client goes away.

        A dropped client shows up as a socket error on write, which is normal
        (a reload, a closed tab) and must not be logged as a fault — the
        session it was watching carries on regardless. `source.close()` always
        runs so the subscriber is released either way.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            for chunk in source:
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError, ValueError):
            pass
        finally:
            try:
                source.close()
            except Exception:  # noqa: BLE001
                pass

    def do_GET(self):
        self._dispatch("GET", {})

    def do_POST(self):
        if self.headers.get("X-Console-Request") != "1":
            self._send_json(403, {"error": "missing X-Console-Request header"})
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "invalid JSON body"})
            return
        if not isinstance(body, dict):
            self._send_json(400, {"error": "JSON body must be an object"})
            return
        self._dispatch("POST", body)


#: Addresses that reach only this machine. Anything else is other people's
#: machines too, and that must never be a quiet fact.
LOOPBACK = ("127.0.0.1", "localhost", "::1")


def _announce_env(repo_root):
    """Say which variable NAMES came from .env — never their values.

    Worth a line because the alternative is a backend that reports "not
    installed" while a key sits in a file two directories up, with nothing to
    say whether it was read.
    """
    from . import dotenv
    info = dotenv.describe(repo_root)
    if not info["present"]:
        return
    if info["names"]:
        print("  .env: %s" % ", ".join(info["names"]))
    else:
        print("  .env: present but defines nothing")


def _announce_binding(host):
    """Say clearly when the console is listening beyond this machine.

    The console has no authentication of its own — by design, because the
    supported way to reach it remotely is a private network (Tailscale or
    similar) that authenticates first. That decision is only safe while it is
    *known*, so a non-loopback bind announces itself every single start rather
    than being something you have to remember configuring six months ago.
    """
    if host in LOOPBACK:
        return
    print("  BINDING: %s — reachable from other machines." % host)
    print("           The console has NO authentication of its own. This is")
    print("           only safe behind a private network (Tailscale or")
    print("           similar) that authenticates before traffic arrives.")
    print("           Do not expose this port to the internet.")


def _announce_notifications(repo_root):
    """Say whether a parked approval can actually reach anyone.

    Silence here is the failure: a run started from a phone stalls at its first
    gated tool and dies on the timeout, and without this line there is nothing
    to suggest why.
    """
    from . import notify
    state = notify.status(repo_root)
    if state["ready"]:
        print("  notifications: %s -> %s"
              % (state["channel"], ", ".join(state["events"])))
    elif state["enabled"]:
        print("  notifications: CONFIGURED BUT NOT READY — %s" % state["reason"])
        print("                 A parked approval will not reach you.")


def _start_scheduler(repo_root):
    """Start the clock, or explain why there isn't one.

    Silence in either direction is the failure to avoid: someone who parked
    every schedule should not wonder whether the ticker is broken, and someone
    whose config has a typo should not discover it a week later when the job
    they expected never ran.
    """
    from . import jobs as jobs_mod
    from . import schedules as schedules_mod
    try:
        registry = schedules_mod.registry(repo_root, force=True)
    except schedules_mod.ScheduleError as exc:
        print(f"  scheduler: OFF — {exc}")
        return None

    enabled = [s for s in registry.values() if s.enabled]
    if not enabled:
        print(f"  scheduler: idle ({len(registry)} schedule(s), all parked)")
        return None

    queue = jobs_mod.JobQueue(repo_root).start()
    ticker = schedules_mod.Ticker(repo_root, queue).start()
    for schedule in sorted(enabled, key=lambda s: s.id):
        print(f"  scheduler: {schedule.id} ({schedule.expr}) "
              f"-> {schedule.verb}, next {schedule.describe()['next_run'] or '-'}")
    return ticker


def serve(repo_root=None, host=None, port=None):
    repo_root = repo_root or find_repo_root()
    console_config = boards_mod.load_console_config(repo_root)
    cfg = console_config["general"]
    host = host or cfg.get("host", "127.0.0.1")
    port = port or cfg.get("port", 8790)
    # Plugins see the *bound* address, not just the file's — a --port override
    # must reach anything that hands this server's address to a subprocess.
    cfg["host"], cfg["port"] = host, port

    ctx, router = build(repo_root, console_config)

    Handler.repo_root = repo_root
    Handler.router = router
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Delivery Console serving http://{host}:{port} (repo: {repo_root})")
    print(f"  plugins: {', '.join(sorted(ctx.tabs()))}")
    _announce_env(repo_root)
    _announce_binding(host)
    _announce_notifications(repo_root)

    # The clock. Started here rather than in a plugin because it belongs to the
    # server's lifetime, not to a tab — and stated out loud, because a
    # scheduler nobody can see running is a scheduler nobody trusts.
    ticker = _start_scheduler(repo_root)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if ticker is not None:
            ticker.stop()
        httpd.server_close()
        # Agent sessions are child processes of this server. Without this they
        # survive it — still running, still holding their transcript files
        # open, and unreachable because nothing re-attaches after a restart.
        # Asked of the plugin by name so the transport layer keeps knowing
        # nothing about agents, and skipped silently when that plugin is off.
        if ctx.has_provider("agents"):
            try:
                ctx.provider("agents").shutdown_all()
            except Exception as exc:  # noqa: BLE001
                print(f"  warning: could not stop agent sessions cleanly: {exc}")
