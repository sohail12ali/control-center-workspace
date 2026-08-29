#!/usr/bin/env python3
"""MCP entry point. Exposes the Delivery Console's verbs to any MCP client.

    python console/mcp_server.py

Stdlib only, like the rest of the console — no SDK, no install step.

## Wiring it up

Claude Code and Cursor both read a project `.mcp.json`:

    {
      "mcpServers": {
        "console": {
          "command": "python",
          "args": ["console/mcp_server.py"]
        }
      }
    }

The server resolves the workspace root the same way the CLI does, so it works
from whatever directory the client happens to launch it in.

## The rule that matters

**stdout carries protocol messages and nothing else.** A stray print corrupts
the stream, and the client reports a parse error instead of the real problem.
Anything diagnostic goes to stderr — which is why this file reconfigures the
streams before importing anything that might be tempted to print.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import dotenv, mcp  # noqa: E402
from server.paths import RepoRootError, find_repo_root  # noqa: E402


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    start = argv[0] if argv else None
    try:
        repo_root = find_repo_root(start)
    except RepoRootError as exc:
        print("mcp_server: %s" % exc, file=sys.stderr)
        return 1

    # Line buffering keeps a reply from sitting in a buffer while the client
    # waits for it; the server also flushes explicitly after every message.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:  # pragma: no cover - very old interpreters
        pass

    # An MCP client launches this with whatever environment it happens to have,
    # which is often not the shell you set your keys in — so the file is the
    # only reliable source here.
    loaded = dotenv.load(repo_root)
    if loaded:
        print("mcp_server: loaded %d variable(s) from .env" % len(loaded),
              file=sys.stderr)

    print("mcp_server: serving %s" % repo_root, file=sys.stderr)
    mcp.Server(repo_root).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
