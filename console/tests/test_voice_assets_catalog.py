"""The voice-asset catalog (T-031-06; AC-1, AC-2, AC-3, AC-26).

The committed `console/config/voice-assets.toml` is the only place a download
URL or a SHA256 enters the repo, so these tests are the reviewer's net: shape,
counts, naming contract, hint-versus-size agreement, a cross-check of every
hash against the decision log it was copied from, and (when the files exist on
this machine) a check against real bytes. The one test that touches the
internet is opt-in (`CC_ONLINE_TESTS=1`) and is not part of CI.
"""

import hashlib
import os
import re
import urllib.error
import urllib.request

import pytest

from server import tomlio, voice_assets
from server.voice_assets import CatalogError, catalog_from_dict, load_catalog

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DECISION_LOG = os.path.join(REPO, "knowledge-center", "artifacts", "T-031",
                            "T-031-decision-log.md")
URL = re.compile(r"^https://huggingface\.co/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/resolve/"
                 r"([0-9a-f]{40})/[A-Za-z0-9._/-]+$")


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def all_files(catalog):
    return [(a, f) for a in catalog.assets for f in a.files]


def test_counts_are_exactly_what_the_scripts_offered(catalog):
    assert [a.id for a in catalog.of_kind("stt")] == [
        "tiny.en", "base.en", "small.en", "medium.en"]
    assert [a.id for a in catalog.of_kind("voice")] == [
        "en_US-amy-medium", "en_US-ryan-medium", "en_US-lessac-medium",
        "en_GB-alba-medium", "en_GB-northern_english_male-medium"]
    files = all_files(catalog)
    assert len(files) == 14
    assert sum(f.hash_source == "hf-lfs-oid" for _, f in files) == 9
    assert sum(f.hash_source == "computed-pinned" for _, f in files) == 5


def test_every_file_pins_an_https_huggingface_commit(catalog):
    for asset, f in all_files(catalog):
        m = URL.match(f.url)
        assert m, "%s: %s is not an https huggingface.co commit-pinned URL" % (asset.id, f.url)
        assert m.group(1) == asset.commit, "%s: URL commit differs from the entry's" % asset.id
        assert f.url.endswith("/" + f.name) or f.url.split("/")[-1] == f.name
        assert not f.url.startswith("http://")


def test_every_file_has_size_hash_provenance_and_a_safe_name(catalog):
    for asset, f in all_files(catalog):
        assert f.size > 0
        assert re.fullmatch(r"[0-9a-f]{64}", f.sha256), (asset.id, f.name)
        assert f.hash_source in ("hf-lfs-oid", "computed-pinned")
        assert voice_assets.SAFE_NAME.match(f.name)
        if f.hash_source == "computed-pinned":
            assert re.fullmatch(r"[0-9a-f]{40}", f.git_blob_sha1), (asset.id, f.name)
        else:
            assert f.git_blob_sha1 == ""
    shas = [f.sha256 for _, f in all_files(catalog)]
    assert len(set(shas)) == len(shas), "two files share a hash: a copy-paste slip"


def test_filename_contract_with_the_shell(catalog):
    for asset in catalog.of_kind("stt"):
        assert [f.name for f in asset.files] == ["ggml-%s.bin" % asset.id]
        assert asset.main_file.name == "ggml-%s.bin" % asset.id
        assert asset.dir_rel == os.path.join("desktop", "stt")
    for asset in catalog.of_kind("voice"):
        assert [f.name for f in asset.files] == [
            asset.id + ".onnx.json", asset.id + ".onnx"], "json first, onnx last"
        assert asset.main_file.name == asset.id + ".onnx"
        assert asset.dir_rel == os.path.join("desktop", "tts")


def test_public_row_carries_size_hint_and_license_but_no_url(catalog):
    for asset in catalog.assets:
        row = asset.public()
        assert row["size_bytes"] == sum(f.size for f in asset.files) > 0
        assert row["hint"] and row["license"]
        assert "url" not in row and "files" not in row and "path" not in row
    amy = catalog.get("en_US-amy-medium").public()
    assert amy["size_bytes"] == 63201294 + 4882, "a voice is both of its files"


def test_hints_state_the_catalog_size_not_another(catalog):
    pattern = re.compile(r"([\d.]+) (MiB|GiB) / ([\d.]+) (MB|GB)")
    for asset in catalog.assets:
        m = pattern.search(asset.hint)
        assert m, "%s: the hint states no size to check" % asset.id
        for number, unit in ((m.group(1), m.group(2)), (m.group(3), m.group(4))):
            div ={"MiB": 2 ** 20, "GiB": 2 ** 30, "MB": 10 ** 6, "GB": 10 ** 9}[unit]
            decimals = len(number.split(".")[1]) if "." in number else 0
            assert round(asset.size_bytes / div, decimals) == float(number), (
                "%s: hint says %s %s but size_bytes is %d" % (
                    asset.id, number, unit, asset.size_bytes))
    # The four sizes decision D-13 fixed, so a wrong rounding rule cannot pass.
    tiny, base, small, medium = (catalog.get(i).hint for i in
                                 ("tiny.en", "base.en", "small.en", "medium.en"))
    assert tiny.startswith("74 MiB / 78 MB")
    assert base.startswith("141 MiB / 148 MB")
    assert small.startswith("465 MiB / 488 MB")
    assert medium.startswith("1.43 GiB / 1.53 GB")


