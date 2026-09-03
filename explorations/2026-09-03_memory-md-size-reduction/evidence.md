# Exploration — Reducing `.claude/MEMORY.md` Session Cost

**Date:** 2026-09-03
**Status:** OPEN — paused for a later decision by the user
**Trigger:** after `verification-gate-semantic-hardening` closed (7 phases,
commits `2af3df7`…`d2d0847`), the user observed that `.claude/MEMORY.md` and
its LEARN entries "got too big now" and asked for compression.

**Outcome so far:** stylistic compression was attempted and delivered **1.2%**.
That route is exhausted. Two real levers remain, both requiring a user
decision. Nothing further was changed.

---

## 1. Read this first — what a future agent does NOT need to redo

Every number below was measured, not estimated. The exact commands are
included so they can be re-run, but **re-running them is not necessary to
resume**; they are here for verification if the file has since changed.

Three conclusions are settled and should not be re-litigated:

1. **`.claude/MEMORY.md` contains no padding to remove.** Stylistic
   compression is not the lever. Measured, see §3.
2. **There is no redundancy to deduplicate.** Zero near-duplicate entry pairs.
   Measured, see §2.
3. **An ad-hoc file at the top level of `.claude/` is not durable** — the
   installer deletes it as an obsolete owned file. This kills the naive
   "put the archive next to MEMORY.md" plan. Measured, see §5.

---

## 2. Baseline measurements

As of 2026-09-03, after the 1.2% compression in §3 had been applied:

| Metric | Value |
|---|---|
| Lines | 717 |
| Bytes | 49,455 |
| Approx tokens (bytes / 4) | ~12,360 |
| `[LEARN:...]` entries | 171 |
| Entry-body words | 6,468 |
| Median words per entry | 35 |
| Longest entry | 167 words |
| Headings | only `## Domain-Specific` and `## Workflow` |

Pre-compression baseline for reference: 718 lines, 50,051 bytes, ~12,510
tokens, 7,348 words.

Category spread across the 171 entries:

`testing` 31, `security` 28, `workflow` 22, `verification` 20,
`architecture` 14, `quality` 7, `tooling` 7, `review` 7, `documentation` 6,
`tests` 6, `installer` 5, `domain` 3, `code` 3, then a tail of 1–2 each
(`runtime`, `codex`, `config`, `recovery`, `shell`, `diagnostics`,
`observability`, `planning`).

Note `tests` and `testing` are separate labels for the same concept, and
`code`/`quality` overlap — a label cleanup is a small, separate opportunity.

