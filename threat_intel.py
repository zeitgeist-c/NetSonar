"""Optional, quota-aware IP reputation and current web enrichment."""

from __future__ import annotations

import ipaddress
import logging
import re
from datetime import datetime, timedelta
from urllib.parse import quote

import requests

log = logging.getLogger("NetSonar.ThreatIntel")
_BACKOFF_UNTIL: dict[str, datetime] = {}


def _is_public_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


def _clean_text(value, limit: int = 500) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def rank_candidates(rows: list[dict], suspicious_ports: set[int],
                    suspicious_processes: set[str], byte_threshold: int) -> list[dict]:
    by_ip: dict[str, dict] = {}
    for row in rows:
        ip = str(row.get("remote_ip", ""))
        if not _is_public_ip(ip):
            continue
        item = by_ip.setdefault(ip, {"ip": ip, "ports": set(), "processes": set(),
            "sent_bytes": 0, "flow_count": 0, "after_hours": False})
        item["ports"].add(int(row.get("remote_port", 0) or 0))
        item["processes"].add(str(row.get("process", "unknown")).lower())
        item["sent_bytes"] += int(row.get("sent_bytes", 0) or 0)
        item["flow_count"] += int(row.get("flow_count", 0) or 0)
        for field in ("first_seen", "last_seen"):
            try:
                hour = datetime.fromisoformat(str(row.get(field, ""))).hour
                item["after_hours"] = item["after_hours"] or 2 <= hour < 6
            except (TypeError, ValueError):
                pass
    ranked = []
    for item in by_ip.values():
        signals = []
        score = 0
        if item["processes"] & {p.lower() for p in suspicious_processes}:
            score += 4; signals.append("suspicious_process")
        if item["ports"] & suspicious_ports:
            score += 3; signals.append("risky_port")
        if item["sent_bytes"] >= byte_threshold:
            score += 2; signals.append("high_outbound_volume")
        if item["flow_count"] >= 3:
            score += 1; signals.append("repeated_connection")
        if item["after_hours"]:
            score += 1; signals.append("after_hours")
        item.update({"local_score": score, "local_signals": signals,
                     "ports": sorted(item["ports"]), "processes": sorted(item["processes"])})
        ranked.append(item)
    return sorted(ranked, key=lambda x: (-x["local_score"], -x["sent_bytes"], x["ip"]))


