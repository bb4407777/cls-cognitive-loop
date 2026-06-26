# Recursion Enforcement Investigation

**Date:** 2026-06-27
**Part of:** ADR-0001 Safety Recovery (Step 3)
**Author:** Architecture review follow-up

---

## Question

Why did the system produce 5+ consecutive RECURSION BLOCK events in hook_audit.jsonl on 2026-06-25, and why did the cognitive loop freeze afterward?

## Methodology

1. Read `.claude/hooks/PreToolUse` — the actual enforcement mechanism
2. Read `data/state/hook_audit.jsonl` — the audit trail
3. Read `data/state/recursion_depth.json` — the depth counter
4. Traced the causal chain from CONFIG_PATH error → fuse disable → hook behavior

## Findings

### Finding 1: The Hook Enforces Correctly — but Creates a Retry Loop

The PreToolUse hook at `.claude/hooks/PreToolUse` independently checks recursion depth:

```bash
# Lines 41-51
depth=$(python3 -c "import json; print(json.load(open('$RECURSION_FILE'))['depth'])")
depth=$((depth + 1))
if [[ $depth -gt $MAX_DEPTH ]]; then
  log "BLOCK" "RECURSION" "depth=$depth"
  echo '{"permissionDecision":"deny",...}'
  exit 0
fi
echo '{"depth":$depth,...}' > "$RECURSION_FILE"
```

The hook:
- Reads current depth from `recursion_depth.json`
- Increments it
- **Blocks if depth > 5** (exit 0 with deny verdict)
- **Only updates the file on PASS** (line 51 never runs after block)

### Finding 2: Depth Get Stuck at 5, Creating Infinite Block Loop

| Step | Event | `recursion_depth.json` |
|------|-------|----------------------|
| 1 | Tool call A | reads depth=5, increments to 6 → **BLOCK** |
| 2 | Tool call B | reads depth=5, increments to 6 → **BLOCK** |
| 3 | Tool call C | reads depth=5, increments to 6 → **BLOCK** |
| ... | (repeats) | depth stays at 5 |

Since the file never advances past 5 (all subsequent calls are blocked before the write), the LLM keeps retrying and each retry hits the same block. This explains the **20 consecutive BLOCK entries** across ~2 hours (10:23 to 12:04).

### Finding 3: Fuse Board Was Irrelevant to This Freeze

The fuse board's `_check_recursion_limit` was **never called** during the freeze. The enforcement was entirely at the hook layer. However, the fuse board's CONFIG_PATH was also wrong, meaning:

| Layer | During freeze | After fix |
|-------|---------------|-----------|
| PreToolUse hook | **Enforcing** (depth > 5 = block) | Same — no change needed |
| fuse_board._check_recursion_limit | **Disabled** (config not found → enabled=false → always returns True) | **Enforcing** (config loads correctly) |

The fuse board's RECURSION_LIMIT would NOT have helped during the freeze because the hook was already blocking at the same depth. The fuse board provides defense-in-depth but would have behaved identically.

### Finding 4: The Real Root Cause Was the Retry Loop, Not Ignored Return Value

The R2/R3 hypothesis was "ignored return value from block()" (60% probability). **This was incorrect.** The hook enforces via `exit 0` with a deny verdict, which Claude Code respects. The problem was:

1. LLM makes a tool call
2. Hook blocks it (correctly)
3. LLM retries with a different tool/input
4. Hook blocks again (depth counter never advances)
5. Repeat → infinite retry loop until session timeout or manual intervention

This is a **LLM behavior problem**, not an enforcement bug. The hook fires correctly; the LLM doesn't understand that it should stop retrying.

## Root Cause Summary

```
CONFIG_PATH wrong (scripts/data/safety-configs/ instead of data/safety-configs/)
    → fuse board silently disabled (all fuses: enabled=false)
    → not relevant to recursion freeze (that was the hook)
    → but created false sense of safety

PreToolUse hook enforces recursion correctly
    → blocks at depth > 5
    → but LLM retries indefinitely → infinite block loop
    → system appears frozen to an observer

Combined effect:
    Hook is working but causing retry storms
    Fuse board is silent (disabled)
    Observer sees "system frozen with safety disabled"
```

## What Changed

With this PR's fixes:
- CONFIG_PATH now points to `data/safety-configs/fuses_config.json` (correct)
- fuse board loads all 10 fuses with proper configuration
- MVS fallback provides minimum protection if config is missing
- The hook behavior is unchanged (it was always working)

## Recommendations for Future

1. **Add exponential backoff to the hook:** After N consecutive blocks, insert a cooldown delay before allowing the next tool call
2. **Add block counter to hook_audit.jsonl:** Track consecutive blocks to detect retry storms
3. **Consider a "circuit breaker" state:** After K consecutive blocks, escalate (write a fatal marker, notify, pause)
