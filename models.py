"""NetSonar v0.5 core data contracts."""

from dataclasses import dataclass, field
from typing import Literal


Direction = Literal["inbound", "outbound"]


@dataclass(frozen=True, slots=True)
class FlowBucket:
    bucket_start: str
    local_ip: str
    local_port: int
    remote_ip: str
    remote_port: int
    protocol: str
    process: str = "unknown"
    sent_bytes: int = 0
    received_bytes: int = 0
    sent_packets: int = 0
    received_packets: int = 0
    first_seen: str = ""
    last_seen: str = ""


@dataclass(frozen=True, slots=True)
class CaptureHealth:
    state: Literal["stopped", "active", "partial", "error"]
    adapters: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalysisBatch:
    id: int
    status: str
    high_water_id: int
    flow_count: int
    created_at: str


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    risk_score: float
    status: str
    findings: tuple[dict, ...] = ()


@dataclass(frozen=True, slots=True)
class SecurityFinding:
    severity: str
    confidence: float
    evidence: str
    flow_refs: tuple[int, ...]
    status: str = "open"


@dataclass(frozen=True, slots=True)
class AnalysisRun:
    status: str
    risk_score: float
    flow_count: int
    analyzed_at: str
