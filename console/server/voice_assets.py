"""Speech models and voices: the catalog, and (in later sections) the downloader.

T-031. The console owns downloading, verifying and deleting what lives in
`desktop/stt` (whisper `ggml-*.bin`) and `desktop/tts` (piper `*.onnx` +
`*.onnx.json`); the desktop shell only reads those directories. Stdlib only,
on purpose (decision D-10): `urllib`, `hashlib`, `threading`, and the console's
own `tomlio` (D-16, not `tomllib`).

Mechanics are ported from Mic Drop's downloader (resumable `.part` + Range,
bounded retries, nothing half-written ever has the shell-visible name) with one
addition it lacks: every file is checked against a SHA256 pinned in the
committed catalog before it gets its real name (BR-2).

## Catalog

`console/config/voice-assets.toml` is the only place a URL or a hash enters the
repo. Requests carry catalog ids only (BR-9), never a URL or a path, so
everything below that touches the network or the disk starts from an `Asset`
loaded here.
"""

import datetime
import hashlib
import http.client
import json
import logging
import math
import os
import re
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from . import tomlio

#: Where assets land, relative to the repo root. The shell reads the same two
#: directories (`stt.rs` STT_DIR, `piper.rs` TTS_DIR).
STT_DIR_REL = os.path.join("desktop", "stt")
TTS_DIR_REL = os.path.join("desktop", "tts")

KIND_STT = "stt"
KIND_VOICE = "voice"

HASH_LFS = "hf-lfs-oid"
HASH_COMPUTED = "computed-pinned"
HASH_SOURCES = (HASH_LFS, HASH_COMPUTED)

#: Every name that ever reaches a path is checked against this (NFR-3).
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class CatalogError(ValueError):
    """The catalog file is malformed. Raised at load, never at request time."""


@dataclass(frozen=True)
class AssetFile:
    name: str
    url: str
    size: int
    sha256: str
    hash_source: str
    git_blob_sha1: str = ""


@dataclass(frozen=True)
class Asset:
    id: str
    kind: str
    label: str
    repo: str
    commit: str
    hint: str
    license: str
    files: tuple = field(default_factory=tuple)

    @property
    def size_bytes(self):
        """What the user is committing to download; a voice is both files."""
        return sum(f.size for f in self.files)

    @property
    def dir_rel(self):
        return STT_DIR_REL if self.kind == KIND_STT else TTS_DIR_REL

    @property
    def main_file(self):
        """The shell-visible file: `ggml-*.bin` or `*.onnx`. It is always the
        LAST file of an asset, so it only appears once everything it needs
        (a voice's `.onnx.json`) is already in place."""
        return self.files[-1]

    def public(self):
        """The catalog facts the API returns (AC-3). Never a URL or a path."""
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "hint": self.hint,
            "license": self.license,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class Catalog:
    assets: tuple

    def get(self, asset_id):
        for asset in self.assets:
            if asset.id == asset_id:
                return asset
        return None

    def of_kind(self, kind):
        return tuple(a for a in self.assets if a.kind == kind)


def _need(row, key, where, kind=str):
    value = row.get(key)
    if not isinstance(value, kind) or isinstance(value, bool) or value in ("", None):
        raise CatalogError("%s: %r is missing or not a %s" % (where, key, kind.__name__))
    return value


def _file_from_row(row, where):
    name = _need(row, "name", where)
    if not SAFE_NAME.match(name):
        raise CatalogError("%s: unsafe file name %r" % (where, name))
    sha256 = _need(row, "sha256", where)
    if not _HEX64.match(sha256):
        raise CatalogError("%s: sha256 of %s is not 64 lowercase hex" % (where, name))
    source = _need(row, "hash_source", where)
    if source not in HASH_SOURCES:
        raise CatalogError("%s: hash_source %r of %s is not one of %s"
                           % (where, source, name, ", ".join(HASH_SOURCES)))
    blob = row.get("git_blob_sha1", "")
    if source == HASH_COMPUTED and not _HEX40.match(str(blob)):
        raise CatalogError("%s: %s is computed-pinned but has no git_blob_sha1"
                           % (where, name))
    size = _need(row, "size", where, int)
    if size <= 0:
        raise CatalogError("%s: size of %s must be positive" % (where, name))
    return AssetFile(name=name, url=_need(row, "url", where), size=size,
                     sha256=sha256, hash_source=source,
                     git_blob_sha1=str(blob))


def _asset_from_row(row, kind):
    asset_id = _need(row, "id", kind)
    where = "%s %s" % (kind, asset_id)
    if not SAFE_NAME.match(asset_id):
        raise CatalogError("%s: unsafe id" % where)
    rows = row.get("file")
    if not isinstance(rows, list) or not rows:
        raise CatalogError("%s: no files" % where)
    files = tuple(_file_from_row(r, where) for r in rows)
    return Asset(id=asset_id, kind=kind, label=_need(row, "label", where),
                 repo=_need(row, "repo", where), commit=_need(row, "commit", where),
                 hint=_need(row, "hint", where), license=_need(row, "license", where),
                 files=files)


def catalog_from_dict(data):
    """Build a Catalog from parsed TOML; the entry point for test fixtures."""
    assets = []
    for kind in (KIND_STT, KIND_VOICE):
        for row in data.get(kind, []):
            assets.append(_asset_from_row(row, kind))
    ids = [a.id for a in assets]
    if len(set(ids)) != len(ids):
        raise CatalogError("duplicate asset id in the catalog")
    return Catalog(assets=tuple(assets))


def default_catalog_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "config", "voice-assets.toml")


def load_catalog(path=None):
    """Read the committed catalog with the console's own `tomlio` (D-16)."""
    return catalog_from_dict(tomlio.load(path or default_catalog_path()))


# ---------------------------------------------------------------------------
# Transfer: one file, resumable, streamed
# ---------------------------------------------------------------------------

#: Read and write in 1 MiB pieces; memory stays flat however large the model
#: (NFR-5). A bigger buffer buys nothing and a 1.5 GB model must never be held.
CHUNK = 1 << 20

#: Per-socket-operation timeout. There is deliberately no overall deadline:
#: models are large and slow links are legitimate, a stalled link is not.
IO_TIMEOUT = 30.0

