# ADR-0001: Safety Recovery Plan

## Metadata

- **Status:** ACCEPTED
- **Date:** 2026-06-27
- **Supersedes:** None
- **Session:** ILCP 2k9m8a4r (Rounds 1-3)
- **Author:** External architecture review (multi-LLM panel)
- **This document is frozen. Changes require a new ADR.**

---

## Context

The CLS (Cognitive Loop System) underwent a major restructuring (commit `8f59c74`). A three-round architecture review (Rounds 1-3 via ILCP Lite protocol) identified that the system suffers from a **Silent Safety Failure**: the fuse board's CONFIG_PATH points to a nonexistent directory, causing all 10 safety fuses to silently disable themselves via fail-open fallback. This led to a recursion spiral that froze the cognitive loop on 2026-06-24.

The review also identified **Documentation Driven Hallucination**: the architecture documents (~2300 lines across ARCHITECTURE.md, COGNITIVE_CYCLE.md, WHITE_PAPER.md) describe ~30+ components, but only 8 Python files (3880 lines) actually exist. The missing `scripts/wheels/` directory and 13+ referenced modules were never implemented.

The review panel's final judgment: **Prototype in adolescence** — production aspirations growing faster than governance, with the cognitive engine (qwen_gate) collapsed while the safety kernel (fuse_board) survived.

---

## Round Summaries

| Round | Theme | Key Outputs |
|-------|-------|-------------|
| R1 | Diagnosis | Silent Safety Failure identified. Documentation Drift diagnosed. 6-step cycle is conceptually sound but overbuilt (14+ substeps/step). Minimum Viable Safety Profile (MVS) proposed. |
| R2 | Treatment Plan | 10-step fix sequence. 6 engineering decisions resolved: stub vs delete (differentiated), watchdog subprocess, Architecture Contract Test (two-layer), identity delay, pre-depth check, no silent degradation principle. |
| R3 | Spec Lock | Option A for stub location. MVS (3 fuses) ≠ MVO (heartbeat + audit). Minimal+ heartbeat format. Readiness score: 4.5/5. No Round 4 needed. |

---

## Final Locked Specification

### Architecture Layers

```
Operational Core (rebuild order):     fuse_board — Trusted Computing Base
Cognitive Core (system value):        qwen_gate — collapsed, preserve via stubs
```

### Minimum Viable Safety (MVS)

Activated when config is missing or corrupt:

```
RECURSION_LIMIT     max_depth=5
WRITE_PROTECT       paths=[PROJECT_ROOT]
SELF_MODIFICATION   fuse_board code is in its own WRITE_PROTECT list
```

AUDIT_GATE is **excluded** from MVS. Observability ≠ Safety.

### Minimum Viable Observability (MVO)

Parallel to MVS but distinct:

```
heartbeat.json      Minimal+ format (see below)
audit_gate.py       existing 92-line file
```

### Watchdog

- **Process model:** Subprocess (not thread — in-process watchdog is an observer, not a watchdog)
- **Phase 1 behavior:** Detect only (write CRITICAL marker, do NOT auto-restart)
- **Phase 2 (future):** Detect + terminate (optional auto-restart with crash-loop protection)

### Heartbeat Format (Minimal+)

```json
{
  "timestamp": "2026-06-27T10:00:00Z",
  "phase": "situational_awareness",
  "step_counter": 182,
  "safety_status": "degraded",
  "fuse_profile": "mvs",
  "last_event": "RECURSION_BLOCK"
}
```

**Constraints:**
- Must be < 1 KB
- Write frequency < 1/sec
- Atomic update via tmp → rename
- **Append-free.** Overwrite only.

### Ghost References Treatment

| Source | Action |
|--------|--------|
| Documentation references to nonexistent components | **Delete** |
| Hard imports (`from scripts.wheels.api_pipeline import call`) | **Stub** via Option A (preserve import path) |

**Option A:** Create `scripts/wheels/api_pipeline.py` with:
```python
def call(*args, **kwargs):
    raise NotImplementedError("api_pipeline was not included in standalone extraction")
```

### Architecture Contract Test

**Two-layer design:**

| Layer | Method | When | Risk |
|-------|--------|------|------|
| Shallow (default) | String-scan docs + imports for file existence | Pre-commit hook, CI | Zero side effects |
| Deep (optional) | `importlib.util.find_spec()` — verifies resolution without executing module | CI nightly | No init-time side effects |

**DO NOT** use `import module` — risk of init-time side effects in current repo state.

### Identity-Sensitive Configs (deferred until observability restored)

| Config | Research default | Product default |
|--------|-----------------|-----------------|
| fail_open_policy | crash → continue() | crash → raise() |
| exploration_policy | epsilon=0.10 | epsilon=0.0 |
| persistence_guarantee | best-effort | at-least-once |
| restart_policy | manual | automatic |

These are the **only** configs that depend on identity decision. Everything else is a universal invariant.

### No Silent Degradation (Mandatory Invariant)

Any safety component that is:
- `disabled` (config missing)
- `missing` (file not found)
- `fallback` (MVS activated)
- `bypass` (exception caught)

Must produce **ALL** of:
1. CRITICAL-level log entry
2. State marker in heartbeat.json (`safety_status: "degraded"`)
3. (Optional) non-zero exit code for offline validation

---

## 10-Step Fix Sequence

