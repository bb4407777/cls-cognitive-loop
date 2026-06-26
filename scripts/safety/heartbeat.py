#!/usr/bin/env python3
"""
heartbeat.py — 心跳写入/读取 (stdlib-only, 零外部依赖)

Usage:
    from scripts.safety.heartbeat import Heartbeat

    hb = Heartbeat()
    hb.write(phase="task_execution", step=42, safety="ok", progress="running")
    data = hb.read()

Minimal+ format — < 1 KB, append-free atomic overwrite.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import tempfile
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HEARTBEAT_PATH = PROJECT_ROOT / "data" / "state" / "heartbeat.json"


class Heartbeat:
    """心跳读写接口"""

    def __init__(self, path: Path | None = None):
        self._path = path or HEARTBEAT_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        phase: str = "unknown",
        step: int = 0,
        safety: str = "ok",
        progress: str = "running",
        block_reason: str | None = None,
        fuse_profile: str = "full",
    ) -> dict:
        """写入心跳 (原子写入: tmp → rename)"""
        data = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "phase": phase,
            "step_counter": step,
            "safety_status": safety,
            "progress_status": progress,
            "block_reason": block_reason,
            "fuse_profile": fuse_profile,
        }
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.rename(self._path)
        return data

    def read(self) -> dict:
        """读取心跳，文件不存在时返回空字典"""
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
        return {}

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """心跳是否过期"""
        data = self.read()
        ts = data.get("timestamp", "")
        if not ts:
            return True
        try:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            return age > max_age_seconds
        except ValueError:
            return True

    @property
    def path(self) -> Path:
        return self._path


# 模块级便利函数
_hb: Heartbeat | None = None


def get_heartbeat() -> Heartbeat:
    global _hb
    if _hb is None:
        _hb = Heartbeat()
    return _hb


def write_heartbeat(
    phase: str = "unknown",
    step: int = 0,
    safety: str = "ok",
    progress: str = "running",
    block_reason: str | None = None,
    fuse_profile: str = "full",
) -> dict:
    return get_heartbeat().write(
        phase=phase, step=step, safety=safety,
        progress=progress, block_reason=block_reason,
        fuse_profile=fuse_profile,
    )


def read_heartbeat() -> dict:
    return get_heartbeat().read()


if __name__ == "__main__":
    import sys
    hb = get_heartbeat()
    if "--read" in sys.argv:
        data = hb.read()
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif "--stale" in sys.argv:
        seconds = int(sys.argv[sys.argv.index("--stale") + 1]) if "--stale" in sys.argv and len(sys.argv) > sys.argv.index("--stale") + 1 else 300
        print("stale" if hb.is_stale(seconds) else "fresh")
    else:
        data = hb.write()
        print(json.dumps(data, ensure_ascii=False, indent=2))
