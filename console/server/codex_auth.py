"""Codex credentials for one chat.

Codex reads `auth.json` inside `CODEX_HOME`, not the process environment.
When `OPENAI_API_KEY` is set, this writes that file into a per-chat directory
under `console/.cache/` so the user's `~/.codex` is left alone. With no key,
the child inherits the existing Codex login. With neither, the backend says
so before the process starts.
"""

import json
import os


def host_auth_file():
    home = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
    return os.path.join(home, "auth.json")


def has_api_key():
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def has_host_login():
    path = host_auth_file()
    try:
        return os.path.isfile(path) and os.path.getsize(path) > 0
    except OSError:
        return False


def missing_reason():
    """Empty when a key or a host login can start Codex."""
    if has_api_key() or has_host_login():
        return ""
    return ("Codex has no credentials. Set OPENAI_API_KEY in the workspace "
            ".env, or sign in with `codex` so %s exists." % host_auth_file())


def child_env(repo_root, session_id):
    """`CODEX_HOME` for this chat when an API key is set, else nothing.

    Nothing means the child keeps the user's own Codex home. The key value
    is written only into the per-chat `auth.json`, never into a transcript.
    """
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or not session_id or not repo_root:
        return {}
    home = os.path.join(repo_root, "console", ".cache", "codex-homes", session_id)
    os.makedirs(home, exist_ok=True)
    path = os.path.join(home, "auth.json")
    body = json.dumps({"OPENAI_API_KEY": key}) + "\n"
    current = ""
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                current = fh.read()
        except OSError:
            current = ""
    if current != body:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
    return {"CODEX_HOME": home}
