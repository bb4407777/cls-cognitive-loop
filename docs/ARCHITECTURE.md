# CLS Cognitive Loop — System Architecture

**Project**: CLS (Cognitive Loop System)
**Document version**: 3.0 (reconciled with codebase — see ADR-0001)
**Last reconciled**: 2026-06-27
**Note on truth**: This document describes what exists on disk. Components marked [Planned] or [Research] do not exist yet — see ROADMAP.md for timeline.

---

## 1. System Overview

The CLS Cognitive Loop is a structured, file-anchored supervision layer that wraps around a Claude Code LLM session. It does not replace the model's reasoning; it constrains and verifies the model's output through external, auditable mechanisms.

### Why a loop instead of one-shot prompting?

Single-shot prompts leave an LLM with no feedback. The model cannot know when it has hallucinated because it has no mechanism to compare output against external ground truth. A loop provides that mechanism: each pass through the cycle updates external state, checks constraints, and feeds corrections back into the next pass.

### The 6-Step Architecture

The loop has a breath rhythm: systole (contraction, action, output) and diastole (expansion, reflection, learning).

1. **Situational Awareness (systole)** — Load state, peek at other windows, match trajectory
2. **Task Execution (systole)** — Scope, pre-flight, execute, cleanup
3. **Associative Learning (diastole)** — Match new knowledge against existing patterns
4. **Abstract Generalization (diastole)** — Extract transferable patterns
5. **Context Persistence (diastole)** — Write checkpoint, cross-session continuity
6. **Trajectory Update (diastole)** — Record delta, close loop to step 1

### Layered Safety Architecture

Three independent layers, all living outside the model's reach:

```
Layer 1: PreToolUse Hook (.claude/hooks/PreToolUse)
  Runs before every tool call. COG_STEP + RECURSION_LIMIT checks.
  v2: blocked_state.json terminal gate — prevents infinite retry loops.

Layer 2: Safety Monitoring (scripts/safety/)
  heartbeat.py    — Minimal+ heartbeat (atomic write, <1KB)
  blocked_state.py — Terminal state persistence (No Silent Terminal State)
  watchdog.py     — Subprocess detector (detect only, no auto-restart)
  trust_gate.py   — Multi-dimensional trust gate (uses stubs)
  trust_labeler.py — Trust labeler (uses stubs)
  trust_features.py — Feature extraction (uses stubs)
  audit_gate.py   — Audit trail gate
  failure_learner.py — Failure pattern learner

Layer 3: Fuse Board (scripts/core-engine/fuse_board.py)
  11 fuses: WRITE_PROTECT, RECURSION_LIMIT, TOKEN_BUDGET, PARALLEL_CAP,
  CHECKPOINT_REQUIRED, PROXY_PURITY, NUMERIC_COMPUTATION,
  SELF_EVALUATION_PROHIBITED, DUAL_AI_GATE, QWEN_DOWN_TOO_LONG,
  SELF_MODIFICATION (MVS).
  Stdlib-only, zero imports from protected modules.
  Config: data/safety-configs/fuses_config.json
```

---

## 2. Implemented Components

These components exist on disk and are functional.

### 2.1 Core Engine (`scripts/core-engine/`)

| Component | File | Status |
|-----------|------|--------|
| Fuse Board | `fuse_board.py` | ✅ 784 lines, 11 fuses, stdlib-only, self-test 20/20 |
| Dual-AI Gate | `qwen_gate.py` | ✅ 1139 lines, generator/evaluator separation, uses api_pipeline stub |
| Capability Router | `capability_router.py` | ✅ 223 lines, rules-based domain routing |

The Dual-AI Gate (qwen_gate.py) is the cognitive engine: DeepSeek generates, Qwen independently verifies. Statistical guarantee: p(both wrong) = p(DS) × p(Qwen) ≈ 1% at 10% baseline hallucination rate.

The gate depends on `scripts/wheels/api_pipeline.py` (stub) for external API calls. In standalone extraction, the stub raises NotImplementedError — the gate's verification path is unavailable, but the fuse board and safety modules continue to function.

**Gate trigger conditions:**

| Condition | Action |
|-----------|--------|
| Writing to knowledge base | Forced verification |
| Session > 60K tokens | Forced verification |
| Material + numerical computation | Forced verification |
| 30-60K + numerical computation | Preventive verification |

### 2.2 Safety Monitoring (`scripts/safety/`)

| Component | File | Status |
|-----------|------|--------|
| Heartbeat | `heartbeat.py` | ✅ Minimal+, atomic write, <1KB |
| Blocked State | `blocked_state.py` | ✅ Terminal state persistence |
| Watchdog | `watchdog.py` | ✅ Subprocess, detect only |
| Trust Gate | `trust_gate.py` | ✅ Multi-dimensional, uses stubs |
| Trust Labeler | `trust_labeler.py` | ✅ Uses stubs |
| Trust Features | `trust_features.py` | ✅ Uses stubs |
| Audit Gate | `audit_gate.py` | ✅ 92 lines, audit trail |
| Failure Learner | `failure_learner.py` | ✅ 252 lines, pattern learning |

### 2.3 Safety Stubs (`scripts/wheels/`)

These modules exist in the original system but were excluded from standalone extraction. They preserve import paths and raise NotImplementedError:

| Stub | Imported by | Original location |
|------|-------------|-------------------|
| `api_pipeline.py` | qwen_gate.py | Full API pipeline with rate limiting |
| `trust_features.py` | trust_gate.py, trust_labeler.py | 8-dimension feature extraction |
| `cross_validator.py` | trust_gate.py, trust_labeler.py | Multi-perspective validation |

