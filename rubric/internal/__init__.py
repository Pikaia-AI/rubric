"""Internal helpers shared across built-in plugins.

Not user-facing — but plugins can import from here:
    from rubric.internal import pkbench_v5
    from rubric.internal import outline_alignment
    from rubric.internal import parrot as _parrot

Underscore-prefixed at the directory level (`builtin_metrics/_shared/`) would
also work for plugin-local sharing, but we keep this as a regular package
so eval adapters and external consumers can reach the same code.
"""
