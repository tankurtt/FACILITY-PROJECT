from __future__ import annotations

import ast
import csv
import math
import queue
import random
import re
import statistics
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
import tkinter as tk
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import simpy
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "SimPy kurulu değil. Önce şu komutu çalıştırın:\n\n"
        "    pip install simpy\n"
    ) from exc

# -----------------------------------------------------------------------------
# Varsayılan ayarlar
# -----------------------------------------------------------------------------

DEFAULT_ARRIVAL_MEAN = 8.0
DEFAULT_PRODUCTION_TIME = 800.0
DEFAULT_ASSEMBLY_TIME = 800.0
DEFAULT_REPLICATIONS = 5
DEFAULT_SEED = 42
DEFAULT_SCRAP_RATE = 0.02
ANIM_SCALE = 0.03
DEFAULT_ZOOM = 0.50
MIN_ZOOM = 0.35
MAX_ZOOM = 2.0
ZOOM_STEP = 0.1
EPS = 1e-9

DEFAULT_MULTI_FLOW_TEXT = '[Kaynaklar]\n100T Mechanical Press: 3\n160T Mechanical Press: 2\n60T Compact Press: 1\nHeat Treatment – Hardening: 2\nHeat Treatment – Tempering: 2\nSurface Grinder: 1\nCNC Lathe: 1\nCNC Spring Coiling Machine: 3\nStress Relief Oven: 2\nhardened progressive die set: 1\n\n[Akış: P012]\nCreate -> Transfer 1\nTransfer 1: (0.12, 0.15, 0.19) -> Kesme Şekillendirme Delme\nKesme Şekillendirme Delme: (11.5, 13.2, 15.4) | 100T Mechanical Press -> Kalite Kontrol 1\nKalite Kontrol 1: (6.8, 8, 9.4) -> Çapak Alma\nÇapak Alma: (2.4, 3, 3.8) -> Kalite Kontrol 2\nKalite Kontrol 2: (5.0, 6, 7.1) -> Yüzey Hazırlama\nYüzey Hazırlama: (1.4, 1.8, 2.2) -> Kaplama\nKaplama: (5.0, 6, 7.2) -> Kalite Kontrol 3\nKalite Kontrol 3: (8.7, 10, 11.6) -> Montaj Alanına Transfer\nMontaj Alanına Transfer: (0.08, 0.10, 0.13)\nScrap: 2.0\n\n[Akış: P021]\nCreate -> Transfer 1\nTransfer 1: (0.12, 0.15, 0.19) -> Kesme Bükme Delme Şekillendirme\nKesme Bükme Delme Şekillendirme: (14.0, 16.2, 18.7) | 100T Mechanical Press -> Kalite Kontrol 1\nKalite Kontrol 1: (8.5, 10, 11.8) -> Çapak Alma\nÇapak Alma: (2.4, 3, 3.8) -> Kalite Kontrol 2\nKalite Kontrol 2: (4.2, 5, 5.9) -> Korozyon Koruma\nKorozyon Koruma: (1.9, 2.4, 3.0) -> Montaj Alanına Transfer\nMontaj Alanına Transfer: (0.08, 0.10, 0.13)\nScrap: 2.0\n\n[Akış: P022]\nCreate -> Transfer 1\nTransfer 1: (13, 15, 17.5) -> Presleme Şekillendirme Delme\nPresleme Şekillendirme Delme: (13.2, 15, 17.2) | 160T Mechanical Press + hardened progressive die set -> Kalite Kontrol 1\nKalite Kontrol 1: (10.2, 12, 13.8) -> Sertleştirme\nSertleştirme: (15.5, 18, 21.0) | Heat Treatment – Hardening -> Quenching\nQuenching: (1.5, 1.8, 2.2) -> Temperleme\nTemperleme: (15.5, 18, 21.0) | Heat Treatment – Tempering -> Sertlik Kontrol\nSertlik Kontrol: (13, 15, 17.2) -> Boyutsal Kontrol\nBoyutsal Kontrol: (8.8, 10, 11.4) -> Yüzey Taşlama\nYüzey Taşlama: (3.8, 4.5, 5.3) | Surface Grinder -> Kalite Kontrol 2\nKalite Kontrol 2: (0.32, 0.4, 0.52) -> Koruyucu Uygulama\nKoruyucu Uygulama: (6.8, 8, 9.5) -> Montaj Alanına Transfer\nMontaj Alanına Transfer: (0.08, 0.10, 0.13)\nScrap: 3.0\n\n[Akış: P023]\nCreate -> Transfer 1\nTransfer 1: (3.2, 4, 5.0) -> Form Verme\nForm Verme: (3.2, 4, 5.0) -> CNC Tornalama\nCNC Tornalama: (10.5, 12, 13.8) | 100T Mechanical Press -> Kalite Kontrol 1\nKalite Kontrol 1: (6.8, 8, 9.4) -> Çapak Alma\nÇapak Alma: (1.0, 1.2, 1.5) -> Görsel Kontrol\nGörsel Kontrol: (4.2, 5, 6.0) -> Koruyucu\nKoruyucu: (1.0, 1.2, 1.5) -> Montaj Alanına Transfer\nMontaj Alanına Transfer: (0.06, 0.08, 0.10)\nScrap: 2.0\n\n[Akış: P024]\nCreate -> Transfer 1\nTransfer 1: (0.06, 0.08, 0.10) -> CNC Torna İşlemleri\nCNC Torna İşlemleri: (9.6, 11, 12.8) | CNC Lathe -> Kalite Kontrol 1\nKalite Kontrol 1: (5.2, 6, 7.1) -> Yüzey Parlatma\nYüzey Parlatma: (1.2, 1.5, 1.9) -> Kontrol 2\nKontrol 2: (4.2, 5, 6.0) -> Koruyucu\nKoruyucu: (4.2, 5, 6.0) -> Montaj Alanına Transfer\nMontaj Alanına Transfer: (0.06, 0.08, 0.10)\nScrap: 2.0\n\n[Akış: P025]\nCreate -> Wire Coiling\nWire Coiling: (4.2, 5, 5.9) | CNC Spring Coiling Machine -> End Grinding\nEnd Grinding: (8.8, 10, 11.8) -> Kalite Kontrol 1\nKalite Kontrol 1: (4.2, 5, 6.0) -> Isıl İşlem\nIsıl İşlem: (10.2, 12, 14.4) | Stress Relief Oven -> Spring Test\nSpring Test: (6.8, 8, 9.4) -> Geometrik Kontrol\nGeometrik Kontrol: (5.0, 6, 7.1) -> Preset\nPreset: (3.2, 4, 4.8) -> Korozyon Koruma\nKorozyon Koruma: (1.4, 1.8, 2.2) -> Montaj Alanına Transfer\nMontaj Alanına Transfer: (0.06, 0.08, 0.10)\nScrap: 2.0\n\n[Akış: P026]\nCreate -> Wire Coiling\nWire Coiling: (4.2, 5, 5.9) | CNC Spring Coiling Machine -> Şekillendirme\nŞekillendirme: (5.0, 6, 7.1) -> Kontrol\nKontrol: (5.0, 6, 7.1) -> Isıl İşlem\nIsıl İşlem: (10.2, 12, 14.4) | Stress Relief Oven -> Test\nTest: (6.8, 8, 9.4) -> Preset\nPreset: (3.2, 4, 4.8) -> Korozyon Koruma\nKorozyon Koruma: (1.4, 1.8, 2.2) -> Montaj Alanına Transfer\nMontaj Alanına Transfer: (0.06, 0.08, 0.10)\nScrap: 2.0\n\n[Akış: P032]\nCreate -> Transfer 1\nTransfer 1: (0.08, 0.10, 0.13) -> Pres İşlemleri\nPres İşlemleri: (7.5, 9, 10.8) | 60T Compact Press -> Kalite Kontrol 1\nKalite Kontrol 1: (5.2, 6, 7.1) -> Çapak Alma\nÇapak Alma: (2.4, 3, 3.8) -> Kalite Kontrol 2\nKalite Kontrol 2: (4.2, 5, 5.9) -> Yüzey İşlemi\nYüzey İşlemi: (1.0, 1.2, 1.5) -> Montaj Alanına Transfer\nMontaj Alanına Transfer: (0.06, 0.08, 0.10)\nScrap: 2.0\n\n[Akış: P027]\nCreate -> Wire Coiling\nWire Coiling: (3.2, 4, 4.8) | CNC Spring Coiling Machine -> Şekillendirme\nŞekillendirme: (3.2, 4, 4.8) -> Geometrik Kontrol\nGeometrik Kontrol: (4.2, 5, 6.0) -> Isıl İşlem\nIsıl İşlem: (5.0, 6, 7.2) | Stress Relief Oven -> Yay Çekme Testi\nYay Çekme Testi: (4.2, 5, 6.0) -> Preset\nPreset: (2.4, 3, 3.6) -> Korozyon Koruma\nKorozyon Koruma: (1.0, 1.2, 1.5) -> Montaj Alanına Transfer\nMontaj Alanına Transfer: (0.06, 0.08, 0.10)\nScrap: 1.5\n\n[Akış: P011]\nCreate -> Transfer\nTransfer: (4.2, 5, 6.0)\nScrap: 1.5\n\n[Akış: P013]\nCreate -> Transfer\nTransfer: (4.2, 5, 6.0)\nScrap: 1.5\n\n[Akış: P031]\nCreate -> Transfer\nTransfer: (4.2, 5, 6.0)\nScrap: 1.5\n\n[Akış: U Montaj Hattı]\nDepo -> Istasyon 1\nIstasyon 1: (11, 13, 15)\nIstasyon 2: (19, 19, 19)\nIstasyon 3: (6.3, 8, 9.4)\nScrap: 1\n'

