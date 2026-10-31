"""
NetSonar - Report export module
Exports AI reports as JSON, CSV or TXT.
"""

from i18n import t, status_text as t_status
import json
import csv
from pathlib import Path
from datetime import datetime
from database import Database
from config import user_data_path


def _csv_cell(value) -> str:
    """Escape against CSV formula injection (=, +, -, @, tab, CR leading cells)."""
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def _suspicious_rows(report: dict) -> list[dict]:
    rows = [row for row in report.get("suspicious_connections", []) if isinstance(row, dict)]
    if rows:
        return rows
    for finding in report.get("findings", []) or []:
        for evidence in finding.get("flow_evidence", []) or [{}]:
            rows.append({"ip": evidence.get("remote_ip", ""),
                         "port": evidence.get("remote_port", ""),
                         "process": evidence.get("process", ""),
                         "reason": finding.get("evidence", ""),
                         "action": finding.get("recommended_action", "")})
    return rows


def export_report(report: dict, format: str = "json", filepath: str = None) -> str:
    """
    Export a single report.

    Args:
        report: report dict
        format: "json", "csv" or "txt"
        filepath: target file path (generated automatically when None)

    Returns:
        The path of the saved file
    """
    if filepath is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = format.lower()
        filepath = user_data_path("netsonar_data", "reports", f"rapor_{timestamp}.{ext}")
    
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    if format.lower() == "json":
        return _export_json(report, filepath)
    elif format.lower() == "csv":
        return _export_csv(report, filepath)
    elif format.lower() == "txt":
        return _export_txt(report, filepath)
    else:
        raise ValueError(f"Desteklenmeyen format: {format}")


def _export_json(report: dict, filepath: str) -> str:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return filepath


def _export_csv(report: dict, filepath: str) -> str:
    conns = _suspicious_rows(report)
    
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([t("Analiz Zamanı"), "IP", t("Port"), t("Süreç"), t("Neden"), t("Eylem"), t("Risk Skoru"), t("Durum"), t("Kaynaklar")])
        
        writer.writerow([
            _csv_cell(report.get("analysis_time", report.get("created_at", ""))),
            t("Genel"),
            "",
            "",
            "",
            "",
            _csv_cell(report.get("risk_score", "")),
            _csv_cell(t_status(report.get("status", ""))),
            "",
        ])
        writer.writerow([])
        
        for conn in conns:
            source_urls = [f"{s.get('checked_at','')} {s.get('source_url') or s.get('url') or ''}" for s in
                           (report.get("intel_sources", []) + report.get("web_sources", []))
                           if s.get("indicator") == conn.get("ip")]
            writer.writerow([
                _csv_cell(report.get("analysis_time", report.get("created_at", ""))),
                _csv_cell(conn.get("ip", "")),
                _csv_cell(conn.get("port", "")),
                _csv_cell(conn.get("process", "")),
                _csv_cell(conn.get("reason", "")),
                _csv_cell(conn.get("action", "")),
                _csv_cell(report.get("risk_score", "")),
                _csv_cell(t_status(report.get("status", ""))),
                _csv_cell(" | ".join(source_urls)),
            ])
        
        writer.writerow([])
        writer.writerow([t("Özet")])
        writer.writerow([_csv_cell(report.get("summary", ""))])
    
    return filepath


def _export_txt(report: dict, filepath: str) -> str:
    lines = [
        "=" * 60,
        t("NETSONAR GÜVENLIK RAPORU"),
        "=" * 60,
        t("Risk Skoru: {score}/10", score=report.get('risk_score', '')),
        t("Durum: {status}", status=t_status(report.get('status', ''))),
        t("Tarih: {time}", time=report.get('analysis_time', report.get('created_at', ''))),
        "",
        "=" * 60,
        t("ŞÜPHELI BAĞLANTILAR"),
        "=" * 60,
    ]
    
    conns = _suspicious_rows(report)
    if conns:
        for i, conn in enumerate(conns, 1):
            lines.append(f"\n{i}. IP: {conn.get('ip', '')}")
            lines.append(t("   Port: {port}", port=conn.get('port', '')))
            lines.append(t("   Süreç: {proc}", proc=conn.get('process', '')))
            lines.append(t("   Neden: {reason}", reason=conn.get('reason', '')))
            lines.append(t("   Eylem: {action}", action=conn.get('action', '')))
    else:
        lines.append("\n" + t("Şüpheli bağlantı tespit edilmedi."))
    
    lines.extend([
        "",
        "=" * 60,
        t("AI YORUMU"),
        "=" * 60,
        report.get("summary", ""),
        "",
        "=" * 60,
        t("GÜNCEL KAYNAKLAR"),
        "=" * 60,
        *[f"{s.get('provider','')}: {s.get('indicator','')} @ {s.get('checked_at','')} - {s.get('source_url') or s.get('url','')}"
          for s in (report.get("intel_sources", []) + report.get("web_sources", []))],
        "",
        "=" * 60,
    ])
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    return filepath


def export_all_reports(db: Database, format: str = "json", output_dir: str = None) -> list[str]:
    """
    Export all reports.

    Returns:
        List of the files created
    """
    if output_dir is None:
        output_dir = user_data_path(
            "netsonar_data",
            "reports",
            f"_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    reports = []
    offset = 0
    while True:
        page = db.get_all_reports(limit=100, offset=offset)
        if not page:
            break
        reports.extend(row for row in page if float(row.get("risk_score", 0)) > 0
                       or str(row.get("status", "")).lower() == "risky")
        offset += len(page)
    files = []
    
    for i, row in enumerate(reports, 1):
        content = row.get("content", "{}")
        try:
            report = json.loads(content)
        except json.JSONDecodeError:
            report = {"raw": content}
        
        report["created_at"] = row.get("created_at", "")
        report["analysis_time"] = row.get("created_at", "")
        report["provider"] = row.get("provider", "")
        
        filepath = f"{output_dir}/rapor_{i:03d}.{format}"
        export_report(report, format, filepath)
        files.append(filepath)
    
    return files
