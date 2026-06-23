# CLS Cognitive Loop

> **An autonomous cognitive architecture that structures LLM agent reasoning into a provable 6-step closed loop — with dual-AI verification, circuit-breaker safety, and cross-session learning.**
> 
> Author: **认知工坊** (Cognitive Workshop)  
> Contact: QQ 1419456542 · Email zyc2018@mail.ustc.edu.cn

CLS (Cognitive Loop System) is a harness-level reasoning framework that turns stochastic LLM outputs into a verifiable, self-improving pipeline. Instead of letting the model generate and move on, CLS wraps every task in a 6-step cognitive cycle that forces situational awareness, structured execution, adversarial learning, abstract generalization, persistent context, and trajectory recording. The architecture was committed to code on **2026-05-25** — roughly 2 weeks before the "Loop Engineering" discourse reached the public AI engineering community in June 2026.

---

## Table of Contents

- [Origin Story](#origin-story)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Core Concepts](#core-concepts)
  - [The 6-Step Cognitive Cycle](#the-6-step-cognitive-cycle)
  - [Dual-AI Gate](#dual-ai-gate)
  - [Fuse Board (Circuit Breakers)](#fuse-board-circuit-breakers)
  - [Symbolic Dynamics Audit](#symbolic-dynamics-audit)
  - [Cross-Window Awareness](#cross-window-awareness)
  - [Fact Anchoring Protocol](#fact-anchoring-protocol)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Contributing](#contributing)
- [License](#license)

---

## Origin Story

In May 2026, during the development of a Claude Code harness system, a pattern emerged: single-pass LLM interactions kept hitting the same walls — context drift, self-referential hallucination, and no persistent memory of what was just done. Tasks that spanned multiple sessions degraded because there was no structural "spine" to carry state forward.

On **2026-05-25**, commit [`73ee3a84`](#) landed the first implementation of a 6-step cognitive cycle in code. The six steps were:

1. **Situational Awareness** — read active context, match trajectory to user intent
2. **Task Execution** — scope judgment, pre-flight checks, execution, cleanup
3. **Associative Learning** — match new knowledge against existing patterns
4. **Abstract Generalization** — extract transferable patterns from concrete experience
5. **Context Persistence** — write checkpoint to disk for cross-session continuity
6. **Trajectory Update** — record delta-Q (question shift) and delta-P (progress shift)

Two weeks later, in early June 2026, Anthropic's Boris Cherny (creator of Claude Code) and Google's Addy Osmani began publicly discussing "Loop Engineering" — the idea that AI harnesses should automatically assemble context, generate prompts, execute, observe, and loop, replacing the old paradigm of hand-written prompts. The concept resonated because it validated the direction CLS had already taken.

**Timeline:**

| Date | Event |
|------|-------|
| 2026-05-25 | CLS 6-step cognitive cycle first committed (commit `73ee3a84`) |
| 2026-06-02 | Fuse Board (circuit breaker system) activated in code |
| 2026-06-03 | Dual-AI Gate (generator/evaluator separation) enforced |
| 2026-06-07 | Addy Osmani publishes "Loop Engineering" blog post naming the paradigm |
| Mid-June 2026 | Boris Cherny & Peter Steinberger public talks on loop-based harness design |

**What CLS adds beyond the basic loop concept:**

- **Generator/Evaluator separation** — not just "don't evaluate your own output," but a *second independent model* (Qwen) serving as verifier, with a statistical guarantee: P(DS err) * P(QW err) = dual-hallucination rate (e.g., 0.1 * 0.1 = 1%)
- **Circuit breaker layer** — 6 independent fuses that run *outside* the cognitive system, written in pure stdlib with no imports from the reasoning modules they protect
- **Symbolic compression** — a 50K-token conversation compresses to 3 numbers + 1 status word via topological entropy, Perron-Frobenius spectrum, and forbidden-word state machine
- **Cross-window coordination** — multiple Claude Code sessions share a state file, peeking at each other's focus to avoid domain collisions

---

## Architecture at a Glance

```
                    ┌─────────────────────────────────────────┐
                    │            FUSE BOARD (stdlib)            │
                    │  WRITE_PROTECT | RECURSION | TOKEN_BUDGET │
                    │  PARALLEL_CAP | CHECKPOINT | PROXY_PURITY │
                    └──────────────┬──────────────────────────┘
                                   │ checks every operation
    ┌──────────────────────────────▼──────────────────────────────┐
    │                     COGNITIVE CORE LOOP                      │
    │                                                              │
    │  ① Situational Awareness ──→ ② Task Execution                │
    │         ▲                          │                          │
    │         │                          ▼                          │
    │  ⑥ Trajectory Update ←──── ③ Associative Learning            │
    │         │                          │                          │
    │         ▼                          ▼                          │
    │  ⑤ Context Persistence ←── ④ Abstract Generalization         │
    │                                                              │
    └──────────────────────────────────────────────────────────────┘
                    │                           │
          ┌─────────▼─────────┐       ┌────────▼─────────┐
          │   DUAL-AI GATE     │       │ SYMBOLIC DYNAMICS │
          │ DS creates         │       │ Real-time audit   │
          │ Qwen verifies      │       │ <200ms per check  │
          └───────────────────┘       └───────────────────┘
```

- **docs/** — Detailed documentation for each architectural component
- **scripts/core-engine/** — The loop executor, strategy selector, and convergence lock
- **scripts/safety/** — Fuse board, dual-AI gate, premise check, and symbolic dynamics engine
- **rules/** — P0 (non-negotiable) rules and design philosophy
- **workflows/** — Reusable task pipelines (knowledge capture, context save, etc.)
- **data/workflows/** — JSON workflow definitions
- **data/safety-configs/** — Fuse thresholds, gate parameters, and audit configs

---

## Core Concepts

### The 6-Step Cognitive Cycle

Every task — whether a single question or a multi-hour engineering design — passes through six mandatory steps. This is not optional; the harness enforces it structurally.

| Step | Name | What Happens |
|------|------|-------------|
| ① | **Situational Awareness** | Reads `active_context`, `cog_thread`, and `trajectory.json`. Matches user keywords against the last 5 trajectory entries. Peers at other Claude Code windows via cross-window hook. |
| ② | **Task Execution** | Scope judgment (simple/medium/complex) → Pre-flight checks (fuse board, premise validation) → Execution with monitoring → Cleanup. |
| ③ | **Associative Learning** | New knowledge is matched against existing patterns. Similar past tasks are linked. Contradictions are flagged. |
| ④ | **Abstract Generalization** | Concrete experiences are distilled into transferable patterns. "Fixed bug X by changing Y" becomes "class of bugs Z requires pattern W." |
| ⑤ | **Context Persistence** | Active context, current focus, and checkpoint data are written to disk. This is what makes cross-session continuity possible — the system wakes up knowing what it was doing. |
| ⑥ | **Trajectory Update** | Delta-Q (how the question evolved) and delta-P (how progress shifted) are recorded. The trajectory file grows as a searchable history of cognitive movement. |

The loop closes: step ⑥ feeds directly back into step ① on the next task. This is not a linear pipeline — it is a cycle that gets tighter with each iteration.

### Dual-AI Gate

The core statistical insight: two independent models making the same mistake is exponentially less likely than one.

- **Generator (DeepSeek):** Creates designs, writes code, captures knowledge
- **Evaluator (Qwen):** Independently verifies those outputs with a fresh context

The gate operates in three modes:
1. **Design Check** — verifies CAD design completeness and geometric validity
2. **Knowledge Check** — verifies knowledge claim consistency and reproducibility
3. **Numeric Check** — independently recomputes calculations and checks order-of-magnitude

If Qwen is unavailable, the system falls back to Anthropic's Haiku model as an alternate auditor. If both are down, the gate enters `unavailable` status and defaults to allow — but logs a degradation event.

### Fuse Board (Circuit Breakers)

The fuse board is a safety layer that runs *outside* the cognitive system. It does not import any reasoning modules. It is pure Python stdlib. It cannot be modified by the system it protects.

| Fuse | Protects Against | Action |
|------|-----------------|--------|
| `WRITE_PROTECT` | Self-modification of core files | Block writes to protected paths |
| `RECURSION_LIMIT` | Unbounded self-referential nesting (max depth: 5) | Truncate + 30min cooldown |
| `TOKEN_BUDGET` | API cost runaway (2M daily / 500K session) | Block API calls |
| `PARALLEL_CAP` | Simultaneous destructive changes (max 3) | Block new parallel ops |
| `CHECKPOINT_REQUIRED` | No rollback point before major changes | Force save every 300s |
| `PROXY_PURITY` | Semantic transformation in the proxy layer | Allow only field deletion |

The board is designed with a hardware migration path: the `FuseBackend` abstract interface means the software backend can be swapped for a hardware implementation without changing any calling code.

### Symbolic Dynamics Audit

Every tool call passes through a real-time audit daemon that checks against:
- **Forbidden word patterns** — regex state machines that catch known failure signatures
- **Domain-specific transfer matrices** — weighted transition graphs encoding what token sequences are valid
- **Topological entropy** — a single number measuring how "chaotic" the output space is (0 = fully deterministic, ln(N) = completely random)

The daemon processes each check in **under 200ms** and returns a verdict: `allow` (pass), `ask` (flag for human review), or `deny` (block). A 50,000-token conversation ultimately compresses to 3 numbers (topological entropy, spectral radius, alert count) + 1 status word for human oversight.

### Cross-Window Awareness

When multiple Claude Code sessions run simultaneously, they share a state file (`state/cross_window_context.json`). Each window:
- **Peeks** at other windows' focus during Step ① (situational awareness)
- **Announces** its own focus during Step ② (task execution start)
- **Checks for domain collisions** before committing to a task — if another window is already working on the same domain, it coordinates rather than conflicts

This prevents the classic multi-agent problem of two sessions unknowingly editing the same file or pursuing contradictory goals.

### Fact Anchoring Protocol

Every claim made by the system must be anchored to a concrete file path and field value. A statement without a file reference is treated as unsubstantiated. This is the anti-hallucination mechanism at the structural level:

- **Claim:** "The system is healthy."
- **Rejected.** No file path, no field, no evidence.
- **Claim:** "`state/session_health.json#status.msgs_current` = 42, below compact threshold of 150."
- **Accepted.** Verifiable by reading the referenced file.

---

## Repository Structure

```
cls-cognitive-loop/
├── README.md                  # This file (English)
├── README_zh.md               # Chinese version
├── LICENSE                    # Apache 2.0
├── docs/                      # Architecture & concept documentation
├── scripts/
│   ├── core-engine/           # Loop executor, strategy selector, convergence lock
│   └── safety/                # Fuse board, dual-AI gate, premise check, symbolic engine
├── rules/
│   ├── P0-rules/              # Non-negotiable safety & quality rules
│   └── philosophy/            # Design philosophy and first principles
├── workflows/                 # Reusable task pipeline definitions
├── data/
│   ├── workflows/             # JSON workflow schemas
│   └── safety-configs/        # Fuse thresholds, gate parameters
├── CLAUDE_templates/          # Template harness configurations
└── assets/                    # Diagrams and visual assets
```

---

## Getting Started

### Prerequisites

CLS is a **harness-layer architecture** — it is not a standalone application but a set of protocols, scripts, and configuration templates that integrate with an LLM agent host (currently Claude Code). To experiment with or adapt CLS, you need:

- A working Claude Code installation (the architecture is host-independent by design; see `docs/host-independence.md`)
- Python 3.10+ for the safety scripts and symbolic dynamics engine
- (Optional) A second LLM API endpoint for the dual-AI gate (the architecture supports Qwen or any independent model)

### Integration Points

CLS integrates at three levels of an LLM agent harness:

1. **Configuration layer** — `CLAUDE.md` / system prompt templates that encode the 6-step loop as behavioral instructions
2. **Hook layer** — PreToolUse/PostToolUse hooks that run fuse board checks and symbolic audits before every tool call
3. **Daemon layer** — Long-running background processes (symbolic dynamics daemon, activation listener, cross-window state manager)

See `CLAUDE_templates/` for example harness configurations and `docs/integration-guide.md` for step-by-step instructions.

### Quick Validation

```bash
# Run the fuse board self-test (pure stdlib, no dependencies)
python scripts/safety/fuse_board.py --test

# Run the symbolic dynamics engine on sample data
python scripts/safety/symbolic_dynamics_engine.py --test

# Check that the dual-AI gate can initialize (requires API access)
python scripts/safety/qwen_gate.py --health
```

### Design Philosophy

CLS is built on 11 design principles (see `rules/philosophy/design-philosophy.md`). The three most important:

1. **Interface > Implementation** — Signatures are fixed; backends can be swapped. The fuse board abstract interface means a software implementation today can become a hardware implementation tomorrow without changing a single caller.
2. **Triple Product, Not AGI** — CLS does not aim for artificial general intelligence. It aims for `AI × CLS × Human` as a stable closed loop. AI provides computation and generation (the engine). CLS provides memory and constraints (the chassis). Humans provide goals and value judgments (the steering). The product is zero if any factor is zero.
3. **Sparse Activation, Shared Baseline** — The safety layer is always on. Domain-specific skills load on demand. If routing fails, the baseline still holds.

---

## Contributing

CLS is a living architecture that improves through use. Contributions are welcome in several forms:

- **Bug reports:** Open an issue describing the failure mode, expected behavior, and a minimal reproduction case.
- **Architecture proposals:** For significant changes, open a discussion issue first. CLS has strong opinions about separation of concerns (generator vs. evaluator, safety vs. cognition, interface vs. implementation). Proposals that respect these boundaries are more likely to be accepted.
- **Documentation:** Improvements to docs, examples, and integration guides are always valuable.
- **New fuse types:** If you have encountered a failure mode that a new circuit breaker could prevent, propose it with: (a) the accident it prevents, (b) the threshold logic, and (c) the action it takes when tripped.

### Before Submitting

1. Read `rules/philosophy/design-philosophy.md` to understand the architectural constraints.
2. Ensure your change does not import cognitive modules into the safety layer (stdlib-only rule for fuse board).
3. If adding a new fuse, provide the accident history that motivates it — every fuse in CLS corresponds to a real production incident.

---

## License

CLS Cognitive Loop is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.

Copyright 2026 The CLS Project Authors

---

*"The loop does not make the model smarter. It makes the system more stable, more reusable, and more cumulative. Short tasks, verified individually, chained into a cycle — that is the architecture."*
