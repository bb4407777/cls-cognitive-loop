#!/usr/bin/env python3
"""
verify_architecture.py — Architecture Contract Test (ADR-0001 D-007)

Checks that the codebase is honest about what exists vs what is referenced.

Two layers:
  Layer 1 (default): String-scan imports + docs refs → verify file existence
  Layer 2 (--deep):  importlib.util.find_spec() — verify resolvability
                      without executing module code.

Exit codes:
  0 = all checks passed
  1 = ghost references found (Layer 1)
  2 = unresolvable imports found (Layer 2)
"""

from pathlib import Path
import sys
import re
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DOCS_DIR = PROJECT_ROOT / "docs"

# Known stubs (purposefully missing implementations)
KNOWN_STUBS = {
    "scripts.wheels.api_pipeline",
    "scripts.wheels.trust_features",
    "scripts.wheels.cross_validator",
}

# Known docstring-only references (usage examples in file headers, not code imports)
KNOWN_DOCSTRING_REFS = {
    "scripts.wheels.qwen_gate",
    "scripts.wheels.trust_gate",
    "scripts.wheels.trust_labeler",
    "scripts.fuse_board",  # docstring usage example in fuse_board.py itself
}

# Known planned/research components (documented in ARCHITECTURE.md §3/§4)
KNOWN_PLANNED = {
    "scripts/self_activate.py",
    "scripts/wheels/strategy_selector.py",
    "scripts/wheels/epsilon_gate.py",
    "scripts/wheels/external_anchor.py",
    "scripts/wheels/cls_memory.py",
    "scripts/wheels/path_mutation.py",
    "scripts/wheels/premise_check.py",
    "scripts/wheels/cross_window_hook.py",
    "scripts/wheels/knowledge_quality_gate.py",
    "scripts/wheels/compact_health_board.py",
    "scripts/anti_atrophy_consumer.py",
}

KNOWN_RESEARCH = {
    "scripts/wheels/symbolic_observer.py",
    "scripts/symbolic_dynamics_engine.py",
    "scripts/cross_window_awareness.py",
}

# Patterns to search
IMPORT_PATTERN = re.compile(
    r'(?:from\s+(scripts\.[\w.]+)\s+import|import\s+(scripts\.[\w.]+))'
)
DOCS_REF_PATTERN = re.compile(r'(scripts/[\w./]+\.py)')


def extract_imports_from_file(path: Path) -> set[str]:
    """Extract scripts.* import paths from a Python file."""
    imports = set()
    try:
        content = path.read_text(encoding="utf-8")
        for match in IMPORT_PATTERN.finditer(content):
            mod = match.group(1) or match.group(2)
            imports.add(mod)
    except (OSError, UnicodeDecodeError):
        pass
    return imports


def import_to_path(mod: str) -> Path:
    """Convert 'scripts.core_engine.fuse_board' to Path."""
    return SCRIPTS_DIR / mod.replace("scripts.", "").replace(".", "/") / "__init__"


def import_to_file(mod: str) -> Path:
    """Convert 'scripts.core_engine.fuse_board' to the .py file path.

    Tries module/__init__.py first, then module.py.
    """
    base = SCRIPTS_DIR / mod.replace("scripts.", "").replace(".", "/")
    py_file = base.with_suffix(".py")
    init_file = base / "__init__.py"
    return py_file if py_file.exists() else init_file


def extract_doc_refs(file_path: Path) -> set[str]:
    """Extract file paths referenced in documentation."""
    refs = set()
    try:
        content = file_path.read_text(encoding="utf-8")
        for match in DOCS_REF_PATTERN.finditer(content):
            ref_path = match.group(1)
            refs.add(ref_path)
    except (OSError, UnicodeDecodeError):
        pass
    return refs


