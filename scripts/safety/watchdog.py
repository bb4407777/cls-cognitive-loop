#!/usr/bin/env python3
"""
watchdog.py — 看门狗子进程 (stdlib-only, 零外部依赖)

职责:
  检测 progress 死亡（而非 safety 死亡）。
  不阻断，只记录+报告。

运行模式:
  Phase 1 (当前): detect only — 发现异常写 CRITICAL marker，不重启
  Phase 2 (未来): detect + terminate (可选)

Usage:
    python scripts/safety/watchdog.py                    # 运行一次检查
    python scripts/safety/watchdog.py --daemon           # 持续监控
    python scripts/safety/watchdog.py --check            # 单次检查，返回状态码
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HEARTBEAT_PATH = PROJECT_ROOT / "data" / "state" / "heartbeat.json"
BLOCKED_STATE_PATH = PROJECT_ROOT / "data" / "state" / "blocked_state.json"
CRITICAL_MARKER_PATH = PROJECT_ROOT / "data" / "state" / "watchdog_critical.json"
HOOK_AUDIT_PATH = PROJECT_ROOT / "data" / "state" / "hook_audit.jsonl"

# 阈值常量
HEARTBEAT_MAX_AGE_SECONDS = 300  # 心跳超过5分钟无更新 → 判定为 stale
MAX_CONSECUTIVE_BLOCKS = 10     # 连续 block 超过 10 次 → 判定为 retry storm
WATCHDOG_INTERVAL_SECONDS = 60   # 守护进程检查间隔


def read_json(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def count_consecutive_blocks(max_age_hours: int = 1) -> int:
    """读取 hook_audit.jsonl，统计最近 max_age_hours 小时内连续 BLOCK 次数"""
    try:
        if not HOOK_AUDIT_PATH.exists():
            return 0
        lines = HOOK_AUDIT_PATH.read_text(encoding="utf-8").strip().split("\n")
        if not lines or lines == [""]:
            return 0
        now = datetime.now(timezone.utc)
        count = 0
        for line in reversed(lines):
            try:
                entry = json.loads(line)
                ts = entry.get("ts", "")
                if ts:
                    try:
                        entry_time = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                        age_hours = (now - entry_time).total_seconds() / 3600
                        if age_hours > max_age_hours:
                            break  # 遇到超过时间窗口的条目停止
                    except ValueError:
                        continue
                if entry.get("verdict") == "BLOCK":
                    count += 1
                else:
                    break  # 遇到非 block 条目停止
            except json.JSONDecodeError:
                continue
        return count
    except OSError:
        return 0


def check() -> dict:
    """运行一次 watchdog 检查，返回诊断结果"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = {
        "timestamp": now,
        "status": "ok",
        "checks": {},
    }

    # Check 1: Blocked state
    blocked = read_json(BLOCKED_STATE_PATH)
    if blocked.get("status") == "blocked":
        result["checks"]["blocked_state"] = {
            "status": "CRITICAL",
            "reason": blocked.get("reason", "unknown"),
            "detail": f"System in blocked state since {blocked.get('timestamp', 'unknown')}",
        }
        result["status"] = "critical"

    # Check 2: Heartbeat staleness
    heartbeat = read_json(HEARTBEAT_PATH)
    ts = heartbeat.get("timestamp", "")
    if ts:
        try:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            if age > HEARTBEAT_MAX_AGE_SECONDS:
                result["checks"]["heartbeat_stale"] = {
                    "status": "CRITICAL",
                    "reason": "heartbeat_stale",
                    "detail": f"Age: {age:.0f}s > {HEARTBEAT_MAX_AGE_SECONDS}s threshold",
                }
                result["status"] = "critical"
            else:
                result["checks"]["heartbeat"] = {
                    "status": "ok",
                    "detail": f"Age: {age:.0f}s",
                }
        except ValueError:
            result["checks"]["heartbeat"] = {"status": "unknown", "detail": "parse error"}

    # Check 3: Progress status
    progress = heartbeat.get("progress_status", "")
    if progress == "blocked":
        result["checks"]["progress"] = {
            "status": "CRITICAL",
            "reason": heartbeat.get("block_reason", "unknown"),
            "detail": "System explicitly reports blocked progress",
        }
        result["status"] = "critical"

    # Check 4: Retry storm detection
    consecutive_blocks = count_consecutive_blocks()
    if consecutive_blocks >= MAX_CONSECUTIVE_BLOCKS:
        result["checks"]["retry_storm"] = {
            "status": "CRITICAL",
            "reason": "retry_storm",
            "detail": f"{consecutive_blocks} consecutive blocks detected",
        }
        result["status"] = "critical"
    elif consecutive_blocks > 0:
        result["checks"]["retry_storm"] = {
            "status": "warning",
            "detail": f"{consecutive_blocks} consecutive blocks (threshold: {MAX_CONSECUTIVE_BLOCKS})",
        }

    # Write master status
    result["overall"] = result["status"]

    # If critical, write CRITICAL marker
    if result["status"] == "critical":
        CRITICAL_MARKER_PATH.parent.mkdir(parents=True, exist_ok=True)
        CRITICAL_MARKER_PATH.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        # Remove stale marker if exists
        if CRITICAL_MARKER_PATH.exists():
            CRITICAL_MARKER_PATH.unlink()

    return result


def daemon_loop() -> None:
    """守护进程模式: 持续监控"""
    print(f"[watchdog] daemon started (interval={WATCHDOG_INTERVAL_SECONDS}s)")
    print(f"[watchdog] heartbeat: {HEARTBEAT_PATH}")
    print(f"[watchdog] blocked_state: {BLOCKED_STATE_PATH}")
    print(f"[watchdog] PID: {PROJECT_ROOT}/data/state/watchdog.pid")
    # Write PID file
    pid_path = PROJECT_ROOT / "data" / "state" / "watchdog.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(12345), encoding="utf-8")

    critical_count = 0
    while True:
        try:
            result = check()
            status = result["status"]
            if status == "critical":
                critical_count += 1
                reasons = [c.get("reason", "?") for c in result["checks"].values()
                          if c.get("status") == "CRITICAL"]
                print(f"[watchdog] CRITICAL [{critical_count}] {' | '.join(reasons)}")
                print(f"           marker written to {CRITICAL_MARKER_PATH}")
            else:
                critical_count = 0
                print(f"[watchdog] OK  (heartbeat age: {result.get('checks', {}).get('heartbeat', {}).get('detail', '?')})")

            time.sleep(WATCHDOG_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n[watchdog] shutting down")
            break
        except Exception as e:
            print(f"[watchdog] ERROR: {e}")
            time.sleep(WATCHDOG_INTERVAL_SECONDS)


def main():
    if "--daemon" in sys.argv:
        daemon_loop()
    elif "--check" in sys.argv:
        result = check()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["status"] == "ok" else 1)
    else:
        result = check()
        status = result["status"]
        if status == "critical":
            print(f"[watchdog] STATUS: {status.upper()}")
            for name, c in result["checks"].items():
                cs = c.get("status", "?")
                detail = c.get("detail", c.get("reason", ""))
                print(f"  [{cs}] {name}: {detail}")
            sys.exit(1)
        else:
            print(f"[watchdog] STATUS: OK")
            sys.exit(0)


if __name__ == "__main__":
    main()