# -----------------------------------------------------------------------------
# Veri sınıfları
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessStep:
    """Bir proses adımı: triangular süre + opsiyonel kaynak listesi."""

    name: str
    duration: Tuple[float, float, float]
    resources: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FlowDefinition:
    """Bir ürün/akış rotası."""

    name: str
    entry_kind: str  # "create" veya "depot"
    steps: Tuple[ProcessStep, ...]
    scrap_rate: float
    terminal: str  # "Depo" veya "Dispose"

    @property
    def is_assembly(self) -> bool:
        return self.entry_kind == "depot"

    @property
    def visual_nodes(self) -> List[str]:
        start = "Depo" if self.is_assembly else "Create"
        end = self.terminal
        nodes = [start] + [s.name for s in self.steps]
        if self.scrap_rate > 0:
            nodes.append("Scrap")
        nodes.append(end)
        return nodes


@dataclass(frozen=True)
class NetworkDefinition:
    flows: Tuple[FlowDefinition, ...]
    resources: Dict[str, int]

    @property
    def source_flows(self) -> Tuple[FlowDefinition, ...]:
        return tuple(f for f in self.flows if not f.is_assembly)

    @property
    def assembly_flows(self) -> Tuple[FlowDefinition, ...]:
        return tuple(f for f in self.flows if f.is_assembly)


@dataclass
class FlowStats:
    created: int = 0
    started_from_depot: int = 0
    good_to_depot: int = 0
    scrapped: int = 0
    finished_products: int = 0
    completed: int = 0
    cycle_times: List[float] = field(default_factory=list)
    queue_times: List[float] = field(default_factory=list)
    process_times: List[float] = field(default_factory=list)

    def to_row(self, flow_name: str, entry_kind: str) -> Dict[str, Any]:
        return {
            "flow": flow_name,
            "entry_kind": entry_kind,
            "created": self.created,
            "started_from_depot": self.started_from_depot,
            "good_to_depot": self.good_to_depot,
            "scrapped": self.scrapped,
            "finished_products": self.finished_products,
            "completed": self.completed,
            "avg_cycle_time": mean_or_zero(self.cycle_times),
            "avg_queue_time": mean_or_zero(self.queue_times),
            "avg_process_time": mean_or_zero(self.process_times),
        }


@dataclass
class ResourceStats:
    capacity: int
    requests: int = 0
    queue_wait_total: float = 0.0
    busy_time_total: float = 0.0

    def utilization(self, horizon: float) -> float:
        denom = max(EPS, horizon * self.capacity)
        return min(1.0, self.busy_time_total / denom)

    def avg_queue_wait(self) -> float:
        return self.queue_wait_total / self.requests if self.requests else 0.0


@dataclass
class ReplicationResult:
    rep_no: int
    seed: int
    sim_time_end: float
    stopped: bool
    flow_stats: Dict[str, FlowStats]
    resource_stats: Dict[str, ResourceStats]
    depot_remaining: Dict[str, int]
    terminal_finished_products: int
    event_log: List[Dict[str, Any]] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# -----------------------------------------------------------------------------


def mean_or_zero(values: Iterable[float]) -> float:
    values = list(values)
    return float(sum(values) / len(values)) if values else 0.0


def stdev_or_zero(values: Iterable[float]) -> float:
    values = list(values)
    return float(statistics.stdev(values)) if len(values) > 1 else 0.0


def normalize_name(name: str) -> str:
    return " ".join((name or "").strip().split())


def sample_triangular(rng: random.Random, low: float, mode: float, high: float) -> float:
    """Triangular dağılım örneklemesi. Parametre sırası: low, mode, high."""
    if low < 0 or mode < 0 or high < 0:
        raise ValueError("Süre değerleri negatif olamaz.")
    if not (low <= mode <= high):
        raise ValueError(f"Triangular süre sırası hatalı: ({low}, {mode}, {high})")
    return rng.triangular(low, high, mode)


def parse_triplet(spec_text: str) -> Optional[Tuple[float, float, float]]:
    text = (spec_text or "").strip()
    if not text:
        return None
    try:
        obj = ast.literal_eval(text)
        if isinstance(obj, (tuple, list)) and len(obj) == 3:
            triplet = tuple(float(x) for x in obj)
            low, mode, high = triplet
            if not (low <= mode <= high):
                raise ValueError(f"Triangular süre sırası hatalı: {triplet}")
            return triplet  # type: ignore[return-value]
    except ValueError:
        raise
    except Exception:
        pass

    cleaned = text.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    if len(parts) != 3:
        raise ValueError(f"Geçersiz süre tanımı: {spec_text}")
    triplet = tuple(float(x) for x in parts)
    low, mode, high = triplet
    if not (low <= mode <= high):
        raise ValueError(f"Triangular süre sırası hatalı: {triplet}")
    return triplet  # type: ignore[return-value]


