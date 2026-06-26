# Cognitive Justification Review

**Gate type:** Decision gate
**Opens after:** Operational Validation (3-7 days)
**Blocks:** Rebuild Cognition phase
**Status:** PENDING (to be answered after validation)

---

## Purpose

Before investing in rebuilding the cognitive layer (missing wheels, extended 6-step execution, symbolic dynamics, etc.), establish whether these components are *necessary* or merely *architecturally symmetrical*.

The Safety Recovery Epic (ADR-0001) demonstrated that several key assumptions about the system were wrong. The freeze was not an enforcement failure; the core safety loop was working. The missing wheels caused NotImplementedError, not system collapse. These findings change the cost-benefit calculation for rebuilding cognition.

## The Three Questions

### Q1: What capability is actually missing?

Describe the gap in concrete terms. Not "we lack symbolic dynamics" but "we cannot detect X at runtime."

**Guidelines:**
- State the missing output/behavior, not the missing component name
- Reference a real user scenario or operational failure
- If no real scenario exists, it's not missing

**Examples:**
- ❌ "We need cross-window awareness" (component name)
- ✅ "Two Claude Code sessions modified the same file without coordination" (real failure)
- ❌ "We need symbolic dynamics for entropy monitoring"
- ✅ "The system has been diverging for 4 hours and nobody noticed" (real gap)

### Q2: Is the gap solvable only by rebuilding cognition?

Some gaps have simpler fixes:
- A hook check (10 lines of bash) may replace a missing wheel
- A README note may replace a coordination protocol
- Stdlib Python may replace a symbolic dynamics engine

**If the gap can be fixed with 10 lines of hook code, do that first.**

### Q3: What evidence exists that this component is needed?

Not architectural symmetry. Not "the white paper describes it." Real evidence:

| Evidence type | Strength | Example |
|--------------|----------|---------|
| Operational failure | High | "System froze because..." |
| User requirement | High | "I need the system to..." |
| Logged incident | Medium | "hook_audit shows..." |
| Architectual gap analysis | Low | "The design is incomplete without..." |
| White paper reference | Zero | "WHITE_PAPER.md describes..." |

**Threshold for proceeding:** At least one piece of High evidence, or 2+ Medium evidence items.

## Evaluation Matrix

| Component | Q1: Missing capability | Q2: Requires rebuild? | Q3: Evidence |
|-----------|----------------------|---------------------|-------------|
| `strategy_selector.py` | | | |
| `epsilon_gate.py` | | | |
| `external_anchor.py` | | | |
| `cls_memory.py` | | | |
| `path_mutation.py` | | | |
| `premise_check.py` | | | |
| `cross_window_hook.py` | | | |
| `knowledge_quality_gate.py` | | | |
| `self_activate.py` | | | |
| `anti_atrophy_consumer.py` | | | |
| `symbolic_observer.py` | | | |
| `symbolic_dynamics_engine.py` | | | |
| `cross_window_awareness.py` | | | |

## Decision

After Operational Validation, fill the matrix and decide:

- **PASS:** At least one component has High evidence AND requires rebuild → Proceed with Rebuild Cognition
- **FAIL:** No component meets the threshold → Close the Cognitive Core Epic, keep the system as an observability-first prototype
- **DEFER:** Some components have Medium evidence → Build only those, defer the rest

---

*This gate is intentionally strict. The Safety Recovery phase cost ~1500 lines of code and 4 PRs to fix what turned out to be a single wrong directory path. Before adding another 1500 lines for "cognition," be certain it's needed.*
