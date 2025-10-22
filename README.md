# Asset Protocol Generator

Ein Python-Tool mit moderner GUI (PySide6) zum Erstellen von Übergabe- und Rückgabeprotokollen für Firmeneigentum – inklusive Live-Vorschau und PDF-Export.

## Features
- Übergabe- und Rückgabeprotokolle
- Dynamische Formularfelder (Mitarbeiter, Abteilung, Geräteliste, Zustand, Unterschriftenfelder)
- Live-Vorschau (HTML) im Fenster
- Export als PDF

## Voraussetzungen
- Python 3.10+
- Windows empfohlen (getestet), sollte plattformübergreifend laufen

## Installation

```powershell
python -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt
```

## Start

```powershell
.\.venv\Scripts\Activate.ps1 ; python -m src.asset_protocol_generator.main
```

## Externe Freigabe (Creator-Gate)

Der Ersteller kann die Nutzung extern steuern. Beim Start wird eine JSON-Quelle geprüft:

- URL/Datei via `APG_GATE_URL` (http/https/file oder lokaler Pfad)
- Erwartetes Format: `{ "enabled": true|false }`
- Bei Fehlern (Timeout/Netz/JSON) gilt die Nutzung als nicht erlaubt – der Nutzer sieht lediglich `error`.

Beispiele:

```powershell
# Nutzung erlauben (Dev-Override, nur lokal)
$env:APG_ALLOW = '1'

# Externe Quelle angeben (HTTP)
$env:APG_GATE_URL = 'https://example.com/asset-protocol-gate.json'

# Lokale Datei (Windows-Pfad):
$env:APG_GATE_URL = 'file:///C:/pfad/zur/asset-protocol-gate.json'
# oder ohne Schema
$env:APG_GATE_URL = 'C:\\pfad\\zur\\asset-protocol-gate.json'
```

## Packaging-Hinweis
Für reinen PDF-Export ohne QtWebEngine kann später ein CLI-Modus ergänzt werden.

## Steuerdatei auf GitHub hosten

Es gibt zwei einfache Varianten, die JSON-Steuerdatei online zu hosten:

1) GitHub Gist (einfachste Variante)
- Öffne https://gist.github.com und lege ein neues Gist an
- Dateiname: `asset-protocol-gate.json`
- Inhalt: `{ "enabled": true }` oder `{ "enabled": false }`
- Erstellen (Secret Gist reicht)
- Auf "Raw" klicken und die URL kopieren (beginnt mit `https://gist.githubusercontent.com/.../raw/.../asset-protocol-gate.json`)
- Diese URL in `APG_GATE_URL` setzen

2) Datei im GitHub-Repo
- Lege im Repo (z. B. `main`-Branch) die Datei `asset-protocol-gate.json` an
- Öffne die Datei → "Raw" anklicken → URL kopieren, z. B.:
	`https://raw.githubusercontent.com/<owner>/<repo>/main/asset-protocol-gate.json`
- Diese URL in `APG_GATE_URL` setzen

Start mit gesetzter URL (PowerShell):

```powershell
$env:APG_GATE_URL = 'https://raw.githubusercontent.com/<owner>/<repo>/main/asset-protocol-gate.json'
.\.venv\Scripts\Activate.ps1 ; python -m src.asset_protocol_generator.main
```

Umschalten:
- Einschalten: Dateiinhalt auf `{ "enabled": true }` setzen → App startet
- Ausschalten: auf `{ "enabled": false }` setzen oder die Datei/URL unzugänglich machen → Nutzer sieht "error"