def layer1_check() -> list[str]:
    """Layer 1: String-scan imports -> verify file existence.

    Returns list of ghost references found (empty = pass).
    """
    ghosts = []

    # Scan all Python files
    for py_file in sorted(SCRIPTS_DIR.rglob("*.py")):
        if ".stub" in py_file.name or "__pycache__" in str(py_file):
            continue
        imports = extract_imports_from_file(py_file)
        for mod in sorted(imports):
            # Known stubs and docstring-only refs are allowed
            if mod in KNOWN_STUBS or mod in KNOWN_DOCSTRING_REFS:
                continue
            target = import_to_file(mod)
            if not target.exists():
                ghosts.append(f"{py_file.relative_to(PROJECT_ROOT)} imports {mod} → {target.relative_to(PROJECT_ROOT)} NOT FOUND")

    # Scan docs for file references
    for doc_file in sorted(DOCS_DIR.rglob("*.md")):
        refs = extract_doc_refs(doc_file)
        for ref in sorted(refs):
            # Skip known planned/research components
            if ref in KNOWN_PLANNED or ref in KNOWN_RESEARCH:
                continue
            ref_path = PROJECT_ROOT / ref
            if not ref_path.exists():
                # Check if it's a stub
                stub_marker = ref_path.with_name(ref_path.stem + ".py")
                stub_dir_marker = ref_path.parent / "__init__.py"
                if not stub_marker.exists() and not stub_dir_marker.exists():
                    ghosts.append(f"{doc_file.relative_to(PROJECT_ROOT)} references {ref} → NOT FOUND")

    return ghosts


def layer2_check() -> list[str]:
    """Layer 2: importlib.util.find_spec() — verify resolvability.

    Returns list of unresolvable imports (empty = pass).
    """
    import importlib.util
    # Ensure project root and scripts dir are on path for find_spec
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    unresolvable = []

    # Collect all unique imports from all Python files
    all_imports = set()
    for py_file in sorted(SCRIPTS_DIR.rglob("*.py")):
        if ".stub" in py_file.name or "__pycache__" in str(py_file):
            continue
        all_imports.update(extract_imports_from_file(py_file))

    # Filter to only scripts. imports
    script_imports = {m for m in all_imports if m.startswith("scripts.")}

    for mod in sorted(script_imports):
        if mod in KNOWN_STUBS or mod in KNOWN_DOCSTRING_REFS:
            continue
        spec = importlib.util.find_spec(mod)
        if spec is None:
            unresolvable.append(f"importlib can't resolve: {mod}")

    return unresolvable


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Architecture Contract Test")
    parser.add_argument("--deep", action="store_true", help="Run Layer 2 (find_spec)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    result = {"layer1": {"status": "pass", "ghosts": []}, "layer2": {"status": "skipped", "ghosts": []}}
    exit_code = 0

    # Layer 1
    ghosts = layer1_check()
    if ghosts:
        result["layer1"]["status"] = "fail"
        result["layer1"]["ghosts"] = ghosts
        exit_code = 1

    # Layer 2
    if args.deep:
        result["layer2"]["status"] = "running"
        unresolvable = layer2_check()
        if unresolvable:
            result["layer2"]["status"] = "fail"
            result["layer2"]["ghosts"] = unresolvable
            exit_code = 2
        else:
            result["layer2"]["status"] = "pass"

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Layer 1 results
        l1 = result["layer1"]
        print(f"Layer 1 (file exists): {l1['status'].upper()}")
        if l1["ghosts"]:
            for g in l1["ghosts"]:
                print(f"  ❌ {g}")
        else:
            print("  ✅ All imports resolve to existing files")

        # Layer 2 results
        l2 = result["layer2"]
        if args.deep:
            print(f"Layer 2 (find_spec): {l2['status'].upper()}")
            if l2["ghosts"]:
                for g in l2["ghosts"]:
                    print(f"  ❌ {g}")
            else:
                print("  ✅ All imports resolvable via find_spec()")
        else:
            print(f"Layer 2 (find_spec): SKIPPED (use --deep)")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
