from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


# Externe Steuerung per URL oder Dateipfad; per Env überschreibbar
# Beispiel-URL (anpassen): https://example.com/asset-protocol-gate.json
GATE_URL = os.environ.get(
    "APG_GATE_URL",
    "https://raw.githubusercontent.com/nichtkarim/Protokolle360V/main/asset-protocol-gate.json",
)

#
def _read_local_file(path: str) -> str | None:
    try:
        p = Path(path)
        if not p.exists():
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def _fetch_http(url: str, timeout: float) -> str | None:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "asset-protocol-gui/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if getattr(resp, "status", 200) != 200:
                return None
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def is_usage_allowed(timeout: float = 2.0) -> bool:
    """
    Externer Gate-Check:
    - APG_ALLOW=1 -> erlaubt (Dev-Override)
    - APG_GATE_URL zeigt auf HTTP(S) oder eine lokale Datei
      Erwartetes JSON: {"enabled": true|false}
    - Bei Fehlern (Netzwerk/Timeout/HTTP/JSON/Datei) -> nicht erlaubt
    """
    if os.environ.get("APG_ALLOW") == "1":
        return True

    url = GATE_URL.strip()
    content: str | None = None

    # Unterstütze Datei- und HTTP/HTTPS-Schemata
    try:
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            content = _fetch_http(url, timeout=timeout)
        elif parsed.scheme == "file":
            content = _read_local_file(parsed.path)
        else:
            # Falls ein nackter Pfad ohne Schema übergeben wird
            if url and Path(url).exists():
                content = _read_local_file(url)
            else:
                # Ungültige Quelle -> nicht erlaubt
                return False
    except Exception:
        return False

    if not content:
        return False

    try:
        data = json.loads(content)
        return bool(data.get("enabled", False))
    except Exception:
        return False