### 2.4 PreToolUse Hook (`scripts/core-engine/fuse_board.py`)

The PreToolUse hook (`.claude/hooks/PreToolUse`) runs before every tool call:

1. **COG_STEP Gate** — Denies Write/Edit without valid step declaration (TTL: 300s)
2. **RECURSION_LIMIT** — Blocks at depth > 5, writes blocked_state.json (terminal)
3. **Terminal State Check** — Before any check, verifies blocked_state is clear

Design: the hook enforces correctly (verified in PR #1 investigation). The blocked state persistence (v2) prevents infinite retry loops by making the terminal state observable to the caller.

### 2.5 Architecture Contract

`scripts/verify_architecture.py` — Two-layer contract test:

- **Layer 1 (default):** String-scan imports + doc refs → verify file existence. Zero side effects.
- **Layer 2 (--deep):** `importlib.util.find_spec()` — verify resolvability without executing module code.
- Exit codes: 0=pass, 1=Layer 1 ghosts, 2=Layer 2 failures.

---

## 3. Planned Components

These components are designed but not yet implemented. They appear in the cognitive workflow definition (`workflows/cognitive_core_loop.json`) and the ADR process.

| Component | Design ref | Priority |
|-----------|-----------|----------|
| `scripts/wheels/strategy_selector.py` | Cognitive Core Loop Step 2 | Post-safety-recovery |
| `scripts/wheels/epsilon_gate.py` | Exploration policy (see ADR-0001 D-005) | Post-identity-decision |
| `scripts/wheels/external_anchor.py` | Fact anchoring extension | Future |
| `scripts/wheels/cls_memory.py` | CLS memory search | Future |
| `scripts/wheels/path_mutation.py` | Exploration branching | Future |
| `scripts/wheels/premise_check.py` | File/PID state verification | Future |
| `scripts/wheels/cross_window_hook.py` | Multi-window coordination | Future |
| `scripts/wheels/knowledge_quality_gate.py` | Knowledge quality thresholding | Future |
| `scripts/wheels/compact_health_board.py` | Compact health dashboard | Future |
| `scripts/self_activate.py` | Session init, health checks | Future |
| `scripts/anti_atrophy_consumer.py` | Knowledge decay prevention | Future |

---

## 4. Research Components

These are architectural concepts described in the whitepaper (`WHITE_PAPER.md`) and cognitive cycle design (`COGNITIVE_CYCLE.md`). They have been designed at the information-theoretic or mathematical level but have no implementation plan yet.

| Component | Concept | Current status |
|-----------|---------|---------------|
| `scripts/wheels/symbolic_observer.py` | Event-to-symbol mapping for information-theoretic monitoring | Architectural sketch only |
| `scripts/symbolic_dynamics_engine.py` | 8-domain entropy computation, Shannon entropy over tool-call sequences | Mathematical model exists |
| `scripts/cross_window_awareness.py` | Cross-window symbolic dynamics awareness | Dependent on symbolic engine |
| `data/symbolic_dynamics/` | Symbolic verdict tracking | Not created |
| FPGA watchdog timer | Hardware-level fuse board (WHITE_PAPER.md §12) | Research concept; no hardware |

The symbolic dynamics pipeline (WHITE_PAPER.md §4) would apply information-theoretic monitoring to tool-call sequences — computing entropy rates, forbidden-word counts, and stability metrics over rolling windows. Interesting concept, but it adds significant complexity before the core safety loop is verified.

---

## 5. Runtime State

These files are generated at runtime and are not tracked in version control:

| File | Purpose |
|------|---------|
| `data/state/cog_step.json` | Current cognitive step declaration |
| `data/state/recursion_depth.json` | Recursion depth counter (hook) |
| `data/state/hook_audit.jsonl` | Hook decision audit trail |
| `data/state/heartbeat.json` | Heartbeat (Minimal+ format) |
| `data/state/blocked_state.json` | Terminal state marker |
| `data/state/watchdog_critical.json` | Watchdog CRITICAL marker |
| `data/safety/fuse_log.jsonl` | Fuse board event log |
| `data/safety/fuse_state.json` | Fuse board runtime state |

---

## 6. Design Principles

1. **File-anchored, not memory-anchored:** Rules live in files the model cannot modify.
2. **Fail-closed for safety, fail-open for capability:** Safety fuses (RECURSION, WRITE_PROTECT, SELF_MODIFICATION) block on error; capability fuses (TOKEN_BUDGET, PARALLEL_CAP) may allow on crash.
3. **Generator/Evaluator separation:** Creator never judges creation.
4. **External state:** Session state written to files, not held in model context.
5. **Anti-self-modification:** Core scripts in WRITE_PROTECT list.
6. **No Silent Terminal State:** Any condition that permanently stops execution is persisted to `blocked_state.json` and blocks further retries (verified: PR #1 investigation corrected a false hypothesis about Detection ≠ Enforcement).
7. **Minimum Viable Safety (MVS):** If primary config is missing, activate 3 hard fuses (RECURSION_LIMIT, WRITE_PROTECT, SELF_MODIFICATION) with CRITICAL logging.
8. **Minimum Viable Observability (MVO):** Heartbeat + audit for detectability, separate from safety.
9. **Privacy of the cognitive cycle:** Avoid speculative over-design. The 6-step cycle is sound; its sub-steps should be built only when evidence demands them.
10. **Identity deferral:** Product-vs-research identity decision deferred until safety observability is restored. Only 4 configs depend on identity (fail_open, exploration, persistence, restart).
