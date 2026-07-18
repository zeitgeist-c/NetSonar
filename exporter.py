"""
NetSonar — Rapor Dışa Aktarma Modülü
AI raporlarını JSON, CSV veya TXT olarak dışa aktarır.
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from database import Database
from config import user_data_path


def export_report(report: dict, format: str = "json", filepath: str = None) -> str:
    """
    Bir raporu dışa aktarır.
    
    Args:
        report: Rapor dict'i
        format: "json", "csv" veya "txt"
        filepath: Kaydedilecek dosya yolu (None olursa otomatik oluştur)
    
    Returns:
        Kaydedilen dosya yolu
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
    conns = report.get("suspicious_connections", [])
    
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["IP", "Port", "Process", "Reason", "Action", "Risk Score", "Status"])
        
        writer.writerow([
            "Genel",
            "",
            "",
            "",
            "",
            report.get("risk_score", ""),
            report.get("status", ""),
        ])
        writer.writerow([])
        
        for conn in conns:
            writer.writerow([
                conn.get("ip", ""),
                conn.get("port", ""),
                conn.get("process", ""),
                conn.get("reason", ""),
                conn.get("action", ""),
                report.get("risk_score", ""),
                report.get("status", ""),
            ])
        
        writer.writerow([])
        writer.writerow(["Özet"])
        writer.writerow([report.get("summary", "")])
    
    return filepath


def _export_txt(report: dict, filepath: str) -> str:
    lines = [
        "=" * 60,
        "NETSONAR GÜVENLIK RAPORU",
        "=" * 60,
        f"Risk Skoru: {report.get('risk_score', '')}/10",
        f"Durum: {report.get('status', '')}",
        f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "=" * 60,
        "ŞÜPHELI BAĞLANTILAR",
        "=" * 60,
    ]
    
    conns = report.get("suspicious_connections", [])
    if conns:
        for i, conn in enumerate(conns, 1):
            lines.append(f"\n{i}. IP: {conn.get('ip', '')}")
            lines.append(f"   Port: {conn.get('port', '')}")
            lines.append(f"   Süreç: {conn.get('process', '')}")
            lines.append(f"   Neden: {conn.get('reason', '')}")
            lines.append(f"   Eylem: {conn.get('action', '')}")
    else:
        lines.append("\nŞüpheli bağlantı tespit edilmedi.")
    
    lines.extend([
        "",
        "=" * 60,
        "AI YORUMU",
        "=" * 60,
        report.get("summary", ""),
        "",
        "=" * 60,
    ])
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    return filepath


def export_all_reports(db: Database, format: str = "json", output_dir: str = None) -> list[str]:
    """
    Tüm raporları dışa aktarır.
    
    Returns:
        Oluşturulan dosyaların listesi
    """
    if output_dir is None:
        output_dir = user_data_path(
            "netsonar_data",
            "reports",
            f"_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    reports = db.get_all_reports()
    files = []
    
    for i, row in enumerate(reports, 1):
        content = row.get("content", "{}")
        try:
            report = json.loads(content)
        except json.JSONDecodeError:
            report = {"raw": content}
        
        report["created_at"] = row.get("created_at", "")
        report["provider"] = row.get("provider", "")
        
        filepath = f"{output_dir}/rapor_{i:03d}.{format}"
        export_report(report, format, filepath)
        files.append(filepath)
    
    return files
