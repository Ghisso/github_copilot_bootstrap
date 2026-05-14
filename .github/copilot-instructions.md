# GitHub Copilot Workspace Adapter

This repository now keeps source-of-truth guidance in `shared/` and generated installable guidance in `dist/multi-agent/`.

For work inside this bootstrap repo:

- Read `shared/policies/workspace.instructions.md` for neutral workspace guidance.
- Read `shared/policies/tool-routing.instructions.md` before choosing between direct reads, `rg`, Semble, and context-mode.
- Edit source files under `shared/`, `scripts/`, `docs/`, and `targets/`; do not hand-edit `dist/`.
- Preserve the plan -> implement -> verify -> review -> score workflow.
- Keep hook guardrails intact; this root adapter invokes `shared/hooks/scripts/`.

Regenerate and validate after source changes:

```bash
python3 scripts/generate_targets.py --all
python3 scripts/validate_targets.py
python3 scripts/check_runtime.py
```

