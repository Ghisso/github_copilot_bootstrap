# Planner change log for the devil's advocate review (2026-11-12)

## Change log: devil's advocate items

I checked every item against the code before acting on it.

- **C1. Confirmed; decision 4 rewritten.**
  - `scripts/generate_targets.py:1218` gives Codex SessionStart the matcher `startup|resume|clear`. The Codex `compact` fixture is synthetic (`tests/fixtures/context_mode_hook/capture.py:168-170`).
  - Claude's compaction text is dropped because of the plugin prefix. Copilot's arrives only through UserPromptSubmit, which is not wired.
  - So, as wired, 2.x forwards nothing to any client. MCP-only is now the recommendation.
  - Spike S5 checks whether Codex emits `compact` at all.
- **C2. Confirmed.** `shared/hooks/hooks.json:98-117` has no matcher, so Copilot PostToolUse runs on every tool. I fixed the wording in the "narrow" re-plan note. MCP-only makes this moot.
- **C3. Adopted.**
  - The gate now uses pass/fail commands, and the circular "Phase A" item is gone (P1).
  - I replaced `git merge-base --is-ancestor <branch> dev` with content checks on `dev` (`git show dev:README.md`, `git show dev:openwiki/...`). These still work after the branch ref is deleted.
  - I dropped the CUDA image check, because the full build is now optional (Q4).
- **C4. Confirmed and extended.**
  - `install_bootstrap.py:560-571` and `runtime_ownership.py:21-29` keep tracked `.mcp.json`, `.codex`, `.agents`, and `.vscode/mcp.json` on refresh.
  - The plan now uses one server identity (P5), so no adapter changes. Phase A's verification checks that the root adapters are unchanged.
  - The per-client fallback is decision 7.
  - Extension: a committed `.codex/` also keeps stale Codex hook entries. Phase A therefore makes any legacy hook call a silent exit 0.
- **C5. Confirmed.**
  - The race test (`tests/test_context_mode_mcp_filter.py:285-318`) now races `ctx_stats`.
  - The name lists at :106, :184-193, :281, and :317 are updated, and `:550 ALLOWED_CTX_TOOLS` is deleted with the hook tests.
  - The shared-`ALLOWED_TOOLS` concern for `sanitizeHookOutput` disappears with MCP-only. The narrow re-plan note keeps it.
- **C6. Confirmed.** R-CODEX-01 appears at :3060, :3124, and :3155. The plan deletes only :3155-3160 and edits `expected_codex_events` at :3137-3145. The `runtime-checks.md` reference is now 933-934.
- **C7. Adopted both parts.**
  - A test for an old-pin cache with the correct secret.
  - A fix for the quarantine `mv` race, with a deterministic fake-`mv` test.
  - With MCP-only, the race is between two MCP servers (two clients at once), not between a hook and a server.
- **C8. Resolved by P1.** The spike output goes to a dated `.claude/explorations/<run-date>_context-mode-2x-recheck/`. There is no `docs/` note.
- **C9. Resolved by P1.** There is no spike phase, so there is no spike verification block.
- **C10. Adopted.**
  - A `#` comment line now sits above every item that needs network, Docker, or a prepared binary.
  - I corrected the Docker cache claim: `COPY --from=ghcr.io/astral-sh/uv:latest` re-resolves on every build, and later layers rebuild when that tag moves. The full build is now optional anyway.
- **C11. Adopted.**
  - Whole-file `ctx_doctor` absence check.
  - `four guarded` absence check across the surfaces.
  - A self-install check (now: no `context-mode-dispatch.sh` in any hook file).
  - Docs-plus-root-guidance `1.0.169` check in Phase B.
  - I also removed the Dockerfile pin grep, because the validator already ties the pins together.
- **C12. Adopted.** `--ignore-scripts` on the private-prefix install.
- **C13. Adopted.** An optional `npx`-route item, and spike S6 reads the newest v24 from `https://nodejs.org/dist/index.json`.
- **C14. Adopted.** Phase B adds a rollback note. The mechanism: the old dispatcher moves the 2.x cache aside on its first run and never restores the 1.x folder by itself.
- **P1. Adopted.** The pre-branch spike is a section of the big plan. Phases are re-lettered A to C.
- **P2. Adopted.** The Node.js floor is checked in server mode and `--self-check` only. Legacy hook calls run no Node.js check.
- **P3. Adopted.** MCP-only is recommended, and the phases are written for it.
- **P4. Adopted on the merits.**
  - Both changes edit the same files: generator, validator, filter, dispatcher, tests, and docs.
  - Five agent prompts, the routing policy, and the generator's root guidance each hold the single sentence "exactly four guarded MCP tools (...) alongside its lifecycle hooks". Both changes rewrite that one sentence.
  - Both run on 1.0.169, and merging saves one seven-profile review cycle.
- **P5. Adopted as spike S2.** The phases are written for one server identity. The per-client fallback is in the re-plan notes and decision 7.
- **Q1.** Folded into decision 4.
- **Q2.** New decision 7: server identity and committed MCP adapters.
- **Q3.** Folded into decision 1: the pre-branch spike is recommended.
- **Q4.** Folded into decision 5. The full CUDA build becomes Optional Verification. A required check stays: the chosen Node.js image meets the 24.15 floor and runs the pinned 2.x. This is the recommendation.

**Other notes:**

- I re-ran the exact `HEDGED_VERIFICATION_PATTERNS` from `scripts/validate_plan_frontmatter.py` over all new small-plan prose: 0 hits.
- I still could not run the plan validator on the drafts, because the Bash guard blocks commands that name the protected MCP files. Please run `uv run python scripts/validate_plan_frontmatter.py` on the saved files.
- The tokens `PIN_FROM_SPIKE`, `NODE_IMAGE_FROM_SPIKE`, and `AGENT_FROM_SPIKE` appear only in prose. Verification commands read the pin, image, and identity from source instead. The start gate fails while any token remains.

**Files to save:**

- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/context-mode-2x-migration.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-12_phase-A-context-mode-mcp-only-surface.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-12_phase-B-context-mode-2x-switch.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-12_phase-C-knowledge-refresh.md`

The earlier five-phase files are superseded. Do not save them.

---