def parse_resource_list(resource_text: str) -> Tuple[str, ...]:
    """Kaynakları ayırır. 'A + B', 'A, B', 'A; B' formatlarını destekler."""
    if not resource_text:
        return tuple()
    txt = resource_text.strip().strip("[](){}")
    parts = [p.strip() for p in re.split(r"\s+\+\s+|[,;/]", txt) if p.strip()]
    seen: Dict[str, None] = {}
    for part in parts:
        seen[normalize_name(part)] = None
    return tuple(seen.keys())


def split_triplet_and_resources(spec_text: str) -> Tuple[Optional[str], Tuple[str, ...]]:
    text = (spec_text or "").strip()
    if not text:
        return None, tuple()
    if re.search(r"\s*(\||@|;)\s*", text):
        left, right = re.split(r"\s*(?:\||@|;)\s*", text, maxsplit=1)
        return left.strip(), parse_resource_list(right.strip())
    return text, tuple()


def parse_scrap_rate(text: str) -> float:
    raw = (text or "").strip()
    if not raw:
        return DEFAULT_SCRAP_RATE
    has_percent = raw.endswith("%")
    raw_clean = raw.replace("%", "").strip()
    val = float(raw_clean)
    if val < 0:
        raise ValueError("Scrap oranı negatif olamaz.")
    if has_percent:
        return val / 100.0
    
    if val < 1.0:
        return val
    if val <= 100.0:
        return val / 100.0
    raise ValueError("Scrap oranı 0-100 ya da 0-1 aralığında olmalı.")


def parse_header(line: str) -> Optional[Tuple[str, Optional[str]]]:
    header_re = re.compile(r"^\[(.+)\]$")
    plain_re = re.compile(r"^([^:]+):\s*(.*)$")

    m = header_re.match(line)
    if m:
        content = m.group(1).strip()
        low = content.lower()
        if low in ("kaynaklar", "resources"):
            return "resources", None
        if low.startswith("akış:") or low.startswith("flow:"):
            _, rest = content.split(":", 1)
            return "flow", normalize_name(rest)
        return "flow", normalize_name(content)

    m = plain_re.match(line)
    if m:
        head = m.group(1).strip().lower()
        rest = m.group(2).strip()
        if head in ("kaynaklar", "resources") and not rest:
            return "resources", None
        if head in ("akış", "flow") and rest:
            return "flow", normalize_name(rest)
    return None


def split_sections(text: str) -> List[Dict[str, Any]]:
    lines = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        lines.append(line.strip())
    if not lines:
        raise ValueError("Tanım metni boş.")

    sections: List[Dict[str, Any]] = []
    current_kind: Optional[str] = None
    current_name: Optional[str] = None
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_kind, current_name, current_lines
        if current_lines:
            sections.append(
                {
                    "kind": current_kind or "flow",
                    "name": current_name,
                    "text": "\n".join(current_lines),
                }
            )
        current_kind = None
        current_name = None
        current_lines = []

    for line in lines:
        header = parse_header(line)
        if header:
            flush()
            current_kind, current_name = header
            continue
        current_lines.append(line)
    flush()

    if not sections:
        raise ValueError("En az bir akış veya kaynak tanımı girilmeli.")
    if len(sections) == 1 and sections[0]["kind"] == "flow" and sections[0]["name"] is None:
        sections[0]["name"] = "Akış 1"

    seen: Dict[str, int] = {}
    for section in sections:
        if section["kind"] != "flow":
            continue
        base = normalize_name(section["name"] or "Akış")
        seen[base] = seen.get(base, 0) + 1
        section["name"] = base if seen[base] == 1 else f"{base} ({seen[base]})"
    return sections


def parse_resource_lines(text: str) -> Dict[str, int]:
    resources: Dict[str, int] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(.+?)(?:\s*[:=]\s*|\s+)(\d+)\s*$", line)
        if not m:
            raise ValueError(f"Geçersiz kaynak satırı: {line}")
        name = normalize_name(m.group(1))
        cap = int(m.group(2))
        if cap <= 0:
            raise ValueError(f"Kaynak kapasitesi 0'dan büyük olmalı: {name}")
        if name in resources:
            raise ValueError(f"Kaynak adı eşsiz olmalı: {name}")
        resources[name] = cap
    return resources


def parse_single_flow_text(text: str, default_name: str) -> FlowDefinition:
    """Tek bir akışı parse eder. Geriye doğrusal rota döndürür."""
    lines = [raw.strip() for raw in text.splitlines() if raw.strip() and not raw.strip().startswith("#")]
    if not lines:
        raise ValueError(f"{default_name}: akış tanımı boş.")

    steps_by_name: Dict[str, ProcessStep] = {}
    order: List[str] = []
    edges: Dict[str, str] = {}
    has_create = False
    has_depot = False
    scrap_rate = DEFAULT_SCRAP_RATE

    for line in lines:
        left, right = (line.split("->", 1) + [""])[:2] if "->" in line else (line, "")
        left = left.strip()
        right = normalize_name(right.strip())

        if ":" in left:
            name_part, spec_part = left.split(":", 1)
            name = normalize_name(name_part)
            if name.lower() == "scrap":
                scrap_rate = parse_scrap_rate(spec_part)
                continue
            triplet_text, resources = split_triplet_and_resources(spec_part)
            triplet = parse_triplet(triplet_text or "")
            if triplet is None:
                raise ValueError(f"{default_name}: {name} için süre tanımı eksik.")
            if name in steps_by_name:
                raise ValueError(f"{default_name}: aynı proses adı iki kez kullanılmış: {name}")
            steps_by_name[name] = ProcessStep(name=name, duration=triplet, resources=resources)
            order.append(name)
        else:
            name = normalize_name(left)
            if name.lower() == "create":
                has_create = True
            elif name.lower() == "depo":
                has_depot = True
            elif name.lower() in ("dispose", "scrap"):
                pass
            elif name:
                
                if right:
                    raise ValueError(
                        f"{default_name}: '{name}' için süre tanımı yok. "
                        "Proses satırı 'Ad: (low, mode, high)' şeklinde olmalı."
                    )

        if right:
            edges[name] = right

    if has_depot and has_create:
        raise ValueError(f"{default_name}: aynı akış hem Create hem Depo ile başlayamaz.")
    entry_kind = "depot" if has_depot else "create"
    terminal = "Dispose" if entry_kind == "depot" else "Depo"

    if not steps_by_name:
        raise ValueError(f"{default_name}: en az bir proses bloğu tanımlanmalı.")

    
    start_node = "Depo" if entry_kind == "depot" else "Create"
    route: List[str] = []
    current = edges.get(start_node)
    visited: set[str] = set()
    while current and current in steps_by_name:
        if current in visited:
            raise ValueError(f"{default_name}: rota içinde döngü var: {current}")
        visited.add(current)
        route.append(current)
        current = edges.get(current)

    for name in order:
        if name not in visited:
            route.append(name)
            visited.add(name)

    steps = tuple(steps_by_name[name] for name in route)
    return FlowDefinition(
        name=normalize_name(default_name),
        entry_kind=entry_kind,
        steps=steps,
        scrap_rate=float(scrap_rate),
        terminal=terminal,
    )


