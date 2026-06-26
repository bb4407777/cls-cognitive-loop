"""
api_pipeline.py — STUB (standalone extraction)

This module exists in the original system but was not included in the
standalone extraction at scripts/wheels/. Its import path is preserved
so that dependent modules (qwen_gate.py) can be imported without error.

To restore: replace this stub with the real api_pipeline module.
"""

__stub__ = True
__original_location__ = "scripts/wheels/api_pipeline.py"


def call(*args, **kwargs):
    """API pipeline call — not available in standalone extraction.

    The real api_pipeline provides rate-limited, retry-capable API calls
    to external LLM providers. Without it, qwen_gate cannot perform
    dual-model verification but the system remains operational for
    fuse-level safety enforcement.
    """
    raise NotImplementedError(
        "api_pipeline was not included in standalone extraction. "
        "qwen_gate dual-model verification is unavailable. "
        "Fuse board and safety modules continue to function."
    )
