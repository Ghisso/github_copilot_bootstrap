# Session: OpenWiki Phase I — enable and first generation

**Date:** 2026-09-21
**Plan:** `.claude/plans/2026-09-19_phase-I-openwiki-enable-and-first-generation.md`
**Status:** COMPLETED

This is a transition phase, not the template for future knowledge-refresh
phases. It enables OpenWiki in this checkout for the first time and proves
one host-driven generation; later refreshes follow the small
knowledge-refresh shape in `workflow.instructions.md`.

## Goal

Enable OpenWiki for `github_copilot_bootstrap`: write the brief and ignore
file, install the Claude Code and Codex integrations once, re-probe the guard
against the real server, run one host-driven `update` from a Claude Code
session, and commit. Stop there; the user inspects `openwiki/**` before
Phase J.

## Work Log

- Phase started 2026-09-21 after Phase H's completion commit `cf6c4ac`.
- Plan pre-check against the installed `openwiki@0.5.2` package: the
  `.openwikiignore` file is honored (`dist/agent/openwiki-ignore.js`);
  `/openwiki/INSTRUCTIONS.md` is read as the user-authored brief and never
  rewritten by routine runs; the integration installer writes the `.mcp.json`
  entry `{"command":"openwiki","args":["mcp","--host","claude"]}`, an
  `# OPENWIKI:MCP:START … END` block in the Codex config, and skill bundles
  with `.openwiki-install.json` markers under `.claude/skills/openwiki` and
  `.agents/skills/openwiki`; `openwiki/.run.json` was already ignored by
  `.gitignore:38`. All plan facts held.
- Plan correction before IMPLEMENT: Steps I3 and I4 call OpenWiki's MCP
  tools. The `coder` agent's tool list has no OpenWiki server, and a running
  Claude Code session does not discover a server added to `.mcp.json`, so
  both steps are owned by the orchestrator on the main thread in a session
  started after Step I2, once the user approves the project server.
- Step I1 (Phase H coder reused): created `openwiki/INSTRUCTIONS.md` (the
  four-way split of authoring `shared/`, generated `dist/multi-agent/`, a
  consumer's outer repository, and the nested `.claude` ai-state repository;
  priorities; the rule that `.claude/plans/`, `.claude/session_logs/`,
  `docs/2026-*`, and root `plans/` are historical evidence, not current
  behaviour) and `.openwikiignore` (excludes `dist/`, `.claude/`, `.codex/`,
  `.agents/`, `.github/hooks/`, `.devcontainer/` (an untracked self-install
  overlay here), root `/AGENTS.md` and `/CLAUDE.md`, caches, the
  context-mode provenance secret, and Python build output; keeps source,
  tests, undated docs, and `openwiki/` itself). Ignore syntax confirmed
  gitignore-compatible with one difference: OpenWiki matches
  case-insensitively by design. `verify.py fast` PASS.
- Step I2: `openwiki integrations install claude --project .` and
  `... codex --project .` both exit 0 with no unmanaged-skill warning (the
  Phase H rename freed both paths). `openwiki integrations list --project .`
  reports `installed` for `claude` and `codex`. Diffs are exactly the
  additions the plan names; `semble` and `context-mode` entries untouched;
  no `*openwiki-backup*` directory; both bundles carry
  `.openwiki-install.json`; `check_runtime.py` exit 0 (Phase G exemption
  held); `validate_targets.py` exit 0; the installer did not touch
  `AGENTS.md`/`CLAUDE.md`.
