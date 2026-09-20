"""Read-only public APM Elizabeth terminal-status observation.

Fetches three public, unauthenticated pages and extracts only what they
explicitly state: row-closure text, gate-page presence indicators with any
explicit status sentence, and the latest dated alert section. No login, no
account portals (TERMPoint, EIR, PortTruckPass), no credential, permit, or
appointment lookups, no writes anywhere.

A terminal that looks open NEVER equals dispatch or entry clearance; the
observation is current operating context only. Any fetch or parse failure
returns status ``unavailable`` so the assessment stays explicitly
unresolved. Row-closure text carries no page date, so it is current only as
of ``retrieved_at`` and must not be reused across days (``freshness_hours``).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import re

EXTRACTOR_VERSION = "terminal-status-extractor-v1"
SCHEMA_VERSION = "terminal-status-observation-v1"
TERMINAL_ID = "facility_apm_elizabeth"
TIMEOUT_SECONDS = 10
FRESHNESS_HOURS = 24
MAX_TEXT_CHARS = 2000
USER_AGENT = "drayage-knowledge-graph-prototype/0.1 (+read-only terminal-status check)"

ROW_CLOSURES_URL = "https://www2.apmterminals.com/en/port-elizabeth/practical-information/row-closures"
GATE_INFO_URL = "https://www2.apmterminals.com/en/port-elizabeth/e-tools/truck-turn-times"
STATUS_UPDATE_URL = ("https://www.apmterminals.com/en/port-elizabeth/practical-information/"
                     "news-and-alerts/2026/Port-Status-Update")

SOURCES = (
    ("row_closures", ROW_CLOSURES_URL),
    ("gate_info", GATE_INFO_URL),
    ("status_update", STATUS_UPDATE_URL),
)

STATUS_LIMITS = [
    "Current terminal operating context only; it is not dispatch, entry, permit, or route clearance.",
    "Row-closure text carries no page date and is current only as of retrieved_at; do not reuse it across days.",
    "An absent status sentence means not stated, never open. Camera and turn-time widgets are not an open finding.",
    "Alert excerpts are the latest dated section only; earlier sections on the same page may be superseded.",
]

# Explicit status sentences only; widget presence is reported separately and
# never interpreted here. Line-based so abbreviations like "Mon." cannot
# truncate the extracted notice.
_STATUS_MARKERS = (
    "will be closed",
    "returning to normal gate hours",
    "normal gate hours",
    "currently open",
    "currently closed",
    "is closed",
    "are closed",
)
_CLOSED_AREAS = re.compile(r"([^.\n]*Closed areas\.?)")
_PAGE_DATE = re.compile(r"\b(\d{1,2} \w+ \d{4})\b")
_NOTICE_HEADING = re.compile(r"(Short-Term Vessel Schedule [\d/]+|Gate Advisory[^\n]*)")


def _line_with(text: str, markers) -> str | None:
    lowered = [(line, line.lower()) for line in text.split("\n")]
    if isinstance(markers, str):
        markers = (markers,)
    for marker in markers:
        for line, low in lowered:
            if marker in low and line.strip():
                return line.strip()
    return None


class _Text(HTMLParser):
    """Visible text in document order; scripts and styles skipped."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        elif tag in ("p", "div", "section", "article", "h1", "h2", "h3", "h4", "li", "br"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip() + " ")

    def text(self) -> str:
        return re.sub(r"[ \t]+", " ", "".join(self.parts))