| Priority | Step | Description | PR |
|----------|------|-------------|-----|
| **P0** | 0 | Freeze repo (no new features until safety restored) | Governance |
| **P0** | 1 | Fix CONFIG_PATH → `data/safety-configs/fuses_config.json` | PR #1 |
| **P0** | 2 | Enable MVS (3 fuses) as fallback when config not found | PR #1 |
| **P0** | 3 | Investigate recursion enforcement failure (grep for ignored returns, swallowed exceptions, retry loops) | PR #1 |
| **P1** | 4 | Add heartbeat.json + watchdog subprocess (detect only, no auto-restart) | PR #2 |
| **P1** | 5 | Repair qwen_gate import chain with stubs (Option A) | PR #3 |
| **P2** | 6 | Rewrite ARCHITECTURE.md (Implement / Planned / Research split) | PR #3 |
| **P2** | 7 | Delete ghost references from documentation only | PR #3 |
| **P2** | 8 | Add Architecture Contract Test (two-layer, pre-commit hook) | PR #3 |
| **P3** | 9 | Decide product/research identity (after system is observable) | Future |
| **P4** | 10 | Only then discuss rebuilding cognition | Future |

### PR #1 (Atomic — must ship together)

Steps 1 + 2 + 3 as a single PR because:
- Fixing CONFIG_PATH without MVS means the system re-enters recursion immediately
- Investigating enforcement without fixing config means the investigation runs on a broken system

### PR #1 Acceptance Criteria

- [ ] A. `fuse_board` successfully loads config from `data/safety-configs/fuses_config.json`
- [ ] B. MVS fallback test passes (simulate missing config → 3 fuses active)
- [ ] C. Artificially construct depth=6 → system **actually stops execution** (not just logs RECURSION BLOCK)
- [ ] D. Regression test added for recursion enforcement

---

## Exit Criteria (Safety Recovery Mode)

CLS leaves Safety Recovery Mode when **ALL** of the following are true:

1. Safety config loads correctly at startup
2. Recursion enforcement is verified (depth=6 → execution terminates)
3. Heartbeat + watchdog operational and observable
4. Architecture Contract Test passes (no ghost references)
5. No Silent Degradation invariant is enforced (tested)

---

## Out of Scope (Not to Be Discussed During Safety Recovery)

The following are explicitly excluded from the safety recovery phase. They will be revisited after Exit Criteria are met:

- Rebuilding or extending qwen_gate's cognitive capabilities
- Implementing the missing wheels/ components (other than the api_pipeline stub)
- Adding epsilon-greedy exploration or path mutation
- Implementing symbolic dynamics, anti-atrophy, cross-window awareness
- Optimizing cognitive cycle performance or reducing substep overhead
- Any new feature not directly related to safety restoration

---

## Key Decisions Log

| ID | Decision | Rationale |
|----|----------|-----------|
| D-001 | Stub hard imports (Option A), delete dead docs | Preserves dependency graph; avoids import boundary pollution (rejected: inline try/except in qwen_gate) |
| D-002 | MVS = 3 fuses only; AUDIT excluded | MVS prevents self-destruction; observability is separate concern (MVO) |
| D-003 | Watchdog = subprocess, not thread | In-process watchdog dies with main process (shared fate); subprocess survives |
| D-004 | Heartbeat = Minimal+ format (<1KB, <1/sec) | Extended format creates mini observability platform → monitoring becomes failure source |
| D-005 | Identity decision deferred | Safety fixes are universal invariants; identity only affects 4 specific configs |
| D-006 | Fail-open NOT global default | Safety fuses should be fail-closed; capability fuses may be fail-open |
| D-007 | Architecture Contract = two-layer | Shallow (string scan, zero side effects) + deep (find_spec, no module execution) |
| D-008 | PR #1 = atomic (steps 1+2+3) | Fixing config without MVS and enforcement fix creates incomplete safety |

---

## Lessons Learned

### LL-001: Detection ≠ Enforcement Was Wrong

**R2 hypothesis:** The 5+ consecutive RECURSION BLOCK events in hook_audit.jsonl were caused by the hook detecting the condition but returning an ignored value (Detection ≠ Enforcement).

**R3 finding:** Enforcement was working correctly. The PreToolUse hook executed `exit 0` with a deny verdict on every block. The real problem was that the **blocked state was not observable by the caller** — the depth counter only advanced on PASS, so the next tool call read the same depth and hit the same block, creating an infinite retry loop.

**Why this matters:**
- The system had Prevention (✅ hook blocks at depth > 5)
- But lacked Progress Semantics (❌ how to exit the blocked state)
- This is a **Recovery Failure / Liveness Failure**, not a Safety Failure

### LL-002: No Silent Terminal State

Derived principle from LL-001: any condition that permanently stops execution must:
1. Persist to a terminal state file (`blocked_state.json`)
2. Block retries at the hook level (check before allowing any operation)
3. Return a clear, actionable message to the caller

Implemented in PR #2 via `scripts/safety/blocked_state.py` + hook v2.

### LL-003: Assumptions Must Be Grounded in Code, Not Reasoning

The R2 panel assigned 60% probability to "ignored return value" without reading the actual hook code. The hook (`PreToolUse`) was in `.claude/hooks/` — a path covered by the repo's documented structure. A 5-minute file read would have disproved the hypothesis before Round 3.

**Process improvement:** Before formulating hypotheses about a system's behavior, read the enforcement code first. Especially when it's a shell script — shells do not silently ignore `exit 0`.
