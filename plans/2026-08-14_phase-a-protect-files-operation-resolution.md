---
name: 2026-08-14_phase-a-protect-files-operation-resolution
type: small-plan
parent_plan: protect-files-operation-resolution
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-14_phase-a-protect-files-operation-resolution

## Scope

Repair the protect-files classifier as one atomic control-plane phase. The
phase must remove confirmed command-text false positives, close the confirmed
wildcard move bypass, preserve diagnostic reads, retain fail-closed behavior
for genuine protected-file mutations, and propagate the canonical result to
all generated consumer targets.

Primary implementation ownership is `shared/hooks/scripts/protect-files.py`
and its focused regression coverage. Update policies and public documentation
where their description of protected literals, mutation operands, or wildcard
coverage changes. Do not hand-edit `dist/multi-agent/`.

Required review profiles: `code`, `architecture`, `security`, `tests`, and
`ponytail`.

## Steps

- [ ] Record baseline tests that replay all reported commands through the
      canonical classifier for both Claude and Codex decision envelopes:
  - `git mv terraform/secrets.tf terraform/aws/secrets.tf` is allowed when the
    paths are ordinary Terraform source/configuration.
  - `git commit -m "...Needs AWS credentials..."` is allowed because prose is
    not a filesystem operand.
  - `grep -n closeout .claude/hooks/scripts/enforce-commit-gate.sh` remains
    allowed as read-only inspection.
  - A Python heredoc containing `def secret(self, ref: str)` is allowed when it
    names no protected filesystem target.
  - `mv terraform/* terraform/aws/` is denied when the wildcard selects any
    protected source, and allowed when it selects only ordinary files.
- [ ] Refactor shell-segment classification to represent operation kind,
      source operands, destination operands, effective working directory, and
      confidence explicitly rather than placing arbitrary protected-looking
      words into a single `uncertain` bucket.
- [ ] Add safe operand resolution for relative paths and common shell wildcard
      syntax (`*`, `?`, and bracket expressions) without invoking a shell.
      Resolve matches against a controlled repository working directory,
      normalize results deterministically, preserve source/destination roles,
      and define conservative behavior for unmatched, malformed, escaping, or
      otherwise unsupported patterns.
- [ ] Model `git mv` as a mutation with resolved source and destination
      operands. Preserve the existing Git global-option parsing and ensure
      protected source or destination cases still deny, including `.env`,
      credentials, private keys, and hook/config paths.
- [ ] Replace broad command-text and `"secret" in basename` matching with
      high-confidence path predicates. Keep `.env*`, `uv.lock`,
      `credentials*`, `.pem`/`.key`, hook trees, and explicit hook/client
      configuration protected. Add negative coverage for `secrets.tf`,
      `secretmanager.py`, and `test_secrets.py`.
- [ ] Preserve the read/write boundary: read-only commands may inspect
      protected resources unless they specify an output/in-place mutation;
      confirmed writes remain denied or asked according to the existing
      Claude/Codex policy. Add tests for redirects, `sed`/`perl` in-place
      writes, `git --output`, copy/install/move protected sources, and native
      edit payloads so the refactor cannot weaken established cases.
- [ ] Add adversarial regression coverage for wildcard sources and
      destinations, multiple matches, hidden files where applicable, quoted
      wildcards, relative paths, `..` traversal, symlinks, command wrappers,
      Git `-C`, chained segments, malformed commands, and empty/unmatched
      patterns. Tests must demonstrate both false-positive reduction and
      bypass closure rather than asserting only emitted message text.
- [ ] Update `README.md`, `docs/architecture.md`, `docs/runtime-checks.md`,
      `docs/smoke-tests.md`, and the canonical policy text as applicable so
      the documented contract matches operation-aware resolution and no
      longer promises command-wide secret-name scanning.
- [ ] Regenerate `dist/multi-agent/` from `shared/`, validate target parity,
      and verify installed Claude and Codex hook wiring still routes Bash
      through the ordered guard chain.
- [ ] Run the full control-plane lifecycle: implementation-time Ponytail in
      `full` mode, focused simplification and re-verification, verifier pass,
      reviewer passes for all required profiles, documentation pass, persisted
      findings, score, learning capture, closeout session log, and one atomic
      phase commit.

## Acceptance Criteria

- All five reported command shapes have explicit regression tests; the four
  false-positive cases are allowed and the wildcard protected-source case is
  denied.
- Ordinary source/configuration basenames containing `secret` are not treated
  as credentials solely because of their names.
- Genuine protected mutations and protected-source copy/move/install cases
  remain denied, including when selected through supported wildcards.
- No shell execution or command substitution is used to discover affected
  paths.
- Generated Claude and Codex copies are byte-consistent with canonical source
  and target validation passes.
- Persisted review findings contain zero CRITICAL findings, no unresolved
  blocking security finding remains, and the final matching quality score is
  at least 90.

## Verification

```bash
uv run pytest tests/test_hook_gates.py -q --tb=short
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ shared/scripts/ tests/
uv run ruff format --check scripts/ shared/scripts/ tests/
git diff --check
uv run python .claude/scripts/record_findings.py . --profile code --profile architecture --profile security --profile tests --profile ponytail --phase 2026-08-14_phase-a-protect-files-operation-resolution --base-ref dev --findings-json <reviewer-findings.json> --out .claude/quality_reports/findings-<timestamp>.json
uv run python .claude/scripts/quality_score.py . --phase 2026-08-14_phase-a-protect-files-operation-resolution --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Closeout Checklist

- [ ] Focused and full verification passed
- [ ] Code, architecture, security, tests, and Ponytail findings resolved
- [ ] Findings report persisted with zero CRITICAL findings
- [ ] Score >= 90 persisted with matching branch/phase metadata
- [ ] Documentation updated before final findings and score persistence
- [ ] LEARN entries saved or explicit no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] One atomic commit created for this small plan
