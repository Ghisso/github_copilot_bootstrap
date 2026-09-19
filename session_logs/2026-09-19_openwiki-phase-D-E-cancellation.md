# OpenWiki Phases D and E: Cancellation

**Status:** CANCELLED
**Plans:** `.claude/plans/2026-09-19_phase-D-openwiki-dogfood-migration-and-closeout.md`,
`.claude/plans/2026-09-19_phase-E-openwiki-child-process-sandbox.md`

Both phases were written against a native-CLI model of OpenWiki 0.5.2 (a bootstrap-spawned
`openwiki code --update --print` child process). Verification against the installed package
showed the repository will use host-driven mode (MCP tools called by the coding agent; no
child process; no provider credentials). Four defects made patching unsafe: the runner cannot
pass its own preflight (`openwiki --version` does not exist), three committed rules forbade the
host integrations that host-driven mode requires, the bootstrap skill occupies the paths
OpenWiki's integration installs to (`.claude/skills/openwiki`, `.agents/skills/openwiki`), and the
safety boundary assumed a subprocess. Replaced by phases F, G, H, I, J, K of the same big plan.

## Evidence

Verified against `openwiki@0.5.2` as installed, not from documentation:

- `openwiki --version` exits 1 with `Unknown option: --version`. The Phase A runner's preflight
  calls exactly that, so it reports `required command unavailable: openwiki` and can never run.
- `shared/devcontainer/Dockerfile` ends its install chain with `&& openwiki --version`, so the
  image build fails at that line. `scripts/validate_targets.py` asserts that exact string, so the
  validator enforced the defect. Phase A's own plan required a real smoke check; its session log
  records the build was never run.
- `openwiki integrations install claude --project .` writes `.claude/skills/openwiki/` and an
  `.mcp.json` entry; the Codex variant writes `.agents/skills/openwiki` and `.codex/config.toml`.
  Both collide with the bootstrap skill. The installer refuses rather than clobbering.
- `openwiki_begin` reaches `ensureCodeModeRepoSetup` through
  `dist/integrations/core/session-manager.js` and `dist/generation/repository-run.js:51`, so
  host-driven runs still rewrite the root adapters. Insertion uses `trimEnd()`, so a block strip
  is not byte-exact and a pre-run snapshot is required.

## Why this was not caught earlier

Phase A passed nine review rounds. Every one examined the diff and the deterministic tests, and
every test used a fake `openwiki` executable that answered `--version`. Nobody ran the real
binary. Review depth cannot substitute for one real invocation of the thing being wrapped.
