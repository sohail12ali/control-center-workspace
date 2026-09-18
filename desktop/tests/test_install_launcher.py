"""install-launcher.sh — macOS `.app` skeleton + Linux `.desktop` file.

Runs the real script under `bash` against scratch `HOME`/target dirs, so the
assertions are on files it actually wrote, not a mock. `--target` lets one
runner validate both code paths' file structure: this repo's CI only puts
the shell-script leg on `ubuntu-latest` (no macOS hardware), but the `.app`
skeleton is pure file/plist writing with no macOS-only syscall, so its
structure is provable there too — build-only coverage, stated explicitly;
no Gatekeeper/mic-permission hardware behaviour is claimed.
"""

import os
import shutil
import subprocess

import pytest

DESKTOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(DESKTOP, "install-launcher.sh")

# Resolved once, to a full path: on Windows, a bare "bash" handed to
# subprocess can resolve to the WSL launcher stub (`System32\bash.exe`)
# instead of Git Bash, even when `shutil.which` itself finds Git Bash first
# — the two use different search order. The full path sidesteps the
# ambiguity everywhere else in this file.
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="install-launcher.sh needs bash")


def run_script(tmp_path, target, extra_args=()):
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["XDG_DATA_HOME"] = str(tmp_path / ".local" / "share")
    args = [BASH, SCRIPT, "--target=%s" % target] + list(extra_args)
    return subprocess.run(
        args, cwd=DESKTOP, env=env, capture_output=True, text=True, timeout=30
    )


class TestLinuxDesktopFile:
    def test_writes_a_valid_desktop_entry(self, tmp_path):
        result = run_script(tmp_path, "linux")
        assert result.returncode == 0, result.stderr

        desktop_file = (
            tmp_path / ".local" / "share" / "applications" / "delivery-console.desktop"
        )
        assert desktop_file.is_file()
        text = desktop_file.read_text(encoding="utf-8")
        assert "[Desktop Entry]" in text
        assert "Type=Application" in text
        assert "Exec=" in text
        assert "Terminal=false" in text

    def test_rerun_overwrites_cleanly(self, tmp_path):
        run_script(tmp_path, "linux")
        result = run_script(tmp_path, "linux")
        assert result.returncode == 0, result.stderr


class TestMacosAppSkeleton:
    def test_writes_info_plist_with_required_keys(self, tmp_path):
        app_dir = tmp_path / "Delivery Console.app"
        result = run_script(tmp_path, "macos", extra_args=[str(app_dir)])
        assert result.returncode == 0, result.stderr

        plist = app_dir / "Contents" / "Info.plist"
        assert plist.is_file()
        text = plist.read_text(encoding="utf-8")
        assert "com.noble.deliveryconsole" in text
        assert "NSMicrophoneUsageDescription" in text
        assert "<key>LSUIElement</key>" in text
        assert (app_dir / "Contents" / "MacOS").is_dir()


class TestUnsupportedTarget:
    def test_rejects_an_unknown_target(self, tmp_path):
        result = run_script(tmp_path, "windows")
        assert result.returncode != 0
