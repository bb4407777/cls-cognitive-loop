#!/usr/bin/env python3
"""
blocked_state.py — 终态持久化 (stdlib-only, 零外部依赖)

写入 "No Silent Terminal State" 原则：
  任何永久阻止执行的状态必须：
  1) 持久化为 blocked_state.json
  2) 阻止自动重试
  3) 返回可解释信号

Usage:
    from scripts.safety.blocked_state import BlockedState

    bs = BlockedState()
    bs.set_blocked("recursion_limit", depth=6, max_depth=5)
    data = bs.read()     # → {"status": "blocked", ...}
    bs.clear()           # 人工重置

    if bs.is_blocked():
        print("系统已锁定")
        sys.exit(0)
"""

from datetime import datetime, timezone
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BLOCKED_STATE_PATH = PROJECT_ROOT / "data" / "state" / "blocked_state.json"


class BlockedState:
    """终态读写接口"""

    def __init__(self, path: Path | None = None):
        self._path = path or BLOCKED_STATE_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def set_blocked(
        self,
        reason: str,
        recoverable: bool = False,
        details: dict | None = None,
    ) -> dict:
        """写入阻止状态"""
        data = {
            "status": "blocked",
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "recoverable": recoverable,
            "details": details or {},
        }
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def read(self) -> dict:
        """读取阻止状态"""
        try:
            if self._path.exists():
                return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
        return {"status": "running"}

    def is_blocked(self) -> bool:
        """系统是否处于阻止状态"""
        data = self.read()
        return data.get("status") == "blocked"

    def is_blocked_by(self, reason: str) -> bool:
        """是否被指定的原因阻止"""
        data = self.read()
        return data.get("status") == "blocked" and data.get("reason") == reason

    def clear(self) -> dict:
        """清除阻止状态 (人工操作)"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        data = {"status": "running", "cleared_at": now}
        self._path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    @property
    def path(self) -> Path:
        return self._path


# 模块级便利函数
_bs: BlockedState | None = None


def get_blocked_state() -> BlockedState:
    global _bs
    if _bs is None:
        _bs = BlockedState()
    return _bs


def is_blocked() -> bool:
    return get_blocked_state().is_blocked()


def set_blocked(reason: str, recoverable: bool = False, details: dict | None = None) -> dict:
    return get_blocked_state().set_blocked(reason, recoverable, details)


def clear_blocked() -> dict:
    return get_blocked_state().clear()


if __name__ == "__main__":
    import sys
    bs = get_blocked_state()
    if "--clear" in sys.argv:
        data = bs.clear()
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif "--status" in sys.argv:
        data = bs.read()
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        if bs.is_blocked():
            print(f"BLOCKED: {bs.read()['reason']}")
        else:
            print("RUNNING")