class ThreatIntelService:
    def __init__(self, db, session=None):
        self.db = db
        self.session = session or requests.Session()

    @staticmethod
    def _expiry(hours: int) -> str:
        return (datetime.now() + timedelta(hours=hours)).isoformat()

    def _allowed(self, provider: str, since: str, limit: int) -> bool:
        until = _BACKOFF_UNTIL.get(provider)
        return (not until or until <= datetime.now()) and self.db.api_usage(provider, since) < limit

    def lookup_virustotal(self, ip: str, cfg) -> dict | None:
        cached = self.db.get_intel_cache("virustotal", ip)
        if cached:
            return cached
        if not cfg.VIRUSTOTAL_API_KEY:
            return None
        minute = (datetime.now() - timedelta(minutes=1)).isoformat()
        day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        if not self._allowed("virustotal", minute, 4) or self.db.api_usage(
                "virustotal", day) >= cfg.VIRUSTOTAL_DAILY_SOFT_LIMIT:
            return None
        try:
            response = self.session.get(
                f"https://www.virustotal.com/api/v3/ip_addresses/{quote(ip, safe='')}",
                headers={"x-apikey": cfg.VIRUSTOTAL_API_KEY}, timeout=15)
            self.db.record_api_usage("virustotal")
            if response.status_code == 429:
                _BACKOFF_UNTIL["virustotal"] = datetime.now() + timedelta(
                    minutes=cfg.THREAT_INTEL_ERROR_BACKOFF_MINUTES)
                return None
            if response.status_code == 404:
                result = {"source_ref": f"vt:{ip}", "provider": "virustotal",
                    "indicator": ip, "verdict": "unknown", "checked_at": datetime.now().isoformat(),
                    "cached": False, "source_url": f"https://www.virustotal.com/gui/ip-address/{ip}"}
                self.db.put_intel_cache("virustotal", ip, result,
                    self._expiry(cfg.THREAT_INTEL_UNKNOWN_CACHE_HOURS))
                return result
            if response.status_code != 200:
                if response.status_code >= 500:
                    _BACKOFF_UNTIL["virustotal"] = datetime.now() + timedelta(
                        minutes=cfg.THREAT_INTEL_ERROR_BACKOFF_MINUTES)
                log.warning("VirusTotal HTTP %d for %s", response.status_code, ip)
                return None
            attributes = response.json().get("data", {}).get("attributes", {})
            stats = attributes.get("last_analysis_stats") or {}
            malicious = int(stats.get("malicious", 0) or 0)
            suspicious = int(stats.get("suspicious", 0) or 0)
            verdict = "malicious" if malicious >= 3 else "suspicious" if (
                malicious or suspicious) else "clean" if stats else "unknown"
            result = {"source_ref": f"vt:{ip}", "provider": "virustotal",
                "indicator": ip, "verdict": verdict, "malicious": malicious,
                "suspicious": suspicious, "harmless": int(stats.get("harmless", 0) or 0),
                "undetected": int(stats.get("undetected", 0) or 0),
                "reputation": int(attributes.get("reputation", 0) or 0),
                "last_analysis_at": attributes.get("last_analysis_date"),
                "checked_at": datetime.now().isoformat(), "cached": False,
                "source_url": f"https://www.virustotal.com/gui/ip-address/{ip}"}
            ttl = cfg.THREAT_INTEL_CACHE_HOURS if verdict != "unknown" else cfg.THREAT_INTEL_UNKNOWN_CACHE_HOURS
            self.db.put_intel_cache("virustotal", ip, result, self._expiry(ttl))
            return result
        except (requests.RequestException, ValueError, TypeError) as exc:
            log.warning("VirusTotal lookup failed for %s: %s", ip, exc)
            return None

    def search_tavily(self, ip: str, cfg) -> list[dict]:
        cached = self.db.get_intel_cache("tavily", ip)
        if cached:
            sources = cached.get("sources", [])
            for source in sources:
                source["cached"] = True
            return sources
        if not cfg.TAVILY_API_KEY:
            return []
        month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        if not self._allowed("tavily", month, cfg.TAVILY_MONTHLY_SOFT_LIMIT):
            return []
        try:
            response = self.session.post("https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {cfg.TAVILY_API_KEY}"}, json={
                    "query": f'"{ip}" malware OR botnet OR C2 OR IOC OR threat intelligence',
                    "search_depth": "basic", "topic": "general", "time_range": "year",
                    "max_results": 5, "include_answer": False, "include_raw_content": False,
                }, timeout=20)
            self.db.record_api_usage("tavily")
            if response.status_code == 429 or response.status_code >= 500:
                _BACKOFF_UNTIL["tavily"] = datetime.now() + timedelta(
                    minutes=cfg.THREAT_INTEL_ERROR_BACKOFF_MINUTES)
                return []
            if response.status_code != 200:
                log.warning("Tavily HTTP %d for %s", response.status_code, ip)
                return []
            sources = []
            for index, item in enumerate(response.json().get("results", [])[:5]):
                url = str(item.get("url", ""))
                if not url.startswith("https://"):
                    continue
                sources.append({"source_ref": f"web:{ip}:{index}", "provider": "tavily",
                    "indicator": ip, "title": _clean_text(item.get("title"), 160),
                    "url": url[:1000], "snippet": _clean_text(item.get("content"), 500),
                    "relevance": max(0.0, min(1.0, float(item.get("score", 0) or 0))),
                    "checked_at": datetime.now().isoformat(), "cached": False})
            data = {"provider": "tavily", "indicator": ip, "sources": sources,
                    "checked_at": datetime.now().isoformat()}
            ttl = cfg.THREAT_INTEL_CACHE_HOURS if sources else cfg.THREAT_INTEL_UNKNOWN_CACHE_HOURS
            self.db.put_intel_cache("tavily", ip, data, self._expiry(ttl))
            return sources
        except (requests.RequestException, ValueError, TypeError) as exc:
            log.warning("Tavily search failed for %s: %s", ip, exc)
            return []

    def enrich_batch(self, batch_id: int, cfg, stage_callback=None) -> dict:
        candidates = rank_candidates(self.db.get_batch_candidate_rows(batch_id),
            cfg.SUSPICIOUS_PORTS, cfg.SUSPICIOUS_PROCESSES, cfg.SUSPICIOUS_BYTES_THRESHOLD)
        vt_results = []
        if stage_callback: stage_callback("VirusTotal kontrol ediliyor…", 25)
        for candidate in candidates[:cfg.VIRUSTOTAL_MAX_LOOKUPS_PER_RUN]:
            result = self.lookup_virustotal(candidate["ip"], cfg)
            if result:
                vt_results.append(result)
        vt_by_ip = {item["indicator"]: item for item in vt_results}
        web_candidates = [item for item in candidates if item["local_score"] >= 4 or
            vt_by_ip.get(item["ip"], {}).get("verdict") in {"malicious", "suspicious"}]
        web_sources = []
        if stage_callback: stage_callback("Güncel web kaynakları aranıyor…", 40)
        for candidate in web_candidates[:cfg.TAVILY_MAX_SEARCHES_PER_RUN]:
            web_sources.extend(self.search_tavily(candidate["ip"], cfg))
        return {"candidates": candidates, "virustotal": vt_results, "web_sources": web_sources,
            "status": {"virustotal": "active" if cfg.VIRUSTOTAL_API_KEY else "disabled",
                       "tavily": "active" if cfg.TAVILY_API_KEY else "disabled"}}