def parse_network_text(text: str) -> NetworkDefinition:
    sections = split_sections(text)
    resources: Dict[str, int] = {}
    flows: List[FlowDefinition] = []

    for section in sections:
        if section["kind"] == "resources":
            parsed = parse_resource_lines(section["text"])
            for name, cap in parsed.items():
                if name in resources:
                    raise ValueError(f"Kaynak adı eşsiz olmalı: {name}")
                resources[name] = cap
        else:
            flows.append(parse_single_flow_text(section["text"], default_name=section["name"] or "Akış"))

    if not flows:
        raise ValueError("En az bir akış tanımlanmalı.")

    referenced = sorted({res for flow in flows for step in flow.steps for res in step.resources})
    missing = [r for r in referenced if r not in resources]
    if missing:
        raise ValueError("Kaynaklar bölümünde tanımlanmamış kaynak(lar): " + ", ".join(missing))

    assembly_count = sum(1 for f in flows if f.is_assembly)
    if assembly_count > 1:
        raise ValueError("Bu sürümde aynı model içinde tek montaj/depo akışı desteklenir.")
    if assembly_count and not any((not f.is_assembly and f.terminal == "Depo") for f in flows):
        raise ValueError("Montaj akışı varsa depoya parça gönderen en az bir kaynak akış olmalı.")

    return NetworkDefinition(flows=tuple(flows), resources=resources)


# -----------------------------------------------------------------------------
# Simülasyon çekirdeği
# -----------------------------------------------------------------------------


class SimulationEngine:
    def __init__(
        self,
        network: NetworkDefinition,
        production_time: float,
        assembly_time: float,
        arrival_mean: float,
        start_at_zero: bool,
        seed: int,
    ) -> None:
        if production_time <= 0 or assembly_time <= 0:
            raise ValueError("Üretim ve montaj süresi 0'dan büyük olmalı.")
        if assembly_time < production_time:
            raise ValueError("Montaj süresi, üretim süresinden küçük olamaz.")
        if arrival_mean <= 0:
            raise ValueError("Gelişler arası ortalama süre 0'dan büyük olmalı.")

        self.network = network
        self.production_time = float(production_time)
        self.assembly_time = float(assembly_time)
        self.arrival_mean = float(arrival_mean)
        self.start_at_zero = bool(start_at_zero)
        self.rng = random.Random(int(seed))
        self.seed = int(seed)

    def run(
        self,
        rep_no: int = 1,
        stop_event: Optional[threading.Event] = None,
        collect_log: bool = False,
    ) -> ReplicationResult:
        env = simpy.Environment()
        event_log: List[Dict[str, Any]] = []

        source_flows = [f for f in self.network.flows if not f.is_assembly and f.terminal == "Depo"]
        source_names = [f.name for f in source_flows]
        depot_stores: Dict[str, simpy.Store] = {name: simpy.Store(env) for name in source_names}

        resource_pools = {
            name: simpy.Resource(env, capacity=cap)
            for name, cap in self.network.resources.items()
        }
        resource_stats = {
            name: ResourceStats(capacity=cap)
            for name, cap in self.network.resources.items()
        }
        flow_stats = {flow.name: FlowStats() for flow in self.network.flows}

        def stopped() -> bool:
            return bool(stop_event is not None and stop_event.is_set())

        def emit(evt_type: str, flow: str, pid: int, block_idx: int, extra: Optional[Dict[str, Any]] = None) -> None:
            if collect_log:
                event_log.append(
                    {
                        "type": evt_type,
                        "time": float(env.now),
                        "flow": flow,
                        "pid": int(pid),
                        "block": int(block_idx),
                        "extra": extra or {},
                    }
                )

        def run_process_steps(flow: FlowDefinition, pid: int, created_at: float):
            stats = flow_stats[flow.name]
            entity_queue_time = 0.0
            entity_process_time = 0.0

            
            if flow.steps:
                emit("move", flow.name, pid, 1)

            for step_idx, step in enumerate(flow.steps, start=1):
                acquired: List[Tuple[str, Any]] = []
                try:
                    
                    for res_name in sorted(set(step.resources)):
                        pool = resource_pools[res_name]
                        res_stat = resource_stats[res_name]
                        request_started = env.now
                        req = pool.request()
                        res_stat.requests += 1
                        yield req
                        wait = env.now - request_started
                        res_stat.queue_wait_total += wait
                        entity_queue_time += wait
                        acquired.append((res_name, req))

                    duration = sample_triangular(self.rng, *step.duration)
                    entity_process_time += duration
                    emit("step_start", flow.name, pid, step_idx, {"step": step.name, "duration": duration})
                    yield env.timeout(duration)
                    for res_name, _ in acquired:
                        resource_stats[res_name].busy_time_total += duration
                    emit("step_finish", flow.name, pid, step_idx, {"step": step.name})

                finally:
                    for res_name, req in reversed(acquired):
                        try:
                            resource_pools[res_name].release(req)
                        except RuntimeError:
                            pass

                
                next_block = step_idx + 1
                if step_idx < len(flow.steps):
                    emit("move", flow.name, pid, next_block)

            
            if flow.scrap_rate > 0:
                scrap_block = 1 + len(flow.steps)
                emit("move", flow.name, pid, scrap_block)
                emit("scrap_check", flow.name, pid, scrap_block, {"rate": flow.scrap_rate})
                if self.rng.random() < flow.scrap_rate:
                    stats.scrapped += 1
                    stats.completed += 1
                    stats.cycle_times.append(env.now - created_at)
                    stats.queue_times.append(entity_queue_time)
                    stats.process_times.append(entity_process_time)
                    emit("dispose", flow.name, pid, scrap_block, {"reason": "scrap"})
                    return

            terminal_block = len(flow.visual_nodes) - 1
            if flow.terminal == "Depo":
                stats.good_to_depot += 1
                stats.completed += 1
                stats.cycle_times.append(env.now - created_at)
                stats.queue_times.append(entity_queue_time)
                stats.process_times.append(entity_process_time)
                emit("handoff", flow.name, pid, terminal_block, {"to": "Depo"})
                if flow.name in depot_stores:
                    yield depot_stores[flow.name].put({"flow": flow.name, "pid": pid, "ready_time": env.now})
                return

            stats.finished_products += 1
            stats.completed += 1
            stats.cycle_times.append(env.now - created_at)
            stats.queue_times.append(entity_queue_time)
            stats.process_times.append(entity_process_time)
            emit("dispose", flow.name, pid, terminal_block, {"reason": "finished_product"})

        def source_generator(flow: FlowDefinition):
            pid = 0
            if not self.start_at_zero:
                first_delay = self.rng.expovariate(1.0 / self.arrival_mean)
                if first_delay >= self.production_time - EPS:
                    return
                yield env.timeout(first_delay)

            while not stopped() and env.now < self.production_time - EPS:
                pid += 1
                flow_stats[flow.name].created += 1
                emit("create", flow.name, pid, 0)
                env.process(run_process_steps(flow, pid, env.now))
                delay = self.rng.expovariate(1.0 / self.arrival_mean)
                yield env.timeout(delay)

        def assembly_generator(flow: FlowDefinition):
            pid = 0
            required_sources = list(source_names)
            if not required_sources:
                return
            while not stopped() and env.now < self.assembly_time - EPS:
                get_events = [depot_stores[src].get() for src in required_sources]
                yield simpy.AllOf(env, get_events)
                if stopped() or env.now >= self.assembly_time - EPS:
                    break
                pid += 1
                flow_stats[flow.name].created += 1
                flow_stats[flow.name].started_from_depot += 1
                emit("spawn", flow.name, pid, 0, {"required_parts": len(required_sources)})
                env.process(run_process_steps(flow, pid, env.now))

        def end_marker():
            yield env.timeout(self.assembly_time)

        env.process(end_marker())
        for flow in self.network.flows:
            if flow.is_assembly:
                env.process(assembly_generator(flow))
            else:
                env.process(source_generator(flow))

        while True:
            if stopped():
                break
            next_time = env.peek()
            if next_time == float("inf"):
                break
            if next_time > self.assembly_time + EPS:
                break
            env.step()

        depot_remaining = {name: len(store.items) for name, store in depot_stores.items()}
        assembly_flows = [f for f in self.network.flows if f.is_assembly]
        if assembly_flows:
            terminal_finished = sum(flow_stats[f.name].finished_products for f in assembly_flows)
        else:
            terminal_finished = sum(flow_stats[f.name].finished_products + flow_stats[f.name].good_to_depot for f in self.network.flows)

        event_log.sort(key=lambda e: (e["time"], e["flow"], e["pid"], e["block"]))
        return ReplicationResult(
            rep_no=rep_no,
            seed=self.seed,
            sim_time_end=float(env.now),
            stopped=stopped(),
            flow_stats=flow_stats,
            resource_stats=resource_stats,
            depot_remaining=depot_remaining,
            terminal_finished_products=int(terminal_finished),
            event_log=event_log,
        )


