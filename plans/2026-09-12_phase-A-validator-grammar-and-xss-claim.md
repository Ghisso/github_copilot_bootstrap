---
name: 2026-09-12_phase-A-validator-grammar-and-xss-claim
type: small-plan
parent_plan: 2026-09-12_validator-grammar-and-xss-claim
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-09-12_validator-grammar-and-xss-claim.md
---
# Small Plan: 2026-09-12_phase-A-validator-grammar-and-xss-claim

## Scope

Correct the seven verified defects the post-merge review found in
`2026-09-12_skill-library-hardening`. Each corresponds to a numbered row in
the big plan's `## Verified audit evidence` table, and each was reproduced
against the current `dev` before planning. Re-read every cited line before
editing, because line numbers drift.

This is the only phase in its big plan, so it also runs the documentation,
memory, LEARN, and stale-claims audit that `verify.py`'s closeout gate
requires.

This is control-plane work: it changes `scripts/validate_targets.py`. Required
review profiles: `code`, `architecture`, `security`, `tests`, `ponytail`.

All edits go to canonical `shared/**`, `scripts/`, `docs/`, and `tests/`
sources. Generated targets come from `scripts/generate_targets.py --all`;
never hand-edit a generated copy. Do not touch
`shared/skills/ponytail/SKILL.md`, `ponytail-review/SKILL.md`, or
`humanize/SKILL.md` — they are hash-pinned and any byte change fails the
build.

## Steps

- [ ] **Correct the pyvis escaping attribution (evidence row 1).**
  - Modify `shared/skills/pyvis-xss-testing/SKILL.md` around line 63.
  - The comment currently reads "vis.js renders `title` via innerHTML — the
    real XSS sink — so pyvis HTML-escapes it before JSON-encoding it". The
    second clause is false and security-relevant: a reader can conclude pyvis
    is safe by default for `title` and skip the escaping their own code must
    do, producing a DOM XSS through that same sink.
  - Verified against pyvis upstream: `pyvis/node.py` and `pyvis/network.py`
    contain no escape, markupsafe, bleach, or sanitize call;
    `pyvis/templates/template.html:434` serializes with Jinja2
    `{{nodes|tojson}}`; `:506` assigns `popup.innerHTML = nodeData[0].title`.
    Jinja2's `tojson` escapes `<` to `<` so the value is safe inside a
    `<script>` block, and the browser's JavaScript parser decodes it back to
    `<` before it reaches `innerHTML`. That is JavaScript-source escaping, not
    HTML escaping.
  - State that the calling application must HTML-escape `title` before
    handing it to pyvis, and that pyvis escapes neither `title` nor `label`.
  - Do not change the assertion itself. `json.loads(...) == escape(title_text)`
    correctly tests that the application escaped; only the rationale is wrong.
  - Keep the correct surrounding facts: `title` is an `innerHTML` sink,
    `label` is canvas-rendered by default and is not an HTML sink, and the
    `<` double-encoded form is what `tojson` produces from an
    already-escaped string.
  - Re-read the whole file afterwards and confirm it no longer contradicts
    itself. It already states elsewhere that asserting on `html.escape()`
    directly "tests the standard library, not your escaping logic", which only
    makes sense if the application does the escaping.

- [ ] **Normalize YAML scalars in the frontmatter gate (evidence rows 2-4).**
  - Modify `scripts/validate_targets.py`.
  - Add one small helper that turns a raw frontmatter value into its YAML
    scalar: strip surrounding matched quotes (both `"` and `'`) and a trailing
    `#` comment, then strip whitespace. Keep it a helper rather than inlining
    it twice, so the two call sites cannot drift.
  - `extract_frontmatter_name` (around lines 7958-7962) must use it, so
    `name: "example"`, `name: 'example'`, and `name: example  # note` all
    resolve to `example`.
  - The visibility check (around lines 8177-8182) currently substring-matches
    `"\nvisibility: public"`. Replace it with a normalized value comparison
    against the recognized set, so `visibility: "public"` is accepted.
  - Do not add a YAML dependency or write a general parser. The repository
    deliberately hand-parses this flat schema, mirroring
    `generate_targets.parse_policy`.
  - Leave `scripts/validate_targets.py:7547` alone. It substring-matches
    `visibility: public` as part of the hash-pin check for the vendored
    Ponytail pair; those files are byte-frozen and unquoted, so the limitation
    is unreachable there and changing a pin check would be churn.
  - Note that `extract_frontmatter_description` already strips quotes
    correctly. The new helper should make `name` consistent with it, not
    duplicate a second normalization style.

