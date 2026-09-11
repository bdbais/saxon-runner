"""
Aggiornamento automatico da GitHub Releases.

Ogni release pubblica tre file con nomi fissi, cosi' anche il link
".../releases/latest/download/<nome>" resta sempre valido:

    SaxonRunner-Setup.exe      installer Inno Setup (installa e aggiorna)
    SaxonRunner-portable.exe   eseguibile singolo, senza installazione
    SHA256SUMS.txt             checksum nel formato di sha256sum

L'installer scaricato viene verificato contro SHA256SUMS.txt prima di
essere avviato. Solo libreria standard.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass

REPO = "bdbais/saxon-runner"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
SETUP_ASSET = "SaxonRunner-Setup.exe"
PORTABLE_ASSET = "SaxonRunner-portable.exe"
SUMS_ASSET = "SHA256SUMS.txt"


class UpdateError(Exception):
    pass


@dataclass
class Release:
    version: str
    tag: str
    notes: str
    page_url: str
    setup_url: str | None
    sums_url: str | None


def parse_version(text: str) -> tuple:
    """'v3.1.0' -> (3, 1, 0). Le parti mancanti valgono 0, il resto e' ignorato."""
    m = re.match(r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", text or "")
    if not m:
        return (0, 0, 0)
    return tuple(int(g or 0) for g in m.groups())


def is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


def _request(url: str, user_agent: str, accept: str = "*/*") -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": accept})


def fetch_latest(current_version: str, timeout: float = 10) -> Release | None:
    """Ultima release pubblicata (bozze e pre-release escluse da GitHub stesso)."""
    req = _request(API_LATEST, f"SaxonRunner/{current_version}", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    tag = data.get("tag_name") or ""
    if not tag or data.get("draft") or data.get("prerelease"):
        return None
    assets = {a.get("name"): a.get("browser_download_url") for a in data.get("assets", [])}
    return Release(
        version=tag.lstrip("vV"),
        tag=tag,
        notes=(data.get("body") or "").strip(),
        page_url=data.get("html_url") or RELEASES_PAGE,
        setup_url=assets.get(SETUP_ASSET),
        sums_url=assets.get(SUMS_ASSET),
    )


def parse_sums(text: str) -> dict:
    """Legge righe 'hash  nome' (anche 'hash *nome', formato binario di sha256sum)."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*([0-9a-fA-F]{64})\s+\*?(.+?)\s*$", line)
        if m:
            out[m.group(2)] = m.group(1).lower()
    return out


def install_kind() -> str:
    """'installed' se avviato dall'installazione, 'portable' se exe singolo, 'source' da Python."""
    if not getattr(sys, "frozen", False):
        return "source"
    exe_dir = os.path.dirname(sys.executable)
    try:
        names = os.listdir(exe_dir)
    except OSError:
        return "portable"
    if any(n.lower().startswith("unins") and n.lower().endswith(".exe") for n in names):
        return "installed"
    return "portable"


def download_installer(release: Release, current_version: str, progress=None,
                       timeout: float = 30) -> str:
    """Scarica l'installer in %TEMP%, verifica lo SHA-256 e restituisce il percorso.

    progress(scaricati, totale) viene chiamato dal thread che scarica;
    totale e' 0 se il server non dichiara la dimensione.
    """
    if not release.setup_url or not release.sums_url:
        raise UpdateError("La release non contiene l'installer o il file dei checksum.")
    ua = f"SaxonRunner/{current_version}"

    with urllib.request.urlopen(_request(release.sums_url, ua), timeout=timeout) as r:
        expected = parse_sums(r.read().decode("utf-8", errors="replace")).get(SETUP_ASSET)
    if not expected:
        raise UpdateError(f"{SUMS_ASSET} non riporta il checksum di {SETUP_ASSET}.")

    dest = os.path.join(tempfile.gettempdir(), f"SaxonRunner-Setup-{release.version}.exe")
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(_request(release.setup_url, ua), timeout=timeout) as r, \
                open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    except Exception:
        _remove_quietly(dest)
        raise

    if digest.hexdigest() != expected:
        _remove_quietly(dest)
        raise UpdateError("Il file scaricato non corrisponde al checksum pubblicato: "
                          "aggiornamento annullato.")
    return dest


def launch_installer(path: str) -> None:
    """Avvia l'installer in modalita' silenziosa; al termine riapre Saxon Runner.

    /RELAUNCH=1 e' letto dallo script Inno Setup ({param:RELAUNCH}).
    """
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS", "/RELAUNCH=1"],
        close_fds=True, creationflags=flags)


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
