---
name: haystack
visibility: public
description: |
  Haystack 2.x pipelines: component wiring, ConditionalRouter routes, Docling PDF
  conversion, and OllamaChatGenerator setup. Use when building, debugging, or
  testing a Haystack pipeline or one of these components.
---

# Haystack

Haystack 2.x lessons in four topics. Read only the reference that matches the
task; each is a file in this skill's `references/` folder.

**Pipeline construction.** Read `references/pipelines.md` when building or
debugging a `Pipeline`: adding every component before `connect()`, building
semantic, BM25, or hybrid variants, building run inputs, or fixing
`Component named X not found` and silent empty output.

**Conditional routing.** Read `references/conditional-router.md` when wiring a
`ConditionalRouter` for multi-branch pipelines (semantic, SQL, hybrid): output
names and socket references, per-mode routes, `DocumentJoiner` merging, tagging
SQL documents, or a route that silently skips.

**Docling PDF conversion.** Read `references/docling.md` when ingesting PDFs
with `DoclingConverter`: the `pipeline_options=` `TypeError`, `PdfFormatOption`
wiring, or slow OCR.

**Ollama chat generation.** Read `references/ollama-chat.md` when using Ollama
in a pipeline: an ignored system prompt, `format="json"` with no effect, startup
timeouts, or a missing `warm_up()`.