# -----------------------------------------------------------------------------
# Sonuç birleştirme ve export
# -----------------------------------------------------------------------------


def aggregate_results(results: List[ReplicationResult], network: NetworkDefinition, horizon: float) -> Dict[str, Any]:
    if not results:
        raise ValueError("Birleştirilecek sonuç yok.")

    terminal_values = [r.terminal_finished_products for r in results]
    overall = {
        "replications": len(results),
        "terminal_finished_avg": mean_or_zero(terminal_values),
        "terminal_finished_stdev": stdev_or_zero(terminal_values),
        "terminal_finished_min": min(terminal_values),
        "terminal_finished_max": max(terminal_values),
        "stopped": any(r.stopped for r in results),
        "avg_sim_time_end": mean_or_zero([r.sim_time_end for r in results]),
    }

    flow_rows: List[Dict[str, Any]] = []
    for flow in network.flows:
        per_rep_rows = [r.flow_stats[flow.name].to_row(flow.name, flow.entry_kind) for r in results]
        row = {"flow": flow.name, "entry_kind": flow.entry_kind}
        numeric_keys = [k for k in per_rep_rows[0].keys() if k not in ("flow", "entry_kind")]
        for key in numeric_keys:
            vals = [float(x[key]) for x in per_rep_rows]
            row[f"{key}_avg"] = mean_or_zero(vals)
            row[f"{key}_stdev"] = stdev_or_zero(vals)
        row["scrap_rate_input"] = flow.scrap_rate
        flow_rows.append(row)

    resource_rows: List[Dict[str, Any]] = []
    for res_name, cap in network.resources.items():
        util_vals = [r.resource_stats[res_name].utilization(horizon) for r in results]
        req_vals = [r.resource_stats[res_name].requests for r in results]
        q_vals = [r.resource_stats[res_name].avg_queue_wait() for r in results]
        busy_vals = [r.resource_stats[res_name].busy_time_total for r in results]
        resource_rows.append(
            {
                "resource": res_name,
                "capacity": cap,
                "utilization_avg_percent": 100 * mean_or_zero(util_vals),
                "utilization_stdev_percent": 100 * stdev_or_zero(util_vals),
                "requests_avg": mean_or_zero(req_vals),
                "avg_queue_wait_avg": mean_or_zero(q_vals),
                "busy_time_avg": mean_or_zero(busy_vals),
            }
        )

    depot_keys = sorted({k for r in results for k in r.depot_remaining})
    depot_rows = [
        {
            "source_flow": k,
            "remaining_avg": mean_or_zero([r.depot_remaining.get(k, 0) for r in results]),
            "remaining_stdev": stdev_or_zero([r.depot_remaining.get(k, 0) for r in results]),
        }
        for k in depot_keys
    ]

    return {"overall": overall, "flows": flow_rows, "resources": resource_rows, "depot": depot_rows}


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def export_reports(base_dir: Path, aggregate: Dict[str, Any], results: List[ReplicationResult]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = base_dir / f"simulation_outputs_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_csv(out_dir / "flow_summary.csv", aggregate["flows"])
    write_csv(out_dir / "resource_summary.csv", aggregate["resources"])
    write_csv(out_dir / "depot_summary.csv", aggregate["depot"])

    rep_rows = [
        {
            "rep_no": r.rep_no,
            "seed": r.seed,
            "sim_time_end": r.sim_time_end,
            "terminal_finished_products": r.terminal_finished_products,
            "stopped": r.stopped,
            "depot_remaining_total": sum(r.depot_remaining.values()),
        }
        for r in results
    ]
    write_csv(out_dir / "replication_summary.csv", rep_rows)

    lines = []
    o = aggregate["overall"]
    lines.append("PROFESSIONAL ARENA-LIKE SIMULATION REPORT")
    lines.append("=" * 52)
    lines.append(f"Replication count      : {o['replications']}")
    lines.append(f"Finished products avg  : {o['terminal_finished_avg']:.3f}")
    lines.append(f"Finished products stdev: {o['terminal_finished_stdev']:.3f}")
    lines.append(f"Finished products min  : {o['terminal_finished_min']}")
    lines.append(f"Finished products max  : {o['terminal_finished_max']}")
    lines.append(f"Average sim end time   : {o['avg_sim_time_end']:.3f}")
    lines.append("")
    lines.append("CSV files:")
    lines.append("- flow_summary.csv")
    lines.append("- resource_summary.csv")
    lines.append("- depot_summary.csv")
    lines.append("- replication_summary.csv")
    (out_dir / "summary_report.txt").write_text("\n".join(lines), encoding="utf-8")
    return out_dir


# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------


class ProfessionalArenaGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Professional Arena-like Multi-Flow Simulation")
        self.root.minsize(1150, 760)

        self.network = parse_network_text(DEFAULT_MULTI_FLOW_TEXT)
        self.flows = list(self.network.flows)
        self.zoom = DEFAULT_ZOOM
        self.play_speed = 1.0
        self.running = False
        self.stop_event = threading.Event()
        self.event_queue: queue.Queue = queue.Queue()
        self.tokens: Dict[Tuple[str, int], Dict[str, Any]] = {}
        self.block_boxes: Dict[Tuple[str, int], Tuple[float, float, float, float]] = {}
        self.block_centers: Dict[Tuple[str, int], Tuple[float, float]] = {}
        self.block_tokens: Dict[str, Dict[int, List[int]]] = {}
        self.last_export_dir: Optional[Path] = None

        self._build_ui()
        self._draw_blocks()
        self.root.after(30, self._poll_queue)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        controls = ttk.LabelFrame(main, text="Simülasyon Kontrolleri", padding=10)
        controls.pack(fill=tk.X)

        self.production_time_var = tk.StringVar(value=str(int(DEFAULT_PRODUCTION_TIME)))
        self.assembly_time_var = tk.StringVar(value=str(int(DEFAULT_ASSEMBLY_TIME)))
        self.reps_var = tk.StringVar(value=str(DEFAULT_REPLICATIONS))
        self.arrival_mean_var = tk.StringVar(value=str(DEFAULT_ARRIVAL_MEAN))
        self.seed_var = tk.StringVar(value=str(DEFAULT_SEED))
        self.start_zero_var = tk.BooleanVar(value=True)
        self.anim_var = tk.BooleanVar(value=True)

        labels = [
            ("Üretim süresi", self.production_time_var, 10),
            ("Montaj süresi", self.assembly_time_var, 10),
            ("Replikasyon", self.reps_var, 8),
            ("Geliş ort.", self.arrival_mean_var, 8),
            ("Seed", self.seed_var, 8),
        ]
        for col, (label, var, width) in enumerate(labels):
            ttk.Label(controls, text=label + ":").grid(row=0, column=col * 2, sticky="w", padx=(0, 4))
            ttk.Entry(controls, textvariable=var, width=width).grid(row=0, column=col * 2 + 1, sticky="w", padx=(0, 10))

        ttk.Checkbutton(controls, text="İlk ürün t=0", variable=self.start_zero_var).grid(row=0, column=10, padx=5)
        ttk.Checkbutton(controls, text="Animasyon", variable=self.anim_var).grid(row=0, column=11, padx=5)

        ttk.Label(controls, text="Hız:").grid(row=0, column=12, sticky="e")
        speed = tk.Scale(controls, from_=0.25, to=4.0, resolution=0.05, orient=tk.HORIZONTAL, length=105, command=self._speed_changed)
        speed.set(1.0)
        speed.grid(row=0, column=13, padx=5)

        self.start_btn = ttk.Button(controls, text="Başlat", command=self.start_simulation)
        self.start_btn.grid(row=0, column=14, padx=4)
        self.stop_btn = ttk.Button(controls, text="Durdur", command=self.stop_simulation, state="disabled")
        self.stop_btn.grid(row=0, column=15, padx=4)
        ttk.Button(controls, text="Zoom +", command=self.zoom_in).grid(row=0, column=16, padx=2)
        ttk.Button(controls, text="Zoom -", command=self.zoom_out).grid(row=0, column=17, padx=2)

        self.status_var = tk.StringVar(value="Hazır")
        ttk.Label(main, textvariable=self.status_var).pack(anchor="w", pady=(6, 4))

        paned = ttk.PanedWindow(main, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        definition_frame = ttk.LabelFrame(paned, text="Metinle Akış + Kaynak Tanımı", padding=8)
        paned.add(definition_frame, weight=1)

        definition_top = ttk.Frame(definition_frame)
        definition_top.pack(fill=tk.X)
        ttk.Label(
            definition_top,
            text=(
                "Format: [Kaynaklar], [Akış: ÜrünKodu], Create/Depo -> ilk proses, "
                "Proses: (min, mode, max) | Kaynak -> Sonraki proses, Scrap: 2.0"
            ),
        ).pack(side=tk.LEFT, anchor="w")
        ttk.Button(definition_top, text="Metni Uygula", command=self.update_network).pack(side=tk.RIGHT)

        self.process_entry = scrolledtext.ScrolledText(definition_frame, height=11, width=120, font=("Consolas", 9))
        self.process_entry.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.process_entry.insert(tk.END, DEFAULT_MULTI_FLOW_TEXT)

        canvas_frame = ttk.LabelFrame(paned, text="Arena-like Görsel Akış", padding=8)
        paned.add(canvas_frame, weight=2)
        self.canvas = tk.Canvas(canvas_frame, width=1320, height=340, bg="white", highlightthickness=1, highlightbackground="#cfcfcf")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        xscroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        yscroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        xscroll.grid(row=1, column=0, sticky="ew")
        yscroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        output_frame = ttk.LabelFrame(paned, text="Sonuçlar", padding=8)
        paned.add(output_frame, weight=1)
        self.output = scrolledtext.ScrolledText(output_frame, height=12, width=120, font=("Consolas", 9))
        self.output.pack(fill=tk.BOTH, expand=True)

    def _speed_changed(self, value: str) -> None:
        self.play_speed = max(0.01, float(value))

    def _sleep_with_stop(self, seconds: float) -> None:
        remaining = max(0.0, seconds)
        while remaining > 0 and not self.stop_event.is_set():
            step = min(0.05, remaining)
            time.sleep(step)
            remaining -= step

    def update_network(self) -> bool:
        if self.running:
            self.status_var.set("Simülasyon çalışırken akış metni değiştirilemez.")
            return False
        try:
            self.network = parse_network_text(self.process_entry.get("1.0", tk.END))
            self.flows = list(self.network.flows)
            self.tokens.clear()
            self._draw_blocks()
            self.status_var.set(f"Metin uygulandı: {len(self.flows)} akış, {len(self.network.resources)} kaynak.")
            return True
        except Exception as exc:
            self.status_var.set(f"Tanım hatası: {exc}")
            messagebox.showerror("Tanım hatası", str(exc))
            return False

    def _dims(self) -> Dict[str, int]:
        s = self.zoom
        return {
            "label_w": int(165 * s),
            "block_w": int(160 * s),
            "block_h": int(92 * s),
            "gap": int(14 * s),
            "row_gap": int(132 * s),
            "top": int(24 * s),
            "left": int(20 * s),
            "font_box": max(7, int(9 * s)),
            "font_flow": max(8, int(11 * s)),
            "font_count": max(8, int(10 * s)),
        }

    def zoom_in(self) -> None:
        if self.running:
            self.status_var.set("Zoom simülasyon çalışırken değiştirilemez.")
            return
        self.zoom = min(MAX_ZOOM, round(self.zoom + ZOOM_STEP, 2))
        self._draw_blocks()
        self.status_var.set(f"Zoom: %{int(self.zoom * 100)}")

    def zoom_out(self) -> None:
        if self.running:
            self.status_var.set("Zoom simülasyon çalışırken değiştirilemez.")
            return
        self.zoom = max(MIN_ZOOM, round(self.zoom - ZOOM_STEP, 2))
        self._draw_blocks()
        self.status_var.set(f"Zoom: %{int(self.zoom * 100)}")

    def _draw_blocks(self) -> None:
        self.canvas.delete("all")
        self.block_boxes.clear()
        self.block_centers.clear()
        self.block_tokens.clear()
        if not self.flows:
            return

        dims = self._dims()
        label_w = dims["label_w"]
        block_w = dims["block_w"]
        block_h = dims["block_h"]
        gap = dims["gap"]
        left = dims["left"]
        top = dims["top"]
        start_x = left + label_w + int(28 * self.zoom)

        max_nodes = max(len(f.visual_nodes) for f in self.flows)
        canvas_w = max(1320, start_x + max_nodes * (block_w + gap) + 80)
        canvas_h = max(360, top + len(self.flows) * dims["row_gap"] + 60)

        for row, flow in enumerate(self.flows):
            y1 = top + row * dims["row_gap"]
            y2 = y1 + block_h
            mid_y = (y1 + y2) / 2
            self.block_tokens[flow.name] = {}

            self.canvas.create_rectangle(left, y1, left + label_w, y2, fill="#eef4ff", outline="#c8d4e6")
            self.canvas.create_text(left + label_w / 2, mid_y, text=flow.name, font=("Segoe UI", dims["font_flow"], "bold"), justify="center", width=label_w - 8)

            nodes = flow.visual_nodes
            step_resource_map = {s.name: s.resources for s in flow.steps}
            for idx, name in enumerate(nodes):
                x1 = start_x + idx * (block_w + gap)
                x2 = x1 + block_w
                self.block_tokens[flow.name][idx] = []
                fill = "#ffffff"
                if name in ("Create", "Depo"):
                    fill = "#f7fbff"
                if name == "Scrap":
                    fill = "#fff7f2"
                if name == "Dispose":
                    fill = "#f5fff5"
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="#2f3b52", width=2, fill=fill)
                resources = step_resource_map.get(name, tuple())
                display = name
                if name == "Scrap":
                    display = f"Scrap\n%{flow.scrap_rate * 100:.1f}"
                elif resources:
                    display = f"{name}\nR: {', '.join(resources)}"
                elif name == "Depo":
                    display = "Depo\n(Store)"

                self.canvas.create_text((x1 + x2) / 2, y1 + int(30 * self.zoom), text=display, font=("Segoe UI", dims["font_box"], "bold"), justify="center", width=block_w - 8)
                self.canvas.create_text((x1 + x2) / 2, y2 - int(15 * self.zoom), text="0", tags=(f"count::{flow.name}::{idx}",), font=("Segoe UI", dims["font_count"]))
                self.block_boxes[(flow.name, idx)] = (x1, y1, x2, y2)
                self.block_centers[(flow.name, idx)] = ((x1 + x2) / 2, (y1 + y2) / 2)

            for idx in range(len(nodes) - 1):
                x1, yy1, x2, yy2 = self.block_boxes[(flow.name, idx)]
                nx1, ny1, nx2, ny2 = self.block_boxes[(flow.name, idx + 1)]
                self.canvas.create_line(x2, (yy1 + yy2) / 2, nx1, (ny1 + ny2) / 2, arrow=tk.LAST, width=max(1, int(2 * self.zoom)))

        self.canvas.configure(scrollregion=(0, 0, canvas_w, canvas_h))

    def _set_count(self, flow_name: str, block_idx: int) -> None:
        count = len(self.block_tokens.get(flow_name, {}).get(block_idx, []))
        self.canvas.itemconfigure(f"count::{flow_name}::{block_idx}", text=str(count))

    def _relayout_block(self, flow_name: str, block_idx: int) -> None:
        pids = self.block_tokens.get(flow_name, {}).get(block_idx, [])
        self._set_count(flow_name, block_idx)
        if not pids:
            return
        x1, y1, x2, y2 = self.block_boxes[(flow_name, block_idx)]
        cx = (x1 + x2) / 2
        top = y1 + max(20, int(48 * self.zoom))
        bottom = y2 - max(14, int(17 * self.zoom))
        r = max(7, int(11 * self.zoom))
        for i, pid in enumerate(pids):
            y = (top + bottom) / 2 if len(pids) == 1 else min(bottom, top + i * max(7, int(16 * self.zoom)))
            token = self.tokens.get((flow_name, pid))
            if token:
                self.canvas.coords(token["oval"], cx - r, y - r, cx + r, y + r)
                self.canvas.coords(token["text"], cx, y)

    def _add_token(self, flow_name: str, pid: int) -> None:
        block_idx = 0
        x, y = self.block_centers[(flow_name, block_idx)]
        r = max(7, int(11 * self.zoom))
        token = {
            "block": block_idx,
            "oval": self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="gold", outline="black"),
            "text": self.canvas.create_text(x, y, text=str(pid), font=("Segoe UI", max(7, int(8 * self.zoom)), "bold")),
        }
        self.tokens[(flow_name, pid)] = token
        self.block_tokens[flow_name][block_idx].append(pid)
        self._relayout_block(flow_name, block_idx)

    def _move_token(self, flow_name: str, pid: int, new_block: int) -> None:
        key = (flow_name, pid)
        token = self.tokens.get(key)
        if not token:
            return
        old_block = token["block"]
        if pid in self.block_tokens[flow_name].get(old_block, []):
            self.block_tokens[flow_name][old_block].remove(pid)
        self._relayout_block(flow_name, old_block)
        self.block_tokens[flow_name][new_block].append(pid)
        start = self.block_centers[(flow_name, old_block)]
        end = self.block_centers[(flow_name, new_block)]
        r = max(7, int(11 * self.zoom))
        steps = 10

        def animate(i: int = 0) -> None:
            if key not in self.tokens:
                return
            frac = i / steps
            x = start[0] + (end[0] - start[0]) * frac
            y = start[1] + (end[1] - start[1]) * frac
            self.canvas.coords(token["oval"], x - r, y - r, x + r, y + r)
            self.canvas.coords(token["text"], x, y)
            if i < steps:
                self.root.after(25, animate, i + 1)
            else:
                token["block"] = new_block
                self._relayout_block(flow_name, new_block)

        animate()

    def _dispose_token(self, flow_name: str, pid: int) -> None:
        key = (flow_name, pid)
        token = self.tokens.pop(key, None)
        if not token:
            return
        block = token["block"]
        if pid in self.block_tokens.get(flow_name, {}).get(block, []):
            self.block_tokens[flow_name][block].remove(pid)
        self.canvas.delete(token["oval"])
        self.canvas.delete(token["text"])
        self._relayout_block(flow_name, block)

    def _read_inputs(self) -> Tuple[float, float, int, float, int]:
        production_time = float(self.production_time_var.get())
        assembly_time = float(self.assembly_time_var.get())
        reps = max(1, int(self.reps_var.get()))
        arrival_mean = float(self.arrival_mean_var.get())
        seed = int(self.seed_var.get())
        if production_time <= 0 or assembly_time <= 0 or arrival_mean <= 0:
            raise ValueError("Süre ve geliş ortalaması 0'dan büyük olmalı.")
        if assembly_time < production_time:
            raise ValueError("Montaj süresi, üretim süresinden küçük olamaz.")
        return production_time, assembly_time, reps, arrival_mean, seed

    def start_simulation(self) -> None:
        if self.running:
            return
        if not self.update_network():
            return
        try:
            production_time, assembly_time, reps, arrival_mean, seed = self._read_inputs()
        except Exception as exc:
            messagebox.showerror("Giriş hatası", str(exc))
            return

        self.running = True
        self.stop_event.clear()
        self.tokens.clear()
        self._draw_blocks()
        self.output.delete("1.0", tk.END)
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_var.set("Simülasyon başladı...")

        worker = threading.Thread(
            target=self._run_worker,
            args=(production_time, assembly_time, reps, arrival_mean, seed, self.start_zero_var.get(), self.anim_var.get()),
            daemon=True,
        )
        worker.start()

    def stop_simulation(self) -> None:
        if not self.running:
            return
        self.stop_event.set()
        self.status_var.set("Simülasyon durduruluyor...")

    def _run_worker(self, production_time: float, assembly_time: float, reps: int, arrival_mean: float, seed: int, start_at_zero: bool, animate: bool) -> None:
        results: List[ReplicationResult] = []
        try:
            for rep in range(1, reps + 1):
                if self.stop_event.is_set():
                    break
                collect_log = animate and rep == 1
                self.event_queue.put({"kind": "status", "text": f"Replikasyon {rep}/{reps} çalışıyor..."})
                engine = SimulationEngine(
                    network=self.network,
                    production_time=production_time,
                    assembly_time=assembly_time,
                    arrival_mean=arrival_mean,
                    start_at_zero=start_at_zero,
                    seed=seed + rep - 1,
                )
                result = engine.run(rep_no=rep, stop_event=self.stop_event, collect_log=collect_log)
                results.append(result)

                if collect_log:
                    last_t = 0.0
                    for evt in result.event_log:
                        if self.stop_event.is_set():
                            break
                        dt = max(0.0, evt["time"] - last_t)
                        self._sleep_with_stop(dt * ANIM_SCALE / max(0.01, self.play_speed))
                        self.event_queue.put({"kind": "event", "event": evt})
                        last_t = evt["time"]

            if not results:
                self.event_queue.put({"kind": "finish", "error": "Simülasyon sonucu üretilemedi."})
                return

            aggregate = aggregate_results(results, self.network, horizon=assembly_time)
            export_dir = export_reports(Path.cwd(), aggregate, results)
            self.event_queue.put({"kind": "summary", "aggregate": aggregate, "results": results, "export_dir": str(export_dir)})
        except Exception as exc:
            self.event_queue.put({"kind": "finish", "error": str(exc)})

    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self.event_queue.get_nowait()
                kind = msg.get("kind")
                if kind == "status":
                    self.status_var.set(msg["text"])
                elif kind == "event":
                    evt = msg["event"]
                    if not self.anim_var.get():
                        continue
                    if evt["type"] in ("create", "spawn"):
                        self._add_token(evt["flow"], evt["pid"])
                    elif evt["type"] == "move":
                        self._move_token(evt["flow"], evt["pid"], evt["block"])
                    elif evt["type"] in ("dispose", "handoff"):
                        self._dispose_token(evt["flow"], evt["pid"])
                elif kind == "summary":
                    self._show_summary(msg["aggregate"], msg["results"], Path(msg["export_dir"]))
                    self._finish_ui("Simülasyon tamamlandı.")
                elif kind == "finish":
                    error = msg.get("error")
                    if error:
                        self._show_error(error)
                    self._finish_ui("Simülasyon durduruldu." if self.stop_event.is_set() else "Simülasyon tamamlandı.")
        except queue.Empty:
            pass
        self.root.after(30, self._poll_queue)

    def _finish_ui(self, status: str) -> None:
        self.running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_var.set(status)

    def _show_error(self, error: str) -> None:
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "HATA\n")
        self.output.insert(tk.END, "=" * 60 + "\n")
        self.output.insert(tk.END, error + "\n")
        messagebox.showerror("Simülasyon hatası", error)

    def _show_summary(self, aggregate: Dict[str, Any], results: List[ReplicationResult], export_dir: Path) -> None:
        self.last_export_dir = export_dir
        self.output.delete("1.0", tk.END)
        o = aggregate["overall"]
        self.output.insert(tk.END, "GENEL ÖZET\n")
        self.output.insert(tk.END, "=" * 80 + "\n")
        self.output.insert(tk.END, f"Replikasyon sayısı                 : {o['replications']}\n")
        self.output.insert(tk.END, f"Montajdan çıkan bitmiş ürün ort.   : {o['terminal_finished_avg']:.3f}\n")
        self.output.insert(tk.END, f"Standart sapma                     : {o['terminal_finished_stdev']:.3f}\n")
        self.output.insert(tk.END, f"Min / Max                          : {o['terminal_finished_min']} / {o['terminal_finished_max']}\n")
        self.output.insert(tk.END, f"Ortalama simülasyon bitiş zamanı   : {o['avg_sim_time_end']:.3f}\n")
        self.output.insert(tk.END, f"Rapor klasörü                      : {export_dir}\n\n")

        self.output.insert(tk.END, "AKIŞ BAZLI SONUÇLAR\n")
        self.output.insert(tk.END, "-" * 80 + "\n")
        for row in aggregate["flows"]:
            self.output.insert(tk.END, f"\n• {row['flow']} ({row['entry_kind']})\n")
            self.output.insert(tk.END, f"  Oluşturulan/Başlatılan ort. : {row['created_avg']:.2f}\n")
            self.output.insert(tk.END, f"  Depoya iyi parça ort.       : {row['good_to_depot_avg']:.2f}\n")
            self.output.insert(tk.END, f"  Fire ort.                   : {row['scrapped_avg']:.2f}\n")
            self.output.insert(tk.END, f"  Bitmiş ürün ort.            : {row['finished_products_avg']:.2f}\n")
            self.output.insert(tk.END, f"  Ortalama cycle time         : {row['avg_cycle_time_avg']:.2f} sn\n")
            self.output.insert(tk.END, f"  Ortalama queue time         : {row['avg_queue_time_avg']:.2f} sn\n")

        self.output.insert(tk.END, "\nKAYNAK KULLANIMI\n")
        self.output.insert(tk.END, "-" * 80 + "\n")
        for row in aggregate["resources"]:
            self.output.insert(
                tk.END,
                f"{row['resource']:<38} cap={row['capacity']:<3} util={row['utilization_avg_percent']:>6.2f}% "
                f"req={row['requests_avg']:>8.2f} avg_q={row['avg_queue_wait_avg']:>7.3f} sn\n",
            )

        if aggregate["depot"]:
            self.output.insert(tk.END, "\nDEPO KALANI\n")
            self.output.insert(tk.END, "-" * 80 + "\n")
            for row in aggregate["depot"]:
                self.output.insert(tk.END, f"{row['source_flow']:<20} remaining_avg={row['remaining_avg']:.2f}\n")

        self.output.insert(tk.END, "\nNot: Kaynak akışların depoya gönderdiği parçalar nihai ürün sayısına dahil edilmez. Nihai ürün sayısı montaj/depo akışının Dispose çıktısıdır.\n")


def main() -> None:
    root = tk.Tk()
    try:
        root.state("zoomed")
    except Exception:
        pass
    ProfessionalArenaGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
