# scripts/wheels — stubs for standalone extraction
# See docs/adr/ADR-0001-safety-recovery-plan.md §Ghost-References
# These modules exist in the original system but were not included
# in the standalone extraction. They raise NotImplementedError to
# make missing capability explicit vs silent ModuleNotFoundError.
