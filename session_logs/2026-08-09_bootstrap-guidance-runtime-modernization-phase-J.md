# Session: Bootstrap guidance/runtime modernization — Phase J

**Date:** 2026-08-09
**Plan:** .claude/plans/2026-08-04_phase-J-native-probe-parsing-fixes.md
**Status:** COMPLETED

## Goal

Fix the defects that Phase I's probe revealed the first time it was ever run
against real Claude and Codex binaries, and correct the inaccurate Phase I
evidence record.

## Why Phase I's Evidence Was Wrong

Phase I recorded WARN as "binary missing" and "workspace not trusted". Both
were false:

- `codex` and `claude` were installed, but outside the PATH visible to the
  probing shell.
- The repository was already trusted
  (`trust_level = "trusted"` in `~/.codex/config.toml`).
- The real blocker was an outdated third-party Codex snap — 0.114.0, publisher
  `jcat-nysasounds`, against an official 0.147.0 — which predates
  `[features.multi_agent_v2]` and aborted with
  `invalid type: map, expected a boolean`.

Installing official Codex via npm let the matrix run for the first time.

## Work Log

Three defects found and fixed, each verified against real recorded output:

1. **Codex answer unreadable.** Codex returns the schema answer as JSON *text*
   in `item.completed -> item.text` (`agent_message`), not a nested object.
   `find_structured_observation` walked dicts only, so a correct answer scored
   `FAIL`. Now parses embedded JSON strings, keeping the exactly-one and
   sentinel-field rules.
2. **Claude prompt swallowed.** `--disallowedTools` is variadic and consumed
   the positional prompt; Claude exited 1 with `Input must be provided...`.
   Fixed with a `--` separator. Isolated flag by flag —
   `--no-session-persistence`, `--permission-mode`, and `--strict-mcp-config`
   were all innocent.
3. **Non-zero exit mislabelled as `untrusted`.** The probe asserted something
   untrue about the operator's environment. Non-zero now reports
   `invocation_failed`; `untrusted` is reserved for real preflight failure.

A fourth surfaced once Claude could run at all: it rejects the whole schema
with `no schema with key or ref "https://json-schema.org/draft/2020-12/schema"`.
The inline copy now drops `$schema`; the canonical file keeps it for Codex.

Each fix was proven non-vacuous by re-running the pre-fix logic against the
same input and confirming it failed.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short                               # 116 passed
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 19 files
uv run ruff check scripts/ tests/                                # PASS
uv run ruff format --check <changed Python files>                # PASS
uv run python scripts/generate_targets.py --all                  # PASS twice
uv run python scripts/validate_targets.py                        # PASS
git diff --cached --check                                        # PASS
```

## Native Evidence — Not A Full PASS

```text
claude  all measurable checks PASS, stable across runs
codex   all PASS except scoped_instruction_sentinel, which is
        non-deterministic: PASS on one run, FAIL on two
```

The generated Codex target has **no nested `AGENTS.md`** — Codex's native
scoped-instruction surface. The scoped policy exists only as
`.claude/instructions/*.instructions.md`, a Claude/Copilot surface. Codex is
asked whether it found something with no Codex-native representation, so it
answers inconsistently. Real finding, out of scope here.

`compact_resume` and `coder_escalation` remain hardcoded `WARN`
(`unexercised`): the first is never implemented, the second has no stable
client event to read. Left visible rather than scored as `PASS`.

Codex also needs a longer `--timeout` than the 120s default; one run timed out
because control and candidate execute consecutively.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T155215Z.json`
- Score: `.claude/quality_reports/score-20260808T155215Z.json`

## [LEARN] Entries

- [LEARN:testing] A probe that has never run against its real target is
  untested code with a reassuring name. Phase I passed every offline test and
  scored 100 while carrying three defects that its first real execution found
  immediately.
- [LEARN:testing] Mapping every non-zero exit to one diagnosis makes a tool
  assert things it did not measure. Classify the failure or stay silent.
- [LEARN:tooling] Verify client provenance and version before trusting any
  native result. A third-party repackage (snap `codex` 0.114.0 vs official
  0.147.0) presented as a config error in this repo.
- [LEARN:tooling] Variadic CLI options silently eat positional arguments; pass
  prompts after `--`.

## Open Questions / Next Steps

- Recommend a Phase K: decide whether the Codex target should emit nested
  `AGENTS.md` scoped instructions, or whether the probe should define
  "scoped instruction" per client. Until then `scoped_instruction` is not a
  trustworthy signal for Codex.
- `compact_resume`, `codex_role_matrix`, and `coder_escalation` remain
  unmeasured; the MultiAgent V2 removal gate is still unmet.
