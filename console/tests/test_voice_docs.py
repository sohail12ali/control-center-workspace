"""T-031-33: the docs and the compatibility promises (AC-71, AC-72, AC-73, NFR-2, NFR-14).

Text checks, so they fail when a document stops agreeing with the feature it
describes, plus the "nothing else moved" pins: no new dependency, and files a
script placed or a settings file written before the device keys existed still
behave exactly as before.
"""

import hashlib
import os
import tomllib

from server import assistant_config
from server.voice_assets import Asset, AssetFile, Catalog, inventory

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


# --- AC-71: the docs and the Settings strings ---------------------------------

def test_the_readme_documents_the_manager_the_catalog_and_its_refresh_procedure():
    text = read("console", "README.md")
    for needle in ("Speech models and voices", "console/config/voice-assets.toml",
                   "Refreshing the catalog", "hf-lfs-oid", "computed-pinned",
                   "(not connected)", "(live)", "(restart needed)", "(next chat)"):
        assert needle in text, needle


def test_the_readme_says_what_is_not_included_and_the_licence_and_the_limits():
    text = read("console", "README.md")
    for needle in ("whisper-server", "get-piper.ps1", "get-whisper.ps1",
                   "CC BY-NC-SA 4.0", "en_US-ryan-medium", "untested"):
        assert needle in text, needle


def test_assistant_toml_points_at_settings_and_the_catalog_for_the_two_keys():
    text = read("console", "config", "assistant.toml")
    assert text.count("Speech models") >= 2
    assert text.count("voice-assets.toml") >= 2


def test_assistant_toml_changed_only_in_comments_for_the_two_keys():
    parsed = tomllib.loads(read("console", "config", "assistant.toml"))["assistant"]
    assert parsed["speak_voice"] == "" and parsed["stt_model"] == "base.en"
    assert parsed["speak_rate_percent"] == 100


def test_the_desktop_readme_lists_the_new_modules_routes_and_script():
    text = read("desktop", "README.md")
    for needle in ("devices.rs", "voice_test.rs", "get-whisper.ps1", "GET /audio/devices",
                   "POST /audio/test/mic", "POST /audio/test/speaker",
                   "POST /settings/refresh", "rate_percent", "loaded_model",
                   "speak_voice_in_use", "mic_test", "swap_error"):
        assert needle in text, needle


def test_settings_js_has_the_manager_and_no_longer_makes_the_scripts_the_only_path():
    js = read("console", "static", "settings.js")
    assert "Speech models" in js
    assert "Fetch one with desktop/get-whisper.ps1 -Model" not in js
    assert "fetch one with desktop/get-piper.ps1" not in js


# --- AC-73, NFR-2: no new dependency -------------------------------------------

PINNED_CARGO = {
    "log": "0.4", "serde": "1", "serde_json": "1", "toml": "0.8", "tauri": "2",
    "tauri-plugin-single-instance": "2", "url": "2", "tiny_http": "0.12", "xcap": "0.9",
    "arboard": "3", "getrandom": "0.3", "cpal": "0.16", "earshot": "1", "rustpotter": "3",
    "half": "=2.3.1", "tauri-plugin-global-shortcut": "2",
}


def test_cargo_dependencies_are_exactly_the_pinned_list():
    manifest = tomllib.loads(read("desktop", "src-tauri", "Cargo.toml"))
    found = {name: (spec if isinstance(spec, str) else spec["version"])
             for name, spec in manifest["dependencies"].items()}
    assert found == PINNED_CARGO


def test_requirements_dev_is_unchanged():
    lines = [ln.strip() for ln in read("console", "requirements-dev.txt").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    assert lines == ["pytest>=8.0"]


# --- AC-72: nothing that worked before changes ----------------------------------

def _catalog():
    data = b"b" * 2000
    spec = AssetFile(name="ggml-base.en.bin", size=len(data),
                     sha256=hashlib.sha256(data).hexdigest(),
                     url="https://huggingface.co/a/b/resolve/%s/ggml-base.en.bin" % ("c" * 40),
                     hash_source="hf-lfs-oid")
    return Catalog(assets=(Asset("base.en", "stt", "base", "a/b", "c" * 40, "2 KiB", "mit",
                                 (spec,)),)), data


def test_a_model_placed_by_the_script_reads_installed_and_not_verified(tmp_path):
    catalog, data = _catalog()
    stt = tmp_path / "desktop" / "stt"
    stt.mkdir(parents=True)
    (stt / "ggml-base.en.bin").write_bytes(data)           # as get-whisper.ps1 would
    rows = {r["id"]: r for r in inventory(str(tmp_path), catalog,
                                           settings={"stt_model": "base.en"})["assets"]}
    assert (rows["base.en"]["state"], rows["base.en"]["verified"]) == ("installed", False)


def test_the_existing_evidence_for_ac_72_is_still_present_by_name():
    inv = read("console", "tests", "test_voice_assets_inventory.py")
    assert "def test_files_placed_by_a_script_read_installed_but_not_verified_until_verify_runs" in inv
    cmds = read("console", "tests", "test_assistant_commands.py")
    assert 'merged["input_device"] == "" and merged["output_device"] == ""' in cmds


def test_a_settings_file_without_the_device_keys_means_the_system_default(tmp_path):
    d = tmp_path / "console" / ".cache"
    d.mkdir(parents=True, exist_ok=True)
    merged = assistant_config.settings(str(tmp_path))
    assert merged["input_device"] == "" and merged["output_device"] == ""