def _clip(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value if len(value) <= MAX_TEXT_CHARS else value[:MAX_TEXT_CHARS] + " [truncated]"


def _default_get(url: str, timeout: int) -> bytes:
    try:
        import truststore
        truststore.inject_into_ssl()  # OS trust roots, as the Neo4j connector does.
    except ImportError:
        pass
    from urllib.request import Request, urlopen
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError(f"Unexpected HTTP status: {response.status}")
        return response.read()


def unavailable(reason: str, now: datetime | None = None) -> dict:
    moment = now or datetime.now(timezone.utc)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "unavailable",
        "unavailable_reason": reason,
        "terminal_id": TERMINAL_ID,
        "retrieved_at": moment.isoformat(),
        "sources": [],
        "row_closures_text": None,
        "row_closures_effective": None,
        "gate_status_text": None,
        "gate_indicators": {"live_cameras": False, "turn_times": False, "happiness_index": False},
        "latest_notice_heading": None,
        "latest_notice_date": None,
        "closure_notice_text": None,
        "extractor_version": EXTRACTOR_VERSION,
        "freshness_hours": FRESHNESS_HOURS,
        "operational_use": False,
        "limits": list(STATUS_LIMITS),
    }


def parse_pages(pages: dict[str, bytes]) -> dict:
    """Build the observation from already-fetched page bytes (no network)."""
    texts: dict[str, str] = {}
    for key, raw in pages.items():
        try:
            parser = _Text()
            parser.feed(raw.decode("utf-8", errors="replace"))
            texts[key] = parser.text()
        except Exception:
            texts[key] = ""
    rows, gate, alert = (texts.get("row_closures", ""), texts.get("gate_info", ""),
                         texts.get("status_update", ""))
    if "Closed areas" not in rows or "Truck Turn Times" not in gate:
        raise ValueError("Required status markers missing; page layout may have changed")
    notice_heading = _NOTICE_HEADING.search(alert)
    if notice_heading is None and ("Vessel Schedule" not in alert and "Gate Advisory" not in alert):
        raise ValueError("Required status markers missing; page layout may have changed")
    closed = _CLOSED_AREAS.search(rows)
    status_sentence = _line_with(gate, _STATUS_MARKERS)
    closure = _line_with(alert, "will be closed")
    page_date = _PAGE_DATE.search(alert)
    return {
        "row_closures_text": _clip(closed.group(1) if closed else None),
        "row_closures_effective": None,
        "gate_status_text": _clip(status_sentence),
        "gate_indicators": {
            "live_cameras": "Live gate cameras" in gate,
            "turn_times": "Truck Turn Times" in gate,
            "happiness_index": "Happiness Index" in gate,
        },
        "latest_notice_heading": _clip(notice_heading.group(1) if notice_heading else None),
        "latest_notice_date": page_date.group(1) if page_date else None,
        "closure_notice_text": _clip(closure),
    }


def fetch(get=None, now: datetime | None = None) -> dict:
    """Fetch the public surface and return the observation; never raises."""
    moment = now or datetime.now(timezone.utc)
    reader = get or _default_get
    try:
        pages: dict[str, bytes] = {}
        sources = []
        for key, url in SOURCES:
            raw = reader(url, TIMEOUT_SECONDS)
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            if not isinstance(raw, (bytes, bytearray)) or not raw:
                raise ValueError(f"Empty response: {url}")
            raw = bytes(raw)
            pages[key] = raw
            sources.append({
                "page": key,
                "url": url,
                "retrieved_at": moment.isoformat(),
                "content_sha256": hashlib.sha256(raw).hexdigest(),
                "extractor": EXTRACTOR_VERSION,
            })
    except Exception as exc:
        return unavailable(f"fetch_error:{type(exc).__name__}", moment)
    try:
        parsed = parse_pages(pages)
    except Exception as exc:
        return unavailable(f"unexpected_content:{type(exc).__name__}", moment)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "available",
        "unavailable_reason": None,
        "terminal_id": TERMINAL_ID,
        "retrieved_at": moment.isoformat(),
        **parsed,
        "row_closures_effective": None,
        "extractor_version": EXTRACTOR_VERSION,
        "freshness_hours": FRESHNESS_HOURS,
        "operational_use": False,
        "limits": list(STATUS_LIMITS),
        "sources": sources,
    }
