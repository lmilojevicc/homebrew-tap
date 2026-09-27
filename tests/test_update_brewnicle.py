import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import tarfile
import tempfile
import unittest
from urllib.error import HTTPError

SPEC = importlib.util.spec_from_file_location("updater", Path(__file__).resolve().parents[1] / "scripts/update_brewnicle.py")
u = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(u)


def http_error(url, code):
    error = HTTPError(url, code, "fixture response", {}, io.BytesIO())
    error.close()
    return error


def archive(target, extra=None, omit=None):
    header = bytearray(32)
    if target.startswith("linux_"):
        header[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", header, 18, 62 if target.endswith("amd64") else 183)
    else:
        header[:4] = b"\xcf\xfa\xed\xfe"
        struct.pack_into("<I", header, 4, 0x01000007 if target.endswith("amd64") else 0x0100000C)
    files = {"brewnicle": bytes(header), "LICENSE": b"MIT", "licenses/go/LICENSE": b"Go BSD",
             "licenses/MODULES.txt": b"example.org/mod@v1.0.0\n", "licenses/example.org/mod@v1.0.0/LICENSE": b"BSD",
             "licenses/supplemental/Unicode-3.0.txt": b"Unicode", "licenses/supplemental/Unicode-DFS-2016.txt": b"Unicode",
             "licenses/supplemental/Unicode-15.0.0-NOTICE.txt": b"Unicode",
             "licenses/supplemental/Unicode-17.0.0-NOTICE.txt": b"Unicode",
             "licenses/supplemental/HSLuv-LICENSE.txt": b"MIT"}
    if omit:
        files.pop(omit)
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:gz") as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = 0o755 if name == "brewnicle" else 0o644
            tar.addfile(info, io.BytesIO(content))
        if extra:
            tar.addfile(extra, io.BytesIO(b"x" * extra.size))
    return data.getvalue()


class ReleaseFixture:
    def __init__(self, tag="v1.2.3"):
        self.tag = tag
        self.data = {f"brewnicle_{tag}_{target}.tar.gz": archive(target) for target in u.TARGETS}
        self.release = {"tag_name": tag, "draft": False, "prerelease": False, "html_url": f"{u.WEB}/tag/{tag}"}
        self.requests = []
        self.refresh()

    def refresh(self):
        self.data["SHA256SUMS"] = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n"
                                            for name, data in sorted(self.data.items()) if name != "SHA256SUMS").encode()
        self.release["assets"] = [{"name": name, "state": "uploaded", "size": len(data),
                                   "browser_download_url": f"{u.WEB}/download/{self.tag}/{name}"}
                                  for name, data in self.data.items()]

    def get(self, url, limit):
        self.requests.append(url)
        if url == u.API + "/latest":
            return json.dumps(self.release).encode()
        name = url.rsplit("/", 1)[-1]
        assert url == f"{u.WEB}/download/{self.tag}/{name}"
        data = self.data[name]
        assert len(data) <= limit
        return data


class UpdateBrewnicleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.formula = Path(self.tmp.name) / "brewnicle.rb"
        self.head = u.render_formula()
        self.formula.write_text(self.head)
        self.fixture = ReleaseFixture()

    def reject(self, fixture=None):
        before = self.formula.read_bytes()
        with self.assertRaises((ValueError, KeyError, TypeError, UnicodeError, tarfile.TarError)):
            u.update(self.formula, (fixture or self.fixture).get)
        self.assertEqual(before, self.formula.read_bytes())
        self.assertEqual([self.formula], list(self.formula.parent.iterdir()))

    def test_dependency_license_basename(self):
        for name in ("LICENSE", "COPYING", "LICENCE.txt"):
            self.assertIsNotNone(u.LICENSE_NAME.fullmatch(name))
        for name in ("SOURCE_NOTICES.txt", "LICENSED", "fooLICENSE", "PATENTS"):
            self.assertIsNone(u.LICENSE_NAME.fullmatch(name))

    def test_valid_all_targets_idempotent_and_ruby_syntax(self):
        self.assertTrue(u.update(self.formula, self.fixture.get))
        generated = self.formula.read_text()
        self.assertIn('version "1.2.3"', generated)
        self.assertIn('branch: "main"', generated)
        self.assertEqual(4, generated.count('sha256 "'))
        self.assertEqual(6, len(self.fixture.requests))
        self.assertFalse(u.update(self.formula, self.fixture.get))
        subprocess.run(["ruby", "-c", str(self.formula)], check=True, capture_output=True)
        self.assertEqual(generated, self.formula.read_text())

    def test_checked_in_head_formula_matches_template(self):
        root = Path(__file__).resolve().parents[1]
        current = (root / "Formula/brewnicle.rb").read_text()
        # Stable formulas are generated after the first real release.
        if '  version "' not in current:
            self.assertEqual(self.head, current)
        self.assertNotIn("--version", self.head)

    def test_dry_run_validates_without_writing(self):
        self.assertTrue(u.update(self.formula, self.fixture.get, dry_run=True))
        self.assertEqual(self.head, self.formula.read_text())
        self.assertEqual(6, len(self.fixture.requests))

    def test_no_release_requires_confirmed_empty_list(self):
        def get(url, limit):
            if url == u.API + "/latest":
                raise http_error(url, 404)
            self.assertEqual(u.API + "?per_page=1", url)
            return b"[]"
        self.assertFalse(u.update(self.formula, get))
        self.assertEqual(self.head, self.formula.read_text())

    def test_api_errors_fail_not_noop(self):
        for code in (401, 403, 429, 500):
            with self.subTest(code=code):
                def get(url, limit):
                    raise http_error(url, code)
                with self.assertRaises(HTTPError):
                    u.update(self.formula, get)
        for body in (b"{}", b"null", b"not json", b'[{"prerelease": true}]'):
            def get(url, limit):
                if url.endswith("/latest"):
                    raise http_error(url, 404)
                return body
            with self.subTest(body=body), self.assertRaises(ValueError):
                u.update(self.formula, get)

    def test_malformed_metadata(self):
        for key, value in (("draft", True), ("prerelease", True), ("draft", None), ("assets", None),
                           ("tag_name", None), ("html_url", "https://attacker.invalid/release")):
            f = ReleaseFixture()
            f.release[key] = value
            with self.subTest(key=key, value=value):
                self.reject(f)

    def test_bad_tags_cannot_interpolate_ruby(self):
        for tag in ("1.2.3", "v01.2.3", "v1.2.3-rc.1", "v1.2.3+build", "v1.2.3\n", 'v1.2.3#{system("id")}', "v١.2.3"):
            f = ReleaseFixture()
            f.release["tag_name"] = tag
            self.reject(f)

    def test_missing_duplicate_extra_assets(self):
        for mode in ("missing", "duplicate", "extra"):
            f = ReleaseFixture()
            if mode == "missing":
                f.release["assets"].pop()
            elif mode == "duplicate":
                f.release["assets"][0] = copy.deepcopy(f.release["assets"][1])
            else:
                f.release["assets"].append(copy.deepcopy(f.release["assets"][0]))
            self.reject(f)

    def test_bad_asset_url_state_size(self):
        for key, value in (("browser_download_url", "https://example.org/asset"), ("state", "new"),
                           ("size", True), ("size", 0), ("size", u.ARCHIVE_LIMIT + 1)):
            f = ReleaseFixture()
            f.release["assets"][0][key] = value
            self.reject(f)

    def test_checksums_missing_duplicate_malformed(self):
        for kind in ("missing", "duplicate", "malformed", "unexpected"):
            f = ReleaseFixture()
            lines = f.data["SHA256SUMS"].splitlines(keepends=True)
            if kind == "missing":
                lines.pop()
            elif kind == "duplicate":
                lines.append(lines[0])
            elif kind == "malformed":
                lines[0] = b"invalid\n"
            else:
                lines.append(b"0" * 64 + b"  unknown.tar.gz\n")
            f.data["SHA256SUMS"] = b"".join(lines)
            for asset in f.release["assets"]:
                if asset["name"] == "SHA256SUMS":
                    asset["size"] = len(f.data["SHA256SUMS"])
            self.reject(f)

    def test_checksum_mismatch_even_with_valid_metadata(self):
        name = next(iter(self.fixture.data))
        data = bytearray(self.fixture.data[name])
        data[-1] ^= 1
        self.fixture.data[name] = bytes(data)
        self.reject()

    def test_metadata_size_mismatch(self):
        self.fixture.release["assets"][0]["size"] += 1
        self.reject()

    def test_fourth_archive_failure_never_writes_formula(self):
        name = f"brewnicle_{self.fixture.tag}_{u.TARGETS[-1]}.tar.gz"
        self.fixture.data[name] = archive("linux_amd64")
        self.fixture.refresh()
        self.reject()
        self.assertEqual(6, len(self.fixture.requests))

    def test_archive_paths_links_duplicates_and_missing_notices(self):
        for path in ("../escape", "/absolute", "licenses/../../escape", "licenses//file", "brewnicle", "other"):
            info = tarfile.TarInfo(path)
            info.size = 1
            with self.subTest(path=path), self.assertRaises(ValueError):
                u.verify_archive(archive("darwin_arm64", extra=info), "darwin_arm64")
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.DIRTYPE):
            info = tarfile.TarInfo("licenses/link")
            info.type = kind
            info.linkname = "../../escape"
            with self.assertRaises(ValueError):
                u.verify_archive(archive("darwin_arm64", extra=info), "darwin_arm64")
        for missing in ("LICENSE", "licenses/go/LICENSE", "licenses/example.org/mod@v1.0.0/LICENSE"):
            with self.assertRaises(ValueError):
                u.verify_archive(archive("darwin_arm64", omit=missing), "darwin_arm64")

    def test_archive_expansion_limit(self):
        info = tarfile.TarInfo("licenses/bomb")
        info.size = 257 * 1024 * 1024
        data = gzip.compress(info.tobuf() + bytes(1024))
        with self.assertRaisesRegex(ValueError, "expands"):
            u.verify_archive(data, "linux_arm64")

    def test_monotonic_upgrade_and_older_release_noop(self):
        u.update(self.formula, self.fixture.get)
        newer = ReleaseFixture("v1.10.0")
        self.assertTrue(u.update(self.formula, newer.get))
        current = self.formula.read_text()
        self.assertFalse(u.update(self.formula, self.fixture.get))
        self.assertEqual(current, self.formula.read_text())

    def test_same_version_mutation_rejected(self):
        u.update(self.formula, self.fixture.get)
        name = next(iter(self.fixture.data))
        extra = tarfile.TarInfo("licenses/extra-LICENSE")
        extra.size = 1
        self.fixture.data[name] = archive("darwin_amd64", extra=extra)
        self.fixture.refresh()
        self.reject()

    def test_unrecognized_head_formula_not_overwritten(self):
        self.formula.write_text(self.head + "# local modification\n")
        self.reject()

    def test_only_trusted_https_redirect_hosts(self):
        for url in ("http://github.com/a", "https://evil.invalid/a", "https://github.com.evil.invalid/a",
                    "https://user@github.com/a", "https://github.com:444/a", "file:///tmp/asset"):
            with self.assertRaises(ValueError):
                u.safe_url(url)
        self.assertEqual("https://release-assets.githubusercontent.com/a", u.safe_url("https://release-assets.githubusercontent.com/a"))


if __name__ == "__main__":
    unittest.main()
