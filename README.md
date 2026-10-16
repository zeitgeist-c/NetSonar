# NetSonar — AI-assisted network visibility for Windows

> Türkçe için: [README.tr.md](./README.tr.md)

Local network traffic analysis and SOC helper: per-minute bidirectional flow summaries via Npcap, Gemini risk analysis with VirusTotal + web context, and audited Windows Firewall blocking. Raw detail is discarded by design — no content, URL, or password logging.

![NetSonar screenshots](./docs/screenshots/)

> Screenshots are being added from a clean install (no sample data). The folder above will hold them.

## Requirements

- Windows 10/11, Python 3.11+, administrator rights
- Npcap (`C:\Windows\System32\Npcap\wpcap.dll`)

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

One-shot CLI:

```powershell
.\.venv\Scripts\python.exe main.py --analyze
.\.venv\Scripts\python.exe main.py --block 8.8.8.8
.\.venv\Scripts\python.exe main.py --unblock 8.8.8.8
.\.venv\Scripts\python.exe main.py --list-blocked
```

Other flags: `--no-gui`, `--accept-v05-reset` (confirms the v0.5 storage reset). Ready build: `dist\NetSonar-v0.5.8.exe` + `.bat` (portable, self-updating).

## Features

- **Live capture** — Npcap/scapy capture with per-minute bidirectional `FlowBucket` summaries.
- **Process mapping** — per-process, endpoint, port, and protocol counters (bytes/packets, sent/recv split).
- **AI analysis** — batched structured Gemini analysis; fake IP/source/flow-id rejected by local verification.
- **Threat intel** — VirusTotal reputation + web context; only selected public remote IPs are sent, local/multicast/allowlisted never leave.
- **Key failover** — multiple API keys with automatic failover, DPAPI-encrypted storage.
- **Firewall blocking** — audited bidirectional Windows Firewall rules (`NetSonar` group); off by default, auto-block only on critical + ≥0.95 confidence + `block_now`.
- **SOC panel** — PyQt6 live flow table, metric cards, report view, tray icon.
- **Scheduler** — timed analysis + DB maintenance, desktop notifications.
- **Reports** — JSON/CSV/TXT export.
- **Privacy-first retention** — raw detail dropped, IP-less hourly totals + 30-day audit, unanalyzed detail anonymized in 24h.

## Project structure

```text
main.py              CLI + GUI entry (UAC elevate, single instance)
app_gui.py           SOC panel (ui_components.py, ui_theme.py)
capture_engine.py    live capture (flow_accumulator.py, flow_utils.py)
ai_analyzer.py       Gemini analysis (config/ai_prompt.txt)
threat_intel.py      VirusTotal + web context
database.py          storage (models.py, migration.py)
scheduler.py         timed jobs (notifier.py, custom_alerts.py)
kill_switch.py       firewall blocking
config.py            settings (settings_service.py, DPAPI)
exporter.py          JSON/CSV/TXT reports
packaging/  assets/  tests/  dist/
```

## Contributing

Small PRs, no captures or keys in test data. See [.github/PULL_REQUEST_TEMPLATE.md](./.github/PULL_REQUEST_TEMPLATE.md).

## License

See [LICENSE](./LICENSE) (pending — to be confirmed).