USER_AGENT = "control-center-console/voice-assets"

_CONTENT_RANGE = re.compile(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$")


class TransferError(Exception):
    """A transfer ended without a complete file.

    `retryable` says whether asking again can help (a dropped connection, a
    429 or 5xx); a 404, a changed upstream file or a full disk cannot be fixed
    by trying the same request again.
    """

    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


class Interrupted(Exception):
    """The caller asked the transfer to stop: `reason` is "pause" or "cancel"."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def part_path(final_path):
    return final_path + ".part"


#: Consecutive failures tolerated before a transfer gives up (FR-4, D-4). The
#: counter resets whenever bytes arrive, so a flaky link that keeps making
#: progress is never abandoned; a dead one costs about 47 s of waiting.
MAX_FAILURES = 6


def backoff_delay(failures):
    """Seconds to wait after the `failures`-th consecutive failure (AC-14).

    0.5 s doubling, capped at 16 s: 0.5, 1, 2, 4, 8, 16, 16 for 0..6. The loop
    increments the counter FIRST (Mic Drop's mechanics), so the sleeps it
    actually takes are failures 1..6 = 1, 2, 4, 8, 16, 16 s and the seventh
    consecutive failure fails (decision D-19).
    """
    return 0.5 * 2 ** min(failures, 5)


# --- URL policy (NFR-3, AC-31) ----------------------------------------------

#: Downloads start only here. CDN hostnames are NOT allow-listed (they change;
#: the pinned sha256 is what guards integrity), so a redirect may go to any
#: host, but only over https.
ALLOWED_HOST = "huggingface.co"
_STRIPPED_HEADERS = ("Authorization", "Cookie", "Proxy-authorization")


class PolicyError(TransferError):
    """A URL the downloader refuses to request. Never retried."""


def check_url(url, allow_loopback_http=False, initial=True):
    """Raise PolicyError unless `url` may be requested.

    `initial` is the catalog URL (host must be exactly huggingface.co); a
    redirect target only has to be https. `allow_loopback_http` is the
    test-only flag that admits `http://127.0.0.1`, and nothing else.
    """
    parts = urllib.parse.urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if parts.username or parts.password or "@" in parts.netloc:
        raise PolicyError("a download URL may not carry credentials")
    if scheme == "http":
        if allow_loopback_http and host == "127.0.0.1":
            return
        raise PolicyError("only https downloads are allowed (refused http://%s)" % host)
    if scheme != "https":
        raise PolicyError("only https downloads are allowed (scheme %r)" % scheme)
    if initial and (host != ALLOWED_HOST or parts.port not in (None, 443)):
        raise PolicyError("downloads start only from %s (refused %s)"
                          % (ALLOWED_HOST, parts.netloc))


class _PolicyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to https, and never carry credentials along."""

    def __init__(self, allow_loopback_http):
        self.allow_loopback_http = allow_loopback_http

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl, self.allow_loopback_http, initial=False)
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            for name in _STRIPPED_HEADERS:
                new.remove_header(name)
        return new


def _build_default_opener(allow_loopback_http):
    opener = urllib.request.build_opener(_PolicyRedirectHandler(allow_loopback_http))
    return lambda request, timeout: opener.open(request, timeout=timeout)


def _status_of(response):
    status = getattr(response, "status", None)
    return status if status is not None else response.getcode()


class Transfer:
    """Fetch ONE catalog file into `{dest_dir}/{name}.part`.

    Seams, all injectable so tests never touch the internet or the wall clock:
    `opener(request, timeout)` stands in for `urlopen`; `stop()` returns a
    falsy value to carry on or "pause"/"cancel" to end the transfer between
    chunks (the connection is closed, the `.part` kept); `on_progress(have)`
    gets the byte count of THIS file on disk after every chunk; `sleep(s)`
    replaces the backoff wait (a test records instead of sleeping; by default
    the wait is taken in 0.1 s slices so pause/cancel stay responsive);
    `on_retry(failures, delay, message)` is told before each backoff wait.

    The URL policy (`check_url`) runs inside `_open`, the request path itself,
    so it still applies when a fake `opener` is injected. `allow_loopback_http`
    is test-only and admits `http://127.0.0.1` and nothing else.

    `run()` returns the `.part` path once it holds exactly `spec.size` bytes.
    It does not verify or rename it: that is the install step, which is the
    only code allowed to give a file its shell-visible name (BR-2).
    """

    def __init__(self, spec, dest_dir, opener=None, stop=None, on_progress=None,
                 sleep=None, on_retry=None, allow_loopback_http=False,
                 open_part=open):
        self.spec = spec
        self.dest_dir = dest_dir
        self.final = os.path.join(dest_dir, spec.name)
        self.part = part_path(self.final)
        self.allow_loopback_http = allow_loopback_http
        self.opener = opener or _build_default_opener(allow_loopback_http)
        self.stop = stop
        self.on_progress = on_progress
        self.sleep = sleep
        self.on_retry = on_retry
        self.open_part = open_part          # a test fills the disk through this
        self.resumed_from = 0
        self._progressed = False

    # -- helpers -------------------------------------------------------------
    def have(self):
        try:
            return os.path.getsize(self.part)
        except OSError:
            return 0

    def _discard_part(self):
        try:
            os.remove(self.part)
        except FileNotFoundError:
            pass

    def _check_stop(self):
        reason = self.stop() if self.stop else None
        if reason:
            raise Interrupted(reason)

    def _changed(self, detail):
        """The upstream file is not the one the catalog pinned (D-4)."""
        self._discard_part()
        return TransferError("upstream file changed: %s" % detail)

    def _request(self, have):
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        if have > 0:
            headers["Range"] = "bytes=%d-" % have
        return urllib.request.Request(self.spec.url, headers=headers, method="GET")

    def _open(self, request):
        """The request path: policy, then the (injectable) opener, then the
        policy again on where the answer really came from."""
        check_url(request.full_url, self.allow_loopback_http, initial=True)
        for name in _STRIPPED_HEADERS:
            request.remove_header(name)
        response = self.opener(request, IO_TIMEOUT)
        geturl = getattr(response, "geturl", None)
        final = geturl() if callable(geturl) else None
        if final and final != request.full_url:
            try:
                check_url(final, self.allow_loopback_http, initial=False)
            except PolicyError:
                response.close()
                raise
        return response

    def _wait(self, seconds):
        if self.sleep is not None:
            self.sleep(seconds)
            self._check_stop()
            return
        end = time.monotonic() + seconds
        while True:
            self._check_stop()
            left = end - time.monotonic()
            if left <= 0:
                return
            time.sleep(min(left, 0.1))

    # -- the transfer --------------------------------------------------------
    def run(self):
        os.makedirs(self.dest_dir, exist_ok=True)
        self.resumed_from = self.have()
        failures = restarts = 0
        while True:
            self._check_stop()
            have = self.have()
            if have > self.spec.size:
                self._discard_part()        # cannot be a prefix of this file
                have = 0
            if have == self.spec.size:
                return self.part            # an earlier attempt already got it
            self._progressed = False
            try:
                if self._attempt(have):
                    return self.part
            except TransferError as err:
                if not err.retryable:
                    raise
                if self._progressed:
                    failures = 0            # bytes arrived: not a dead link
                failures += 1
                if failures > MAX_FAILURES:
                    raise TransferError("giving up after %d failures in a row: %s"
                                        % (MAX_FAILURES, err))
                delay = backoff_delay(failures)
                if self.on_retry:
                    self.on_retry(failures, delay, str(err))
                self._wait(delay)
            else:
                # The answer could not be used (a 416 below full size, a range
                # that did not line up): start over, but not forever.
                restarts += 1
                if restarts > 2:
                    raise TransferError("the download server keeps refusing to resume")

    def _attempt(self, have):
        """One connection. True when the file is complete; False to go again
        (a 416 restart, a mismatched range); raises TransferError otherwise."""
        try:
            response = self._open(self._request(have))
        except urllib.error.HTTPError as err:
            return self._handle_http_error(err, have)
        except (OSError, http.client.HTTPException) as err:
            raise TransferError("cannot reach the download server: %s" % err,
                                retryable=True)
        try:
            return self._stream(response, have)
        finally:
            try:
                response.close()
            except Exception:  # noqa: BLE001 - closing must never mask the cause
                pass

    def _handle_http_error(self, err, have):
        err.close()
        if err.code == 416:
            if have == self.spec.size:
                return True
            self._discard_part()            # our prefix is not valid: start over
            return False
        retryable = err.code == 429 or err.code >= 500
        raise TransferError("the download server answered HTTP %d" % err.code,
                            retryable=retryable)

    def _stream(self, response, have):
        status = _status_of(response)
        size = self.spec.size
        if status == 206:
            match = _CONTENT_RANGE.match(response.headers.get("Content-Range", "") or "")
            if match is None:
                self._discard_part()
                return False                # a 206 we cannot place: start over
            if match.group(3) != "*" and int(match.group(3)) != size:
                raise self._changed("the server reports %s bytes, the catalog %d"
                                    % (match.group(3), size))
            if int(match.group(1)) != have:
                self._discard_part()
                return False
            mode = "ab"
        elif status == 200:
            length = response.headers.get("Content-Length")
            if length is not None and length.isdigit() and int(length) != size:
                raise self._changed("the server sends %s bytes, the catalog %d"
                                    % (length, size))
            have, mode = 0, "wb"            # the server ignored the range
        else:
            raise TransferError("unexpected HTTP status %s" % status)

        try:
            out = self.open_part(self.part, mode)
        except OSError as err:
            raise TransferError("cannot write %s: %s" % (self.part, err))
        # `read1` returns what has arrived (at most CHUNK) instead of waiting
        # for a full chunk, so progress and pause stay current on a slow link.
        read = getattr(response, "read1", None) or response.read
        with out:
            while True:
                self._check_stop()
                try:
                    block = read(CHUNK)
                except (OSError, http.client.HTTPException) as err:
                    raise TransferError("the connection broke after %d bytes: %s"
                                        % (have, err), retryable=True)
                if not block:
                    break
                try:
                    out.write(block)
                except OSError as err:
                    raise TransferError("cannot write %s: %s" % (self.part, err))
                have += len(block)
                self._progressed = True
                if have > size:
                    out.close()
                    raise self._changed("more than the catalog's %d bytes arrived" % size)
                if self.on_progress:
                    self.on_progress(have)
        if have == 0:
            self._discard_part()
            raise TransferError("the server sent no data", retryable=True)
        if have < size:
            raise TransferError("the connection closed early, after %d of %d bytes"
                                % (have, size), retryable=True)
        return True


# ---------------------------------------------------------------------------
# Verify and atomic install
# ---------------------------------------------------------------------------

class InstallError(TransferError):
    """The bytes arrived but could not be made an installed asset. Never retried."""


MANIFEST_SUFFIX = ".manifest.json"

#: The four places the fault-injection matrix can stop an install (AC-22).
FAULT_POINTS = ("after_last_byte", "after_hash", "after_replace", "during_manifest")


def manifest_path(final_path):
    return final_path + MANIFEST_SUFFIX


def read_manifest(final_path):
    """The manifest next to an installed file, or None when absent or unreadable."""
    try:
        with open(manifest_path(final_path), "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def sha256_of(path, on_bytes=None):
    """SHA256 over the WHOLE file, streamed (one pass; D-4)."""
    digest = hashlib.sha256()
    done = 0
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            digest.update(block)
            done += len(block)
            if on_bytes:
                on_bytes(done)
    return digest.hexdigest()


def _mismatch(name, expected, actual):
    return ("sha256 mismatch for %s: expected %s..., got %s..."
            % (name, expected[:12], actual[:12]))


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _disk_free(path):
    return shutil.disk_usage(path).free


def _mib(n):
    return "%.1f MiB" % (n / 1048576.0)


def _write_manifest(asset, dest_dir, now, fault):
    """The manifest is the LAST thing written, via temp + replace; a fault
    anywhere inside leaves no manifest and no temp file behind."""
    main = asset.main_file
    final = os.path.join(dest_dir, main.name)
    doc = {"id": asset.id, "sha256": main.sha256, "size": main.size,
           "source_url": main.url, "commit": asset.commit, "installed_at": now(),
           "files": {f.name: f.sha256 for f in asset.files}}
    target = manifest_path(final)
    tmp = target + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=2)
        fault("during_manifest", main.name)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return doc


class Downloader:
    """Download, verify and install one asset. Synchronous: the job manager
    runs it on a thread.

    Order of effects for every file (BR-2, NFR-1): bytes go to `{name}.part`;
    only after the size and the SHA256 of the whole `.part` match does
    `os.replace` give it the shell-visible name; the manifest is written last,
    after every file of the asset is in place. A voice installs `.onnx.json`
    first and `.onnx` last, so it never appears in the shell voice list
    without its config.

    Seams: `opener`, `sleep`, `allow_loopback_http`, `open_part` (as
    `Transfer`); `disk_free(path)`; `now()`; and `fault(point, file_name)`,
    called at each of `FAULT_POINTS` (a test raises from it; production passes
    nothing).
    """

    def __init__(self, opener=None, sleep=None, allow_loopback_http=False,
                 disk_free=None, now=None, fault=None, open_part=open):
        self.opener = opener
        self.sleep = sleep
        self.allow_loopback_http = allow_loopback_http
        self.disk_free = disk_free or _disk_free
        self.now = now or _now
        self.fault = fault or (lambda point, name: None)
        self.open_part = open_part

    def _remaining(self, asset, dest_dir):
        need = 0
        for spec in asset.files:
            try:
                have = os.path.getsize(os.path.join(dest_dir, spec.name) + ".part")
            except OSError:
                have = 0
            need += max(spec.size - have, 0)
        return need

    def download(self, asset, dest_dir, stop=None, on_progress=None,
                 on_retry=None, on_phase=None, created=None):
        """Returns the manifest dict. Raises TransferError (network, policy,
        write errors), InstallError (space, hash, rename, manifest) or
        Interrupted (pause/cancel; nothing is rolled back, the caller decides).

        `on_progress(done, total, file_name)` spans every file of the asset;
        `on_phase("downloading" | "verifying", file_name)` marks the phase.
        `created` is a list the caller owns: it collects the files this job put
        in place, so a later cancel can remove exactly those (see `rollback`).
        """
        os.makedirs(dest_dir, exist_ok=True)
        need = self._remaining(asset, dest_dir)
        free = self.disk_free(dest_dir)
        if free < need:                     # refused BEFORE any connection (AC-30)
            raise InstallError("not enough free disk space: %s needed, %s free"
                               % (_mib(need), _mib(free)))
        total = asset.size_bytes
        created = created if created is not None else []
        completed = 0
        try:
            for spec in asset.files:
                final = os.path.join(dest_dir, spec.name)
                existed = os.path.exists(final)
                if on_phase:
                    on_phase("downloading", spec.name)
                progress = None
                if on_progress:
                    def progress(have, base=completed, name=spec.name):
                        on_progress(base + have, total, name)
                transfer = Transfer(
                    spec, dest_dir, opener=self.opener, stop=stop, sleep=self.sleep,
                    on_retry=on_retry, allow_loopback_http=self.allow_loopback_http,
                    open_part=self.open_part, on_progress=progress)
                if progress:
                    progress(transfer.have())
                part = transfer.run()
                self.fault("after_last_byte", spec.name)
                self._verify_and_replace(spec, part, final, on_phase, stop)
                if not existed:
                    created.append(final)
                completed += spec.size
        except Interrupted:
            raise
        except BaseException:
            self.rollback(created)
            del created[:]
            raise
        # Every file is in place and verified: from here a failure leaves an
        # installed asset with no manifest (`verified: false`, AC-22), never a
        # rollback of good bytes.
        self.fault("after_replace", asset.main_file.name)
        return _write_manifest(asset, dest_dir, self.now, self.fault)

    def _verify_and_replace(self, spec, part, final, on_phase, stop=None):
        if on_phase:
            on_phase("verifying", spec.name)
        size = os.path.getsize(part)
        if size != spec.size:
            os.remove(part)
            raise InstallError("upstream file changed: %s is %d bytes, the catalog says %d"
                               % (spec.name, size, spec.size))

        def check_stop(_done):
            reason = stop() if stop else None
            if reason:                      # pause/cancel reach a long hash too
                raise Interrupted(reason)

        actual = sha256_of(part, check_stop)
        if actual != spec.sha256:
            os.remove(part)                 # a bad mirror would loop: no auto-retry (D-4)
            raise InstallError(_mismatch(spec.name, spec.sha256, actual))
        self.fault("after_hash", spec.name)
        try:
            os.replace(part, final)
        except OSError as err:
            raise InstallError("could not move the verified %s into place: %s"
                               % (spec.name, err))

    @staticmethod
    def rollback(created):
        """Remove files THIS job put in place (a voice .onnx.json whose .onnx
        failed), so nothing half-installed outlives a failure. Files that
        existed before the job are never touched."""
        for path in created:
            for victim in (path, manifest_path(path)):
                try:
                    os.remove(victim)
                except OSError:
                    pass

    def verify_existing(self, asset, dest_dir, on_progress=None):
        """Hash hand-placed files against the catalog (AC-24). On a full match
        write the manifest; on any mismatch report expected/actual prefixes and
        leave every file byte-for-byte untouched. Returns
        `{"ok": bool, "message": str, "files": [{name, ok, message}]}`."""
        results, all_ok = [], True
        total, done = asset.size_bytes, 0
        for spec in asset.files:
            path = os.path.join(dest_dir, spec.name)
            if not os.path.isfile(path):
                results.append({"name": spec.name, "ok": False,
                                "message": "%s is not installed" % spec.name})
                all_ok = False
                continue
            on_bytes = None
            if on_progress:
                def on_bytes(n, base=done, name=spec.name):
                    on_progress(base + n, total, name)
            actual = sha256_of(path, on_bytes)
            done += spec.size
            good = actual == spec.sha256
            all_ok = all_ok and good
            results.append({"name": spec.name, "ok": good,
                            "message": "ok" if good else _mismatch(spec.name, spec.sha256, actual)})
        if not all_ok:
            bad = [r["message"] for r in results if not r["ok"]]
            return {"ok": False, "files": results, "message": "; ".join(bad)}
        try:
            _write_manifest(asset, dest_dir, self.now, self.fault)
        except OSError as err:
            return {"ok": False, "files": results,
                    "message": "the files match but the manifest could not be written: %s" % err}
        return {"ok": True, "files": results, "message": "%s matches the catalog" % asset.id}

    @staticmethod
    def discard_parts(asset, dest_dir):
        """Delete every `.part` of an asset (cancel)."""
        for spec in asset.files:
            try:
                os.remove(os.path.join(dest_dir, spec.name) + ".part")
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Jobs: one background download per asset id
# ---------------------------------------------------------------------------

log = logging.getLogger("console.voice_assets")

STATE_NOT_INSTALLED = "not_installed"
STATE_PARTIAL = "partial"
STATE_DOWNLOADING = "downloading"
STATE_PAUSED = "paused"
STATE_RETRYING = "retrying"
STATE_VERIFYING = "verifying"
STATE_INSTALLED = "installed"
STATE_FAILED = "failed"

#: A job in one of these holds the id: a second Download returns it (AC-11).
LIVE_STATES = (STATE_DOWNLOADING, STATE_RETRYING, STATE_VERIFYING, STATE_PAUSED)
_RUNNING_STATES = (STATE_DOWNLOADING, STATE_RETRYING, STATE_VERIFYING)

#: Speed is measured over this window of clock time; samples are thinned to
#: one per SAMPLE_INTERVAL. `done` itself is always live, never a stale copy.
SPEED_WINDOW = 5.0
SAMPLE_INTERVAL = 0.25


def disk_state(asset, dest_dir):
    """What the disk alone says about an asset: `installed` (the shell-visible
    main file exists), `partial` (a `.part` exists) or `not_installed`, with
    the bytes on disk. Job state is layered on top by the manager."""
    main_final = os.path.join(dest_dir, asset.main_file.name)
    present = parts = 0
    any_part = False
    for spec in asset.files:
        final = os.path.join(dest_dir, spec.name)
        if os.path.isfile(final):
            present += os.path.getsize(final)
        try:
            parts += os.path.getsize(final + ".part")
            any_part = True
        except OSError:
            pass
    if os.path.isfile(main_final):
        return {"state": STATE_INSTALLED, "done": present}
    if any_part:
        return {"state": STATE_PARTIAL, "done": parts}
    return {"state": STATE_NOT_INSTALLED, "done": 0}


def _part_bytes(asset, dest_dir):
    total = 0
    for spec in asset.files:
        try:
            total += os.path.getsize(os.path.join(dest_dir, spec.name) + ".part")
        except OSError:
            pass
    return total


class Job:
    """One asset's download. Fields are read through `snapshot()`; `history`
    lists every state it has been in (diagnostics, and how tests observe the
    order downloading, verifying, installed)."""

    def __init__(self, asset, clock):
        self.asset = asset
        self.clock = clock
        self.thread = None
        self.created = []               # files this job put in place (for cancel)
        self.state = STATE_DOWNLOADING
        self.history = [STATE_DOWNLOADING]
        self.done = 0
        self.total = asset.size_bytes
        self.file = asset.files[0].name
        self.resumed_from = 0
        self.error = ""
        self._cond = threading.Condition()
        self._pause = threading.Event()
        self._cancel = threading.Event()
        self._samples = []

    # -- called from the transfer thread --------------------------------------
    def _set_state(self, state):
        with self._cond:
            if state != self.state:
                self.state = state
                self.history.append(state)
            self._cond.notify_all()

    def stop_reason(self):
        if self._cancel.is_set():
            return "cancel"
        if self._pause.is_set():
            return "pause"
        return None

    def on_progress(self, done, total, name):
        now = self.clock()
        with self._cond:
            self.done, self.total, self.file = done, total, name
            samples = self._samples
            if len(samples) > 1 and now - samples[-1][0] < SAMPLE_INTERVAL:
                samples[-1] = (now, done)
            else:
                samples.append((now, done))
            while len(samples) > 2 and now - samples[0][0] > SPEED_WINDOW:
                samples.pop(0)
            if self.state == STATE_RETRYING:    # bytes are flowing again
                self.state = STATE_DOWNLOADING
                self.history.append(STATE_DOWNLOADING)
                self._cond.notify_all()

    def on_phase(self, phase, name):
        with self._cond:
            self.file = name
        self._set_state(STATE_VERIFYING if phase == "verifying" else STATE_DOWNLOADING)

    def on_retry(self, failures, delay, message):
        log.info("voice asset %s: retry %d in %.1f s: %s",
                 self.asset.id, failures, delay, message)
        self._set_state(STATE_RETRYING)

    # -- read by anyone ---------------------------------------------------------
    def snapshot(self):
        with self._cond:
            speed, eta = 0, None
            samples = self._samples
            if len(samples) >= 2 and self.state in _RUNNING_STATES:
                (t0, d0), (t1, d1) = samples[0], samples[-1]
                if t1 > t0 and self.clock() - t1 <= SPEED_WINDOW:
                    speed = max(int((d1 - d0) / (t1 - t0)), 0)
            if speed > 0:                       # rounded up: 0 s would mean "done"
                eta = int(math.ceil((self.total - self.done) / float(speed)))
            return {"id": self.asset.id, "state": self.state, "done": self.done,
                    "total": self.total, "speed_bps": speed, "eta_s": eta,
                    "resumed_from": self.resumed_from, "file": self.file,
                    "error": self.error}

    def wait_state(self, state, timeout=10.0):
        """Block until the job is in `state` (an event wait, not a poll)."""
        with self._cond:
            return self._cond.wait_for(lambda: self.state == state, timeout)


class Manager:
    """The jobs of one repo root: at most one per asset id, each on its own
    daemon thread. Methods return JSON-ready snapshots and never block on the
    network; the Settings tab polls them.

    Pause drops the connection and keeps the `.part`; resume reconnects with
    Range; cancel stops and deletes the `.part` (and any file this job put in
    place). After a console restart nothing is in memory: state comes from the
    disk (`partial`) and Download resumes by Range (AC-20).
    """

    def __init__(self, repo_root, catalog=None, downloader=None, clock=time.monotonic):
        self.repo_root = repo_root
        self.catalog = catalog or load_catalog()
        self.downloader = downloader or Downloader()
        self.clock = clock
        self._jobs = {}
        self._lock = threading.Lock()

    def dest_dir(self, asset):
        return os.path.join(self.repo_root, asset.dir_rel)

    def _asset(self, asset_id):
        asset = self.catalog.get(asset_id) if isinstance(asset_id, str) else None
        if asset is None:
            raise KeyError(asset_id)        # an id, never a URL or a path (BR-9)
        return asset

    def job(self, asset_id):
        with self._lock:
            return self._jobs.get(asset_id)

    # -- the four verbs ---------------------------------------------------------
    def download(self, asset_id):
        asset = self._asset(asset_id)
        with self._lock:
            job = self._jobs.get(asset_id)
            if job is not None and job.state in LIVE_STATES:
                return job.snapshot()
            if disk_state(asset, self.dest_dir(asset))["state"] == STATE_INSTALLED:
                return self._disk_snapshot(asset)   # Verify or Delete, not a silent re-download
            job = self._jobs[asset_id] = Job(asset, self.clock)
        self._start(job)
        return job.snapshot()

    def pause(self, asset_id):
        job = self.job(self._asset(asset_id).id)
        if job is not None and job.state in _RUNNING_STATES:
            job._pause.set()
        return self.snapshot(asset_id)

    def resume(self, asset_id):
        job = self.job(self._asset(asset_id).id)
        if job is not None and job.state == STATE_PAUSED:
            job._pause.clear()
            job._set_state(STATE_DOWNLOADING)
            self._start(job)
        return self.snapshot(asset_id)

    def cancel(self, asset_id):
        asset = self._asset(asset_id)
        job = self.job(asset.id)
        if job is not None and job.state in _RUNNING_STATES:
            job._cancel.set()               # the thread cleans up and ends
            return job.snapshot()
        if job is not None and job.state == STATE_INSTALLED:
            return job.snapshot()           # nothing to cancel
        self._discard(asset, job)
        return self.snapshot(asset_id)

    def snapshot(self, asset_id):
        asset = self._asset(asset_id)
        job = self.job(asset.id)
        return job.snapshot() if job is not None else self._disk_snapshot(asset)

    def stop_all(self, timeout=10.0):
        """Pause every running job and wait for its thread (shutdown, tests)."""
        with self._lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            job._pause.set()
        for job in jobs:
            if job.thread is not None:
                job.thread.join(timeout)

    # -- internals ----------------------------------------------------------------
    def _disk_snapshot(self, asset):
        found = disk_state(asset, self.dest_dir(asset))
        return {"id": asset.id, "state": found["state"], "done": found["done"],
                "total": asset.size_bytes, "speed_bps": 0, "eta_s": None,
                "resumed_from": 0, "file": "", "error": ""}

    def _discard(self, asset, job):
        dest = self.dest_dir(asset)
        if job is not None:
            Downloader.rollback(job.created)
        Downloader.discard_parts(asset, dest)
        with self._lock:
            if self._jobs.get(asset.id) is job:
                self._jobs.pop(asset.id, None)
        log.info("voice asset %s: cancelled, partial files removed", asset.id)

    def _start(self, job):
        thread = threading.Thread(target=self._run, args=(job,),
                                  name="voice-asset-" + job.asset.id, daemon=True)
        job.thread = thread
        thread.start()

    def _run(self, job):
        asset = job.asset
        dest = self.dest_dir(asset)
        job.resumed_from = job.done = _part_bytes(asset, dest)
        job.on_progress(job.done, job.total, job.file)
        log.info("voice asset %s: download started (%d of %d bytes already on disk)",
                 asset.id, job.resumed_from, job.total)
        try:
            self.downloader.download(
                asset, dest, stop=job.stop_reason, on_progress=job.on_progress,
                on_retry=job.on_retry, on_phase=job.on_phase, created=job.created)
        except Interrupted as stop:
            if stop.reason == "cancel":
                job._set_state(STATE_NOT_INSTALLED)
                self._discard(asset, job)
            else:
                log.info("voice asset %s: paused at %d bytes", asset.id, job.done)
                job._set_state(STATE_PAUSED)
        except TransferError as err:
            log.warning("voice asset %s: failed: %s", asset.id, err)
            job.error = str(err)
            job._set_state(STATE_FAILED)
        except Exception as err:  # noqa: BLE001 - a job thread must never die silently
            log.exception("voice asset %s: unexpected failure", asset.id)
            job.error = "unexpected error: %s" % err
            job._set_state(STATE_FAILED)
        else:
            job.done = job.total
            log.info("voice asset %s: finished (%d bytes verified and installed)",
                     asset.id, job.total)
            job._set_state(STATE_INSTALLED)

    def forget(self, asset_id):
        """Drop a finished or failed job (after a delete), so the id reads
        from the disk again."""
        with self._lock:
            job = self._jobs.get(asset_id)
            if job is not None and job.state not in LIVE_STATES:
                self._jobs.pop(asset_id, None)


# ---------------------------------------------------------------------------
# One Manager per repo root
# ---------------------------------------------------------------------------

_MANAGERS = {}
_MANAGERS_LOCK = threading.Lock()


def _root_key(repo_root):
    return os.path.normcase(os.path.abspath(repo_root))


def manager_for(repo_root, factory=None):
    """The one `Manager` of this repo root, created on first use.

    A job must outlive the request that started it, and the CLI rebuilds its
    route table on every call, so the manager cannot live in a route closure:
    it lives here. `factory(repo_root)` is only for tests (a manager wired to a
    local server); production passes nothing and gets the real downloader.
    """
    key = _root_key(repo_root)
    with _MANAGERS_LOCK:
        manager = _MANAGERS.get(key)
        if manager is None:
            manager = _MANAGERS[key] = (factory or Manager)(repo_root)
        return manager


def drop_manager(repo_root):
    """Forget a root's manager after pausing its jobs and joining their threads
    (shutdown and tests). Partial files stay on disk, so a later manager
    resumes them."""
    with _MANAGERS_LOCK:
        manager = _MANAGERS.pop(_root_key(repo_root), None)
    if manager is not None:
        manager.stop_all()


# ---------------------------------------------------------------------------
# Inventory: what exists, what is verified, what is in use, what is loaded
# ---------------------------------------------------------------------------

#: The inventory is read-only and must stay quick (NFR-4): the one outbound
#: call it makes is to the local shell, capped here (AC-7).
INVENTORY_BRIDGE_TIMEOUT = 1.5

_MODEL_SUFFIX = ".bin"
_MODEL_PREFIX = "ggml-"
_VOICE_SUFFIX = ".onnx"


def _scan(directory, suffix, prefix=""):
    """File names the shell would treat as an asset: right extension (so
    `.part`, `.manifest.json` and `.onnx.json` never match), a safe name."""
    try:
        names = os.listdir(directory)
    except OSError:
        return []
    return sorted(n for n in names
                  if n.endswith(suffix) and n.startswith(prefix) and SAFE_NAME.match(n)
                  and os.path.isfile(os.path.join(directory, n)))


def resolve_model_in_use(stt_dir, wanted):
    """The model file the shell will use: `ggml-{wanted}.bin` when present,
    otherwise the smallest `ggml-*.bin` (`stt.rs` `resolve_model`)."""
    wanted = (wanted or "").strip()
    if wanted and os.path.isfile(os.path.join(stt_dir, "ggml-%s.bin" % wanted)):
        return "ggml-%s.bin" % wanted
    sized = []
    for name in _scan(stt_dir, _MODEL_SUFFIX, _MODEL_PREFIX):
        sized.append((os.path.getsize(os.path.join(stt_dir, name)), name))
    return min(sized)[1] if sized else ""


def resolve_voice_in_use(tts_dir, wanted):
    """The voice file the shell will use: `{wanted}.onnx` when present,
    otherwise the first by sorted name; a blank setting is the first
    (`piper::voice`)."""
    wanted = (wanted or "").strip()
    if wanted and os.path.isfile(os.path.join(tts_dir, wanted + _VOICE_SUFFIX)):
        return wanted + _VOICE_SUFFIX
    names = _scan(tts_dir, _VOICE_SUFFIX)
    return names[0] if names else ""


def installed_voices(repo_root):
    """Names (no `.onnx`) of the voices the shell could speak with, sorted."""
    tts_dir = os.path.join(repo_root, TTS_DIR_REL)
    return [n[:-len(_VOICE_SUFFIX)] for n in _scan(tts_dir, _VOICE_SUFFIX)]


def _is_verified(asset, dest_dir):
    """True only when every file is present and the manifest written at
    install agrees with the catalog and with the size on disk. A hand-placed
    file has no manifest, so it is `installed` but not `verified` (AC-5)."""
    for spec in asset.files:
        if not os.path.isfile(os.path.join(dest_dir, spec.name)):
            return False
    main = asset.main_file
    final = os.path.join(dest_dir, main.name)
    manifest = read_manifest(final)
    if not manifest:
        return False
    return (manifest.get("sha256") == main.sha256
            and manifest.get("size") == main.size == os.path.getsize(final))


def _free_bytes(repo_root, disk_free):
    probe = os.path.join(repo_root, "desktop")
    while probe and not os.path.isdir(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    try:
        return int((disk_free or _disk_free)(probe))
    except OSError:
        return 0


def _shell_view(repo_root, opener, timeout):
    from . import native_bridge
    answer = native_bridge.capabilities(repo_root, opener=opener, timeout=timeout)
    if not answer.get("ok"):
        return {"reachable": False, "reason": answer.get("reason", "shell not running")}
    caps = answer.get("caps") or {}
    return {"reachable": True,
            "speak_backend": caps.get("speak_backend", ""),
            "speak_voice_in_use": caps.get("speak_voice_in_use", ""),
            "stt_model": caps.get("stt_model", ""),
            "loaded_model": caps.get("loaded_model", "")}


def _row(asset, dest_dir, snap, in_use_file, loaded_file):
    main = asset.main_file.name
    installed = snap["state"] == STATE_INSTALLED
    row = dict(asset.public(), custom=False, name=main, state=snap["state"],
               size=snap["done"] if snap["state"] in (STATE_INSTALLED, STATE_PARTIAL) else 0,
               verified=installed and _is_verified(asset, dest_dir),
               in_use=installed and main == in_use_file,
               loaded=installed and bool(loaded_file) and main == loaded_file)
    for key in ("done", "total", "speed_bps", "eta_s", "resumed_from", "file", "error"):
        row[key] = snap[key]
    return row


def _custom_row(kind, name, dest_dir, in_use_file, loaded_file):
    size = os.path.getsize(os.path.join(dest_dir, name))
    stem = name[len(_MODEL_PREFIX):-len(_MODEL_SUFFIX)] if kind == KIND_STT \
        else name[:-len(_VOICE_SUFFIX)]
    return {"id": stem, "kind": kind, "label": name, "hint": "", "license": "",
            "size_bytes": size, "custom": True, "name": name, "state": STATE_INSTALLED,
            "size": size, "verified": False, "in_use": name == in_use_file,
            "loaded": kind == KIND_STT and bool(loaded_file) and name == loaded_file,
            "done": size, "total": size, "speed_bps": 0, "eta_s": None,
            "resumed_from": 0, "file": "", "error": ""}


def inventory(repo_root, catalog=None, manager=None, settings=None, opener=None,
              disk_free=None, bridge_timeout=INVENTORY_BRIDGE_TIMEOUT):
    """Everything the Settings manager shows, with no outbound internet call.

    The console scans `desktop/stt` and `desktop/tts` itself (it must work
    with the shell down, and only it writes manifests); the shell adds what
    only it knows: the model it has loaded. `settings` supplies `stt_model`
    and `speak_voice` (defaults to the merged assistant settings).
    """
    catalog = catalog or load_catalog()
    if settings is None:
        from . import assistant_config
        settings = assistant_config.settings(repo_root)
    stt_dir = os.path.join(repo_root, STT_DIR_REL)
    tts_dir = os.path.join(repo_root, TTS_DIR_REL)
    shell = _shell_view(repo_root, opener, bridge_timeout)
    in_use = {KIND_STT: resolve_model_in_use(stt_dir, settings.get("stt_model", "")),
              KIND_VOICE: resolve_voice_in_use(tts_dir, settings.get("speak_voice", ""))}
    loaded = shell.get("loaded_model", "") if shell["reachable"] else ""
    rows, listed = [], set()
    for asset in catalog.assets:
        dest = os.path.join(repo_root, asset.dir_rel)
        snap = manager.snapshot(asset.id) if manager else \
            dict(disk_state(asset, dest), total=asset.size_bytes, speed_bps=0, eta_s=None,
                 resumed_from=0, file="", error="")
        rows.append(_row(asset, dest, snap, in_use[asset.kind],
                         loaded if asset.kind == KIND_STT else ""))
        listed.add((asset.kind, asset.main_file.name))
    for kind, directory, suffix, prefix in ((KIND_STT, stt_dir, _MODEL_SUFFIX, _MODEL_PREFIX),
                                            (KIND_VOICE, tts_dir, _VOICE_SUFFIX, "")):
        for name in _scan(directory, suffix, prefix):
            if (kind, name) not in listed:
                rows.append(_custom_row(kind, name, directory, in_use[kind],
                                        loaded if kind == KIND_STT else ""))
    return {"assets": rows, "free_bytes": _free_bytes(repo_root, disk_free), "shell": shell}


# ---------------------------------------------------------------------------
# Delete: a destructive action with its own safety rules
# ---------------------------------------------------------------------------

_TOMBSTONE = ".deleting"


def _refusal(code, reason):
    return {"ok": False, "error": code, "reason": reason}


def _confined(path, directory):
    """True when `path`, with every symlink and junction resolved, sits inside
    `directory` (also resolved) and is not the directory itself (NFR-3)."""
    real_dir = os.path.normcase(os.path.realpath(directory))
    real = os.path.normcase(os.path.realpath(path))
    try:
        return os.path.commonpath([real, real_dir]) == real_dir and real != real_dir
    except ValueError:                      # a different drive
        return False


def _files_of(row, catalog, directory):
    """Every path that belongs to an asset: its files, its manifest, its parts."""
    asset = catalog.get(row["id"]) if not row["custom"] else None
    names = [f.name for f in reversed(asset.files)] if asset else [row["name"]]
    names.append(row["name"] + MANIFEST_SUFFIX)
    names += [n + ".part" for n in names[:-1]]
    seen, paths = set(), []
    for name in names:
        path = os.path.join(directory, name)
        if name not in seen and os.path.lexists(path):
            seen.add(name)
            paths.append(path)
    return paths


def delete_asset(repo_root, name_or_id, catalog=None, manager=None, settings=None,
                 opener=None, rename=os.rename, remove=os.remove):
    """Delete one installed (or partial) asset.

    Never raises for an expected refusal: returns `{"ok": False, "error":
    code, "reason": sentence}` (a route answers these 4xx, never 5xx). Codes:
    `bad_name`, `unknown`, `refused` (in use, loaded, downloading), `outside`
    (a path that does not resolve inside `desktop/stt` or `desktop/tts`),
    `locked` (the OS refused; nothing was changed).

    The name must be a safe name AND match an inventory row by id or file
    name, so nothing outside what the inventory lists can be named. Removal is
    rename-to-tombstone first, then unlink; if any rename fails (a Windows
    lock raises PermissionError) every rename already done is undone, so an
    asset is never half deleted. `rename` and `remove` are seams for tests.
    """
    if not isinstance(name_or_id, str) or not SAFE_NAME.match(name_or_id) \
            or name_or_id in (".", ".."):
        return _refusal("bad_name", "That is not a valid model or voice name.")
    catalog = catalog or load_catalog()
    found = inventory(repo_root, catalog, manager=manager, settings=settings, opener=opener)
    matches = [r for r in found["assets"] if name_or_id in (r["id"], r["name"])]
    if not matches:
        return _refusal("unknown", "There is no model or voice called %s." % name_or_id)
    if len(matches) > 1:
        return _refusal("bad_name", "%s is ambiguous; use the file name." % name_or_id)
    row = matches[0]
    label = row["name"]
    if row["state"] in LIVE_STATES:
        return _refusal("refused", "%s is being downloaded; cancel the download first." % label)
    if row["loaded"]:
        return _refusal("refused", "%s is loaded in the speech engine right now; choose "
                        "another model and wait for it to load, then delete this one." % label)
    if row["in_use"]:
        what = "speech model" if row["kind"] == KIND_STT else "voice"
        return _refusal("refused", "%s is the %s in use; choose another before deleting it."
                        % (label, what))
    directory = os.path.join(repo_root, STT_DIR_REL if row["kind"] == KIND_STT else TTS_DIR_REL)
    paths = _files_of(row, catalog, directory)
    if not paths:
        return {"ok": True, "id": row["id"], "removed": [],
                "message": "Nothing to delete for %s." % label}
    for path in paths:
        if not _confined(path, directory):
            return _refusal("outside", "%s does not resolve inside %s; nothing was deleted."
                            % (os.path.basename(path), os.path.relpath(directory, repo_root)))
    done = []                               # (original, tombstone), for rollback
    for path in paths:
        tomb = path + _TOMBSTONE
        try:
            rename(path, tomb)
        except OSError as err:
            for original, parked in reversed(done):
                try:
                    rename(parked, original)
                except OSError:
                    log.error("voice asset delete: could not restore %s", original)
            log.warning("voice asset %s: delete refused by the OS on %s: %s",
                        row["id"], os.path.basename(path), err)
            return _refusal("locked", "Could not delete %s: another program is using it "
                            "(%s). Close it, or stop the speech engine, and try again. "
                            "Nothing was changed." % (os.path.basename(path), err.strerror or err))
        done.append((path, tomb))
    for _original, parked in done:
        try:
            remove(parked)
        except OSError as err:              # already invisible to the shell
            log.warning("voice asset delete: left %s behind: %s", parked, err)
    if manager is not None:
        manager.forget(row["id"])
    names = [os.path.basename(p) for p, _t in done]
    log.info("voice asset %s: deleted %s", row["id"], ", ".join(names))
    return {"ok": True, "id": row["id"], "removed": names,
            "message": "Deleted %s." % label}
