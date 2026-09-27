#!/usr/bin/env python3
"""Verify the official stable Brewnicle release, then atomically update its formula."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import tarfile
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

REPO = "lmilojevicc/brewnicle"
API = f"https://api.github.com/repos/{REPO}/releases"
WEB = f"https://github.com/{REPO}/releases"
TARGETS = ("darwin_amd64", "darwin_arm64", "linux_amd64", "linux_arm64")
SEMVER = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
LICENSE_NAME = re.compile(r"(?:LICEN[CS]E|COPYING)(?:[._-].*)?", re.IGNORECASE)
ARCHIVE_LIMIT = 128 * 1024 * 1024
HOSTS = {"api.github.com", "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}


def version(tag):
    match = re.fullmatch("v" + SEMVER, tag, re.ASCII)
    if not match:
        raise ValueError("release tag must be stable vMAJOR.MINOR.PATCH")
    return tuple(int(part) for part in match.groups())


def safe_url(url):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname not in HOSTS or parts.port not in (None, 443)
            or parts.username is not None or parts.password is not None):
        raise ValueError("unexpected download host or protocol")
    return url


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, limit):
    request = Request(safe_url(url), headers={"User-Agent": "homebrew-tap-brewnicle-updater",
                                             "Accept": "application/octet-stream" if "/download/" in url else "application/vnd.github+json"})
    with build_opener(SafeRedirect).open(request, timeout=30) as response:
        safe_url(response.url)
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("response exceeds size limit")
    return data


def latest_release(get):
    try:
        raw = get(API + "/latest", 1024 * 1024)
    except HTTPError as error:
        error.close()
        if error.code != 404:
            raise
        # A 404 alone could conceal an API/repository problem; confirm an empty list.
        releases = json.loads(get(API + "?per_page=1", 1024 * 1024))
        if releases != []:
            raise ValueError("latest release unavailable but releases list is not empty") from error
        return None
    release = json.loads(raw)
    if not isinstance(release, dict) or release.get("draft") is not False or release.get("prerelease") is not False:
        raise ValueError("expected a published stable release")
    tag = release.get("tag_name")
    if not isinstance(tag, str):
        raise ValueError("missing release tag")
    version(tag)
    if release.get("html_url") != f"{WEB}/tag/{tag}":
        raise ValueError("unexpected release URL")
    return release


def asset_urls(release):
    tag = release["tag_name"]
    names = {f"brewnicle_{tag}_{target}.tar.gz" for target in TARGETS} | {"SHA256SUMS"}
    assets = release.get("assets")
    if not isinstance(assets, list) or len(assets) != len(names):
        raise ValueError("release must have exactly four archives and SHA256SUMS")
    urls = {}
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("malformed asset")
        name = asset.get("name")
        if not isinstance(name, str) or name not in names or name in urls or asset.get("state") != "uploaded":
            raise ValueError("missing, duplicate, or unfinished asset")
        url = f"{WEB}/download/{tag}/{name}"
        if asset.get("browser_download_url") != url:
            raise ValueError("unexpected asset URL")
        size = asset.get("size")
        limit = 8192 if name == "SHA256SUMS" else ARCHIVE_LIMIT
        if type(size) is not int or not 0 < size <= limit:
            raise ValueError("invalid asset size")
        urls[name] = (url, size)
    return urls


def checksums(raw, names):
    sums = {}
    for line in raw.decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line, re.ASCII)
        if not match or match[2] not in names or match[2] in sums:
            raise ValueError("invalid, duplicate, or unexpected checksum entry")
        sums[match[2]] = match[1]
    if set(sums) != names:
        raise ValueError("missing archive checksum")
    return sums


def verify_archive(data, target):
    names = set()
    modules = None
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r|gz") as archive:
        for member in archive:
            name = member.name
            if (not member.isfile() or name in names or "\\" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    or (name not in ("brewnicle", "LICENSE") and not name.startswith("licenses/"))):
                raise ValueError("unsafe or duplicate archive member")
            names.add(name)
            total += member.size
            if total > 256 * 1024 * 1024 or len(names) > 10000:
                raise ValueError("archive expands beyond limits")
            if member.size == 0 and name != "licenses/MODULES.txt" and not name.endswith("SOURCE_NOTICES.txt"):
                raise ValueError("empty archive file")
            if name == "brewnicle":
                if not member.mode & 0o111:
                    raise ValueError("binary is not executable")
                header = archive.extractfile(member).read(32)
                if target.startswith("linux_"):
                    machine = 62 if target.endswith("amd64") else 183
                    valid = len(header) >= 20 and header[:6] == b"\x7fELF\x02\x01"
                    valid = valid and struct.unpack_from("<H", header, 18)[0] == machine
                else:
                    cpu = 0x01000007 if target.endswith("amd64") else 0x0100000C
                    valid = len(header) >= 8 and header[:4] == b"\xcf\xfa\xed\xfe"
                    valid = valid and struct.unpack_from("<I", header, 4)[0] == cpu
                if not valid:
                    raise ValueError("wrong binary architecture")
            elif name == "licenses/MODULES.txt":
                if member.size > 65536:
                    raise ValueError("oversized module list")
                modules = archive.extractfile(member).read().decode().splitlines()
    required = {"brewnicle", "LICENSE", "licenses/MODULES.txt", "licenses/go/LICENSE",
                "licenses/supplemental/Unicode-3.0.txt", "licenses/supplemental/Unicode-DFS-2016.txt",
                "licenses/supplemental/Unicode-15.0.0-NOTICE.txt", "licenses/supplemental/Unicode-17.0.0-NOTICE.txt",
                "licenses/supplemental/HSLuv-LICENSE.txt"}
    if not required <= names or not modules:
        raise ValueError("missing binary or license notices")
    license_files = [name for name in names if LICENSE_NAME.fullmatch(name.rsplit("/", 1)[-1])]
    if any(not any(name.startswith(f"licenses/{module}/") for name in license_files) for module in modules):
        raise ValueError("missing dependency license")


def render_formula(tag=None, sums=None):
    stable = ""
    if tag is not None:
        version(tag)
        stable = f'  version "{tag[1:]}"\n'
        for os_name, goos in (("macos", "darwin"), ("linux", "linux")):
            stable += f"\n  on_{os_name} do\n"
            for rubyarch, goarch in (("arm", "arm64"), ("intel", "amd64")):
                name = f"brewnicle_{tag}_{goos}_{goarch}.tar.gz"
                digest = sums[name]
                if not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise ValueError("invalid formula checksum")
                stable += (f"    on_{rubyarch} do\n"
                           f'      url "{WEB}/download/{tag}/{name}"\n'
                           f'      sha256 "{digest}"\n'
                           "    end\n")
            stable += "  end\n"
        stable += "\n"
    return '''class Brewnicle < Formula
  desc "Terminal browser for recently added Homebrew packages"
  homepage "https://github.com/lmilojevicc/brewnicle"
  license "MIT"
''' + stable + '''
  head do
    url "https://github.com/lmilojevicc/brewnicle.git", branch: "main"
    depends_on "go" => :build
  end

  uses_from_macos "git"

  def install
    if build.head?
      ENV["GOWORK"] = "off"
      ENV["GOTOOLCHAIN"] = "local"
      ENV["CGO_ENABLED"] = "0"
      system "go", "mod", "download"
      system "go", "build", *std_go_args, "-mod=readonly", "-buildvcs=false", "./cmd/brewnicle"
      system "go", "run", "-mod=readonly", "./scripts/notices", "dependency-licenses"
      pkgshare.install "dependency-licenses" => "licenses"
    else
      bin.install "brewnicle"
      pkgshare.install "licenses"
    end
    pkgshare.install "LICENSE"
  end

  test do
    # Launching the TUI would start network indexing; no version flag exists.
    assert_predicate bin/"brewnicle", :executable?
    assert_path_exists pkgshare/"LICENSE"
    assert_path_exists pkgshare/"licenses/go/LICENSE"
    assert_path_exists pkgshare/"licenses/MODULES.txt"
  end
end
'''


def update(formula, get=fetch, dry_run=False):
    release = latest_release(get)
    if release is None:
        print("No published releases; formula unchanged")
        return False
    urls = asset_urls(release)
    tag = release["tag_name"]
    current = formula.read_text()
    versions = re.findall(r'^  version "([^"]+)"$', current, re.MULTILINE)
    if len(versions) > 1 or (not versions and current != render_formula()):
        raise ValueError("unrecognized formula version")
    if versions and version(tag) < version("v" + versions[0]):
        print("Ignoring older release; formula unchanged")
        return False

    def download(name, limit):
        url, size = urls[name]
        data = get(url, limit)
        if len(data) != size:
            raise ValueError("asset size differs from metadata")
        return data

    names = set(urls) - {"SHA256SUMS"}
    sums = checksums(download("SHA256SUMS", 8192), names)
    for target in TARGETS:
        name = f"brewnicle_{tag}_{target}.tar.gz"
        data = download(name, ARCHIVE_LIMIT)
        if hashlib.sha256(data).hexdigest() != sums[name]:
            raise ValueError(f"checksum mismatch: {name}")
        verify_archive(data, target)
    generated = render_formula(tag, sums)
    if current == generated:
        print("Formula is current")
        return False
    if versions and version(tag) == version("v" + versions[0]):
        raise ValueError("existing version differs; refusing mutable release or formula drift")
    if dry_run:
        print(f"Validated {tag}; would update {formula}")
        return True
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=formula.parent, prefix=".brewnicle-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(generated)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, formula)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Updated formula to {tag}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate all downloads without writing")
    args = parser.parse_args()
    update(Path(__file__).resolve().parents[1] / "Formula/brewnicle.rb", dry_run=args.dry_run)