def test_ryan_is_labelled_non_commercial_and_every_licence_is_present(catalog):
    assert "NC" in catalog.get("en_US-ryan-medium").license
    assert "non-commercial" in catalog.get("en_US-ryan-medium").license.lower()
    for asset in catalog.assets:
        assert asset.license.strip(), asset.id


def test_committed_file_loads_through_the_consoles_own_tomlio(catalog):
    data = tomlio.load(voice_assets.default_catalog_path())
    assert set(data) == {"stt", "voice"}
    assert all(isinstance(row["file"], list) for row in data["stt"] + data["voice"])
    assert catalog_from_dict(data) == catalog


def test_every_catalog_hash_and_size_appears_in_the_decision_log(catalog):
    """An independent check on copying: the values came from decision D-2, so
    each one must be found there. A typo in either place fails here."""
    if not os.path.isfile(DECISION_LOG):
        pytest.skip("decision log not found at %s; cannot cross-check D-2" % DECISION_LOG)
    with open(DECISION_LOG, "r", encoding="utf-8") as fh:
        text = fh.read()
    d2 = text.split("## D-2", 1)[1].split("## D-3", 1)[0]
    for asset, f in all_files(catalog):
        assert f.sha256 in d2, "%s sha256 not in D-2" % f.name
        assert asset.commit in d2, "%s commit not in D-2" % asset.id
        if f.hash_source == "computed-pinned":
            assert f.git_blob_sha1 in d2, "%s git oid not in D-2" % f.name
        if f.size >= 10000:
            assert "{:,}".format(f.size) in d2 or str(f.size) in d2, f.name


def test_hashes_equal_the_real_local_files_when_present(catalog):
    wanted = [("base.en", "ggml-base.en.bin", os.path.join("desktop", "stt")),
              ("en_US-amy-medium", "en_US-amy-medium.onnx", os.path.join("desktop", "tts")),
              ("en_US-amy-medium", "en_US-amy-medium.onnx.json", os.path.join("desktop", "tts"))]
    missing = []
    checked = 0
    for asset_id, name, directory in wanted:
        path = os.path.join(REPO, directory, name)
        if not os.path.isfile(path):
            missing.append(path)
            continue
        spec = next(f for f in catalog.get(asset_id).files if f.name == name)
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                digest.update(block)
        assert os.path.getsize(path) == spec.size, name
        assert digest.hexdigest() == spec.sha256, name
        checked += 1
    if not checked:
        pytest.skip("SKIPPED LOUDLY: no legacy local files to hash; absent: %s" % missing)
    if missing:
        print("note: not present, not checked: %s" % missing)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


@pytest.mark.skipif(os.environ.get("CC_ONLINE_TESTS") != "1",
                    reason="opt-in: set CC_ONLINE_TESTS=1 (uses the internet; not CI)")
def test_online_catalog_matches_hugging_face(catalog):
    """AC-26. The nine LFS hashes against the `x-linked-etag` of the resolve
    endpoint's first answer (the redirect to the CDN loses the header), and
    the five small `.onnx.json` files by downloading and hashing them."""
    opener = urllib.request.build_opener(_NoRedirect)
    for _asset, f in all_files(catalog):
        if f.hash_source == "hf-lfs-oid":
            request = urllib.request.Request(f.url, method="HEAD")
            try:
                response = opener.open(request, timeout=30)
            except urllib.error.HTTPError as redirect:
                response = redirect
            etag = (response.headers.get("x-linked-etag") or "").strip('"')
            assert etag == f.sha256, "%s: upstream etag %s" % (f.name, etag)
        else:
            with urllib.request.urlopen(f.url, timeout=60) as response:
                body = response.read()
            assert len(body) == f.size, f.name
            assert hashlib.sha256(body).hexdigest() == f.sha256, f.name


# --- the loader refuses a malformed catalog instead of trusting it -----------

def _fixture(**file_overrides):
    row = {"name": "ggml-x.bin", "url": "https://huggingface.co/a/b/resolve/" + "a" * 40 + "/ggml-x.bin",
           "size": 10, "sha256": "b" * 64, "hash_source": "hf-lfs-oid"}
    row.update(file_overrides)
    return {"stt": [{"id": "x", "label": "x", "repo": "a/b", "commit": "a" * 40,
                     "hint": "1 MiB / 1 MB", "license": "mit", "file": [row]}]}


def test_the_loader_accepts_a_well_formed_fixture():
    assert catalog_from_dict(_fixture()).get("x").size_bytes == 10


@pytest.mark.parametrize("override", [
    {"name": "../ggml-x.bin"}, {"name": "a/b.bin"}, {"name": "a b.bin"},
    {"sha256": "B" * 64}, {"sha256": "b" * 63}, {"sha256": ""},
    {"hash_source": "trust-me"}, {"hash_source": "computed-pinned"},
    {"size": 0}, {"size": -5}, {"url": ""},
])
def test_the_loader_rejects_unsafe_or_unhashed_entries(override):
    with pytest.raises(CatalogError):
        catalog_from_dict(_fixture(**override))


def test_the_loader_rejects_duplicate_ids_and_files_without_hashes():
    data = _fixture()
    data["stt"].append(dict(data["stt"][0]))
    with pytest.raises(CatalogError):
        catalog_from_dict(data)
    data = _fixture()
    del data["stt"][0]["file"][0]["sha256"]
    with pytest.raises(CatalogError):
        catalog_from_dict(data)