- [ ] **Recognize angle-bracket placeholder paths (evidence row 5).**
  - Modify the placeholder handling in `skill_local_reference_errors`
    (around lines 8029-8060).
  - `shared/skills/[skill-name]/SKILL.md` is skipped as a placeholder but
    `shared/skills/<your-skill>/SKILL.md` is rejected, which is uneven for a
    reader who uses a different placeholder convention.
  - Add `<` and `>` to the recognized placeholder markers alongside `**` and
    `[...]`.
  - Do not otherwise weaken the rule: a concrete path that names a known
    repository root and does not resolve must still fail. Confirm that
    `scripts/validate_skills.py`, a file this repository deliberately never
    created, is still rejected when referenced.

- [ ] **Align the contract documentation with real behavior (evidence row 6).**
  - Modify `docs/architecture.md` around lines 68-80.
  - It currently says frontmatter must be "well-formed YAML in the flat
    schema every skill already uses". After this phase the gate accepts
    quoted scalars and trailing comments, but still rejects tabs anywhere in
    frontmatter, which YAML permits inside scalar content.
  - Describe the grammar the gate actually enforces, and say plainly that the
    tab prohibition is a house rule rather than a YAML requirement.
  - State that `name` and `visibility` are compared as normalized scalars, so
    quoting style does not change the result.

- [ ] **Delete the stale wrapping note (evidence row 7).**
  - Modify `shared/third_party/ponytail/UPSTREAM.md`, removing the paragraph
    at lines 35-38 that calls the preceding paragraph's line wrapping
    load-bearing.
  - That was true when written and is now false: the Phase C change normalized
    whitespace in both provenance checks.
  - Change prose only. The release, commit, import date, and all three
    allowlist hashes must not change, and `validate_targets.py` must still
    pass. Confirm the two provenance checks still pass after the edit.

- [ ] **Add regression tests for every newly accepted form.**
  - Extend `tests/test_validate_targets.py`, following its existing fixture
    patterns. Keep it the pytest entrypoint for the validator suite.
  - Cover, parametrized where natural:
    - `name` double-quoted, single-quoted, with a trailing comment, and bare;
    - `visibility` double-quoted, single-quoted, and bare, for both `public`
      and `background`;
    - an angle-bracket placeholder path accepted, and a concrete unresolvable
      path still rejected;
    - the existing behavior that must not regress: duplicate descriptions
      rejected, key-like text inside a block scalar accepted, a URL ending in
      `.md` not treated as a repository reference.
  - **Prove each new test fails against the pre-change code for the intended
    reason.** Extract the current functions to a scratch copy and run the new
    assertions against them; do not assume. A test that passes both before and
    after pins nothing.
  - Add a test asserting `pyvis-xss-testing/SKILL.md` no longer claims pyvis
    performs the escaping. This is a textual assertion about prose — label it
    as such in the docstring and do not describe it as proving runtime
    behavior.

- [ ] **Regenerate, validate, and run the stale-claims audit.**
  - Run `scripts/generate_targets.py --all`, then the validators, then
    `install_bootstrap.py . --allow-self --local-only` to refresh this
    repository's own runtime copies, then `check_runtime.py`.
  - Sweep every live-advice surface for claims this phase invalidates: root
    guidance, `docs/`, shared policies, shared skills, shared templates,
    shared agents and review profiles, state READMEs, and `.claude/MEMORY.md`.
  - Pay specific attention to anything else describing the frontmatter gate's
    grammar, and to `shared/templates/skill-template.md`, which teaches the
    frontmatter shape and should stay consistent with whatever the gate now
    accepts.
  - Record every audited surface and its outcome under the exact heading
    `## Stale-claims surfaces checked` in the closeout session log.

## Verification

Generation before validation; read every exit status from the command itself,
never through a pipe:

```bash
uv run python .claude/scripts/verify.py fast --format text     # during IMPLEMENT
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format json --persist
```

Verification must specifically demonstrate:

- `name` and `visibility` accept bare, double-quoted, and single-quoted
  scalars, and `name` accepts a trailing comment;
- an angle-bracket placeholder path is accepted while a concrete unresolvable
  path is still rejected;
- `pyvis-xss-testing/SKILL.md` no longer attributes the escaping to pyvis;
- the two Ponytail provenance checks still pass after the note is deleted, and
  all three allowlist hashes are unchanged;
- every new test fails against the pre-change code for the intended reason.

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Closeout session log contains non-empty `## Stale-claims surfaces checked`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
- [ ] Vendored Ponytail and `humanize` files unchanged and pinned hashes still match
- [ ] Big plan marked complete only after the completion commit, never before

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume
later. Set `status: paused`, record the three pause fields, and create a
session log with `**Status:** PAUSED`. A checkpoint preserves incomplete work
and does not complete or advance the phase.