**Redundancy check — the important negative result.** A crude near-duplicate
scan over content words (tokens of 5+ letters, pairwise overlap against the
smaller entry's key set) found **zero pairs above 0.55 overlap**. Every one of
the 171 entries is a genuinely distinct lesson. Command:

```bash
uv run python - <<'PY'
import re, collections, pathlib
text = pathlib.Path(".claude/MEMORY.md").read_text()
entries = re.findall(r"^- \[LEARN:?([a-z]*)\][ \t]*(.+?)(?=\n- \[LEARN|\n## |\Z)", text, re.S | re.M)
print("entries:", len(entries))
print("by category:", dict(collections.Counter(c or "(none)" for c, _ in entries).most_common()))
lens = sorted(len(b.split()) for _, b in entries)
print("words: median", lens[len(lens)//2], "max", lens[-1], "total", sum(lens))
def keyset(s): return set(w.lower() for w in re.findall(r"[A-Za-z_]{5,}", s))
pairs = []
for i in range(len(entries)):
    for j in range(i+1, len(entries)):
        a, b = keyset(entries[i][1]), keyset(entries[j][1])
        if a and b and len(a & b) / min(len(a), len(b)) > 0.55:
            pairs.append((entries[i][1][:60], entries[j][1][:60]))
print("near-duplicate pairs:", len(pairs))
PY
```

---

## 3. What was already tried: stylistic compression (1.2%, exhausted)

Used the repo's own purpose-built skill,
`.claude/skills/caveman-compress/SKILL.md`, whose documented trigger is
literally "compress this memory file".

Flow: detector accepts the target (`Type: natural_language`,
`Compressible: yes`) → back up to `<stem>.original.md` → rewrite prose only →
validate.

**Result: 596 bytes saved of 50,051 — 1.2%.** Entry count unchanged at 171.
Validator returned `Valid: True`, zero errors, one harmless warning (a
stray-space typo fix, `browser/ editor` → `browser/editor`, made the naive
path regex see a new path-shaped token).

**Why so little — this is the key finding.** The file was already written
tight:

- **Zero** occurrences of common padding phrases ("in order to", "the fact
  that", "due to the fact", "is able to", "as a result of").
- Only ~42 filler adverbs (already/also/still/just/actually/exactly/
  genuinely) across 7,348 words — an unusually low rate.
- Only 5.9% of words sit inside protected inline-code spans, but much of the
  *remaining* prose is still load-bearing: exact paths, version numbers,
  config keys, quoted error strings, plain-text identifiers.

About 40 targeted edits plus a safe contraction pass (`does not`→`doesn't`
etc., verified none inside backticks) were all the slack that existed.
Roughly 130 of the 171 entries were left untouched because every remaining
word was either a required token or the reasoning clause itself.

**Do not retry this route.** It is done, and the ceiling is ~1%.

### Validator constraints that shape any future attempt

`.claude/skills/caveman-compress/scripts/validate.py` treats these as **hard
errors** (must be byte-identical between backup and result):

- YAML frontmatter
- Markdown heading text and order
- fenced code blocks
- **inline code spans** — extracted as a *list*, so order and multiplicity
  matter
- URLs
- Markdown table structure

And these as **warnings** only: file paths changed; bullet count changed by
more than 15%.

The inline-code equality check is the operative constraint: **merging or
deleting an entry removes inline-code spans and is therefore a hard error.**
The skill is built for rewording while preserving every technical token, and
cannot express curation. Adding section headings is also a hard error, so the
file cannot be reorganized under this skill.

---

## 4. The two remaining levers, with measured sizes

### Lever A — Curation (retire entries that no longer earn their cost)

Measured on the 171 entries / 6,468 words:

| Set | Entries | Words | Share of entry prose |
|---|---|---|---|
| Failure mode now mechanically prevented by a gate | 18 | 934 | 14% |
| Tied to a single historical incident in shipped work | 8 | 338 | 5% |
| Overlap between the two sets | 0 | — | — |
| **Union if both retired** | **26** | **~1,272** | **~20%** |

That is roughly 1,700 tokens per session.

The argument *for* retiring the gate-enforced 18: this plan's entire
philosophy is that a deterministic gate supersedes agent-authored guidance. A
lesson whose failure is now impossible is redundant with the code enforcing
it, and the prose costs context every session forever.

The argument *against*: such a lesson also explains *why* the gate exists,
which is what stops a future agent removing it. Consider keeping a one-line
stub pointing at the enforcing mechanism instead of deleting outright.

Detection heuristics used (these are heuristics, not a curated list — a human
or agent should review the actual 26 before retiring any):

```bash
uv run python - <<'PY'
import re, pathlib
text = pathlib.Path(".claude/MEMORY.md").read_text()
entries = re.findall(r"^- \[LEARN:?([a-z]*)\][ \t]*(.+?)(?=\n- \[LEARN|\n## |\Z)", text, re.S | re.M)
gate = ("verify.py","validate_targets","validate_plan_frontmatter","commit gate",
        "closeout_log_errors","CHECK_IDS","record_findings","VFY-","historical_chain",
        "is_final_phase","phase receipt","closeout receipt","frontmatter")
hist = ("phase-3","Phase I","phase A","phase B","R-SYNC","state-sync.sh","cmd_pull",
        "cmd_push","cmd_migrate","Codex 0.144","1.0.169","graphify","Graphify",
        "antigravity","Antigravity")
for name, markers in (("GATE-ENFORCED", gate), ("HISTORICAL", hist)):
    rows = [(c,b) for c,b in entries if any(m in b for m in markers)]
    print(f"--- {name}: {len(rows)} entries, {sum(len(b.split()) for _,b in rows)} words")
    for c,b in rows: print("   ", (b[:100].replace("\n"," ")))
PY
```

### Lever B — Split (recommended first; loses nothing)

Keep a lean working `MEMORY.md` — the transferable lessons plus an index — and
move the long tail to an archive read on demand.

This is the only option that materially cuts per-session cost **without
deleting a single lesson**, which is why it was recommended first. The
per-session saving depends on how aggressively the working file is trimmed;
the archive is then read only when a topic is actually relevant.

**Blocking design decision (why this is paused):** where does the archive
live? See §5 — the obvious location is not durable.

---

## 5. Durability constraint — critical, and it bites

`.claude/` is fully gitignored (`.gitignore:24:.claude/`), and
`install_bootstrap.py --allow-self --local-only` **deletes files under
`.claude/` that the generated target does not contain**, as obsolete owned
files.

Only these are preserved, from `CONSUMER_STATE_PATHS` in
`scripts/runtime_ownership.py:41`:

```
MEMORY.md, plans, explorations, session_logs, quality_reports,
.cache, instructions/project-context.instructions.md,
(plus machine-local client settings)
```

**Observed, not theorised:** the `caveman-compress` backup at
`.claude/MEMORY.original.md` was created, and then **destroyed by the very
next `install_bootstrap --allow-self --local-only` run**, because
`MEMORY.original.md` is not in that list. Confirmed by the installer logging
it as an obsolete-file removal and by the file being absent afterwards.

Consequences for Lever B:

- An archive at `.claude/memory-archive.md` **will be deleted** on the next
  refresh. Do not put it there.
- Viable homes: inside an already-preserved directory — `.claude/explorations/`
  (where this document lives) or `.claude/session_logs/`.
- Or add the archive path to `CONSUMER_STATE_PATHS`. That is a **control-plane
  change** to `scripts/runtime_ownership.py` and needs the full lifecycle
  (plan, branch, review, closeout), plus a regression test in the style of the
  one added in phase 7 for state-directory READMEs.

Note the phase-7 precedent: `STATE_DIR_OWNED_README_PATHS` was added in
`scripts/runtime_ownership.py` to make `<state-dir>/README.md` bootstrap-owned
and refreshable while leaving `CONSUMER_STATE_PATHS` untouched. That commit
(`d2d0847`) is the worked example for how to extend ownership safely.

---

## 6. Separate defect found — worth its own fix

**`caveman-compress` creates a backup this repo's own installer destroys.**
The skill's step 5 mandates `<stem>.original.md` beside the target as its
safety net, and step 10 says to restore from it on validation failure. For any
target under `.claude/`, that backup is deleted by the next refresh, so the
promised safety net does not hold.

Harmless in this instance — the change was 1.2% and validated clean — but the
skill should either write its backup somewhere durable or state the limitation.
Candidate fix: back up into a preserved directory, or refuse `.claude/` targets
outside preserved paths.

Skill files:
- `.claude/skills/caveman-compress/SKILL.md`
- `.claude/skills/caveman-compress/scripts/detect.py`
- `.claude/skills/caveman-compress/scripts/validate.py`

---

## 7. Current state of the repository

- `.claude/MEMORY.md`: 717 lines, 49,455 bytes, all **171 entries intact**,
  carrying the 1.2% stylistic compression. Validator was clean when applied.
- `.claude/MEMORY.original.md`: **gone**, deleted by the refresh described in
  §5. There is no backup. Re-derive one from the file itself if needed; the
  compression was minor and non-destructive.
- `shared/MEMORY.md` (54 lines, the consumer seed template) was **not touched**
  and is deliberately out of scope — it is tracked canonical source and
  already small.
- Working tree clean; the big plan `verification-gate-semantic-hardening` is
  `complete` at commit `d2d0847`; no PR opened.

## 8. Open decisions for whoever picks this up

1. **Lever B (split) or Lever A (curation), or both?** B loses nothing and was
   the standing recommendation. A gives ~1,700 tokens for 26 entries.
2. **If splitting: where does the archive live?** Preserved directory (cheap,
   no code change) versus extending `CONSUMER_STATE_PATHS` (control-plane,
   needs the full lifecycle). This is the blocking question.
3. **If curating: delete outright, or leave a one-line stub** pointing at the
   gate that now enforces the lesson? Stubs preserve the "why the gate exists"
   value at a fraction of the cost.
4. **Minor, independent:** merge the duplicate `tests`/`testing` labels and the
   overlapping `code`/`quality` labels. Also consider whether 171 entries under
   only two headings is worth regrouping — note the `caveman-compress`
   validator forbids heading changes, so regrouping must be done outside that
   skill.
5. **Unrelated to size, do not lose:** fix the `caveman-compress` backup
   defect in §6.

## 9. Honest framing for the user conversation

The user's instinct that the file is too big is correct — ~12,400 tokens every
session is a real cost. But the file is not bloated; it is 171 distinct,
already-tight lessons. There is no compression trick that helps. Making it
materially smaller means **deciding which lessons stop earning their context**,
which is a value judgement, or **moving the tail out of the default read path**,
which is a structural change. Present it that way rather than promising a
compression win.