- Discovery after Step I2 (recorded as Step I2b in the plan): the self
  overlay refresh `install_bootstrap.py . --local-only --allow-self` exits 1
  with `Refusing .agents takeover ... .claude/bootstrap-root/.agents/skills/openwiki ...`.
  No such mirror directory exists; `_agents_conflicts` labels every
  difference with the mirror prefix, and the difference is OpenWiki's
  marker-claimed live bundle, which `_agents_tree` walks without consulting
  `is_third_party_skill_dir`. `verify.py fast` fails with
  `receipt metadata control-plane provenance is invalid` because the live
  root adapters OpenWiki's installer edited no longer match their
  `.claude/bootstrap-root/` mirror. Phase G exempted the bundles from
  `check_runtime.py` drift only. Step I2b fixes the installer (and the
  verifier's fingerprint if `.agents` is an owned path) with regression
  tests; `ponytail` added to the review profiles.
- Step I2b (same coder): `_agents_tree` in `scripts/install_bootstrap.py`
  now prunes a marker-claimed third-party skill directory from its walk, so
  the takeover and mirror comparisons never see it; a same-shaped directory
  without the marker still surfaces as a conflict. `.agents` is an owned
  root adapter path (`ROOT_ADAPTER_PATHS`), so
  `regular_tree_fingerprint_diagnostic` in `shared/scripts/verify.py` now
  excludes marker-claimed bundles and everything under them on both the live
  and mirror sides, through the file's existing dynamic import of
  `runtime_ownership.py`. Four regression tests added (two per file). The
  refresh then exits 0, leaves `.agents/skills/openwiki/**` untouched, and
  keeps OpenWiki's entries in both MCP config files; nested state was
  committed by the refresh as `bootstrap: update 2026-09-21T02:27:59Z`.
  Focused pytest 353 passed; generate, validate, `check_runtime`, `verify.py
  fast`, mypy, ruff all exit 0.
- Stop for the user: the session must restart so Claude Code discovers the
  `openwiki` MCP server and OpenWiki's installed `openwiki` skill; the user
  approves the project server. Steps I3 and I4 resume on the main thread.
- Session restarted 2026-09-21. The `openwiki` MCP server was discovered from
  `.mcp.json` and its six tools became callable with no approval prompt (the
  plan and skill expected one; Claude Code did not ask in this session).
  Both `knowledge-refresh` and OpenWiki's installed `openwiki` skill loaded.
- Step I3, guard re-probe on Claude Code (spike outcome O1), main thread:
  (1) `openwiki_begin` with `mode: "init"` was denied before the tool ran
  with `openwiki-guard: mode="init" replaces the wiki and is denied; only
  mode="update" is allowed through this guard`; (2) with
  `openwiki/INSTRUCTIONS.md` renamed to `INSTRUCTIONS.md.probe`,
  `openwiki_begin` with `mode: "update"` was denied with `openwiki-guard:
  openwiki/INSTRUCTIONS.md is missing; install OpenWiki before running
  openwiki_begin`; marker restored; (3) snapshot directory
  `.claude/.cache/openwiki-guard/` absent, `git status --porcelain --
  AGENTS.md CLAUDE.md` empty, no `openwiki-update.yml`. All three match the
  spike. Note: `protect-files.sh` denied one compound probe command that
  named `.github/workflows` and `|| true`; the probe was rerun as separate
  commands.
- Step I4, first host-driven generation, main thread. Tool-call sequence:
  `openwiki_begin(root=/home/ghisso/work/github_copilot_bootstrap,
  mode=update)` returned `status: active`, `phase: planning`, `language: en`,
  `lastUpdate: null` — `update` on an empty wiki performed a first
  generation, no `noop`, no refusal. Adapters clean and snapshot directory
  empty immediately after; `openwiki/.run.json` and `.last-update.json`
  created, `.run.json` git-ignored. `openwiki_submit_plan` with 8 pages
  (accepted): `architecture/source-generated-consumer-layout`,
  `workflows/lifecycle-and-task-lanes`, `architecture/agents-and-skills`,
  `architecture/hooks-and-guardrails`, `operations/deterministic-verification`,
  `operations/install-ownership-and-runtime-checks`,
  `operations/git-backed-ai-state-sync`, `quickstart`. The queue was
  served in alphabetical path order, not plan order; quickstart still came
  last. Eight `openwiki_next_page` / write / `openwiki_submit_page` cycles,
  each page researched from source on the main thread (OpenWiki's skill
  forbids page subagents); two submissions were rejected once and
  resubmitted: evidence may not cite `openwiki/INSTRUCTIONS.md` (generated
  OpenWiki output) nor `AGENTS.md`/`CLAUDE.md` (excluded by
  `.openwikiignore`), so those claims cite `README.md` and the generator
  string instead. `openwiki_next_page` returned `status: complete`;
  `openwiki_finish` returned `status: complete`. OpenWiki added `verified:`
  frontmatter to every page and wrote `index.md` files, `.claims/`,
  `.page-manifest.json`, and `.last-update.json`; `.run.json` was removed.
- Step I4 acceptance: adapters byte-identical (porcelain empty), no
  workflow file, changes confined to `openwiki/**` plus the Steps I1/I2/I2b
  files, `.claims/`, `.last-update.json`, `.page-manifest.json` present,
  `.run.json` absent, a grep for secret-like or AI-state content in the pages
  matched only the words "tokens" and the `.context-mode-provenance.secret*`
  filename. `verify.py phase --format text` PASS: ruff 0, mypy 0, pytest
  1759 passed, `VFY-GEN-001` PASS (OpenWiki managed-state conditions clean).
  Eight pages, 1474 lines total.

## Review findings and dispositions

One round (profiles `code`, `architecture`, `security`, `tests`,
`documentation`, `ponytail`; two sequential passes, converged after round
2): 0 CRITICAL, 0 MAJOR, 0 MINOR. Gate PASS.

- Confirmed: both MCP config files gained exactly OpenWiki's managed entries
  and nothing else changed; no credential, private config, or AI-state
  content in `openwiki/**` or `.openwikiignore`; the brief subordinates
  generated content to source, tests, and policy and marks archived records
  as historical.
- Generated pages: three to six concrete claims per page were checked against
  the cited source (agent roster and delegates, `prompt_base` derivations,
  skill counts, `run-hook.sh` root resolution, guard wiring, the
  `git-protection.sh` denial list, `protect-files.py` per-host decisions,
  renderer order, MCP server definitions, the seven `VFY-*` ids, `gate`
  flags, the `state-sync.sh` dispatch table, the installer sequence, and the
  L1 to L4 lint codes); none contradicted the code; terminology is
  consistent and matches the repository's own vocabulary.
- Considered and dropped: whether the shape-only `skills/openwiki` match lets
  a planted marker hide content under another root adapter directory. It is
  the same rule Phase G established for `check_runtime.py`, needs filesystem
  write access that already permits more direct tampering, and matches the
  plan's acceptance bar, so it is not an actionable finding.
- Held up: the four new tests fail if either exemption is removed or
  broadened to shape-only; both code changes are the smallest correct fix
  and reuse the existing `is_third_party_skill_dir` helper.

## [LEARN] Entries

- [LEARN:workflow] An ownership rule added to one checker must reach every
  reader of the same ownership contract. Phase G exempted OpenWiki's
  marker-claimed skill bundle from `check_runtime.py` drift only; the
  installer's `.agents` takeover check and the verifier's bootstrap-root
  fingerprint read the same facts and broke the first time the bundle
  existed. When adding an ownership category to `runtime_ownership.py`,
  grep for every consumer of that module and apply the rule in each.
- [LEARN:planning] A step that calls a project MCP server needs a session
  boundary in the plan: a running Claude Code session does not discover a
  server added to `.mcp.json`, and the `coder` and `reviewer` agents' tool
  lists exclude project MCP servers, so such steps run on the main thread in
  a session started after the server is configured.
- [LEARN:tooling] OpenWiki 0.5.2 facts observed here: `mode: "update"` on an
  empty wiki performs a first generation; the page queue is served in
  alphabetical path order regardless of plan order; `openwiki_submit_page`
  rejects evidence that cites `.openwikiignore`-excluded files (here
  `AGENTS.md`, `CLAUDE.md`) or generated OpenWiki output (including
  `openwiki/INSTRUCTIONS.md`), so cite the generator string or README for
  root-guidance facts; Claude Code discovered the new server without an
  approval prompt in this session.
- [LEARN:workflow] `protect-files.sh` denies a compound Bash command that
  merely names a protected path in read-only context (a heredoc mentioning
  the Codex config file, a `find .github -name openwiki*` chained with
  `|| true`). Split such commands into simple ones or use the Edit tool;
  do not weaken the hook.

## Verification

```text
PASS        1.2s  openwiki integrations list --project .
PASS       29.8s  uv run pytest tests/test_install_bootstrap.py tests/test_verify.py -q --tb=short
PASS        1.2s  uv run python scripts/check_runtime.py
PASS        0.3s  uv run python .claude/scripts/verify.py fast --format json
PASS      119.8s  uv run python .claude/scripts/verify.py phase --format json --persist
closeout: PASS
```

Receipts under `.claude/quality_reports/`: phase receipt (`VFY-RUFF-001`,
`VFY-MYPY-001`, `VFY-PYTEST-001` 1759 passed, `VFY-FRESH-001/002`,
`VFY-GEN-001` all PASS) and the closeout receipt persisted after this log
was checkpointed, with `--documentation-na` because the plan forbids manual
documentation changes in this transition phase and the code change is a
pure-internal ownership fix covered by tests. Findings report:
`.claude/quality_reports/findings-2026-09-19_phase-I-openwiki-enable-and-first-generation.json`
(0 findings, six profiles, `ponytail_reviewed=true`). Staged: the two MCP
config files, `.openwikiignore`, `openwiki/**` (30 files, `.run.json` not
staged), the installer, verifier, and two test files.

- optional 1: NOT RUN — no Codex session was available in this phase; the Codex re-probe of the guard stays optional per the plan and can be run in Phase K.

## Open Questions / Next Steps

- **Stop.** Per the plan, Phase J
  (`2026-09-19_phase-J-openwiki-docs-memory-migration`) starts only after
  the user inspects `openwiki/**` and confirms in writing; that confirmation
  is recorded in Phase J's session log.
- Follow-ups carried: the Codex re-probe of the guard (optional here, can run
  in Phase K); `verify closeout` traceback when the findings report is
  missing (MINOR, from Phase F2); the overlay refresh removing the nested
  `.claude/.gitignore` that `state-sync.sh` recreates.
- Observed: Claude Code discovered the `openwiki` project MCP server without
  an approval prompt in this session. The `knowledge-refresh` skill's
  enablement step 3 says to approve it when asked; that wording still holds
  (approve if asked) and needs no change.
