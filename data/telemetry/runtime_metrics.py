#!/usr/bin/env python3
"""
runtime_metrics.py — Operational Validation metrics collector (stdlib-only)

Records key runtime events to data/telemetry/runtime_metrics.jsonl for
the 3-7 day Operational Validation phase.

Events tracked:
  - watchdog_check:    watchdog status (ok/critical), checks detail
  - blocked_state:     blocked state set/cleared, reason
  - mvs_activation:    MVS fallback activated (config missing)
  - heartbeat_write:   heartbeat written, age since last write
  - fuse_trip:         fuse tripped, fuse_type, reason
  - contract_test:     Architecture Contract result (pass/fail)
  - recovery_event:    system recovered from blocked state

Usage:
    from data.telemetry.runtime_metrics import MetricsCollector

    mc = MetricsCollector()
    mc.record("watchdog_check", status="ok", detail={"age_s": 42})
    mc.record("blocked_state", reason="recursion_limit", action="set")

    # Summary
    mc.summary()
"""

from datetime import datetime, timezone
from pathlib import Path
import json

TELEMETRY_FILE = Path(__file__).resolve().parent / "runtime_metrics.jsonl"


class MetricsCollector:
    """Metrics collector — append-only JSONL, no retention limits."""

    def __init__(self, path: Path | None = None):
        self._path = path or TELEMETRY_FILE
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event_type: str, **fields) -> dict:
        """Record a metrics event. Fields are merged into the event dict."""
        event = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event": event_type,
        }
        event.update(fields)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def summary(self) -> dict:
        """Quick summary of metrics file."""
        counts = {}
        if not self._path.exists():
            return {"total": 0, "events": {}}
        try:
            lines = self._path.read_text(encoding="utf-8").strip().split("\n")
            total = 0
            for line in lines:
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    etype = event.get("event", "unknown")
                    counts[etype] = counts.get(etype, 0) + 1
                    total += 1
                except json.JSONDecodeError:
                    continue
            return {"total": total, "events": counts, "path": str(self._path)}
        except OSError:
            return {"total": 0, "events": {}}


_mc: MetricsCollector | None = None


def get_collector() -> MetricsCollector:
    global _mc
    if _mc is None:
        _mc = MetricsCollector()
    return _mc


def record(event_type: str, **fields) -> dict:
    return get_collector().record(event_type, **fields)


if __name__ == "__main__":
    import sys
    mc = get_collector()
    if "--summary" in sys.argv:
        s = mc.summary()
        print(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        mc.record("manual_test", source="cli")
        print(json.dumps(mc.record("ping", status="ok"), ensure_ascii=False))
