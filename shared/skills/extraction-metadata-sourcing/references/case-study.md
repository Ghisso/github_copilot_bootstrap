# Extraction Metadata Sourcing — Worked Case Study

Domain-specific example from a UN Security Council (UNSC) resolution
extraction project. Kept here because the field names and numbers are
project-specific — the classification method in the root `SKILL.md` does not
depend on this domain.

## Example Classification Table

| Field | Category | Should Come From | Why Extract from Text Fails |
|-------|----------|-----------------|--------------------------|
| Symbol (S/RES/2024/123) | Structured data | Filename or metadata header | Consistent format in document = regex works |
| Title | In-text entity | Document title section | Appears as heading = extraction works |
| Vote (13 in favor, 2 against) | Structured data | Document vote section OR external DB | Prose format, varies by year = hard; external DB = reliable |
| Topic (Health, Security) | **Metadata field** | UNBIS taxonomy / external database | Not in resolution text; curated separately = 0% extraction; external = 100% lookup |
| Subjects (Epidemiology, UN roles) | **Metadata field** | Subject classification system | Curated in library system, not in text = fails; external = lookup works |
| Date adopted | In-text entity | Document body ("adopted on January 2024") or metadata | Clear date format = extraction works |
| Adopted (Y/N) | In-text entity | Vote section ("unanimously adopted") | Explicit language in vote section = extraction works |

## Full Case Study

**Scenario:** UNSC resolution extraction with 2798 documents.

**Observation:** Symbol extraction 99%, topic extraction 0%.

**Root cause analysis (using this skill):**
- Symbol: present in filename and document header → in-text entity → regex extraction works
- Topic: curated in UNBIS taxonomy database, not in document text → metadata field → extraction fails

**Action:**
1. Stop optimizing NER for topics; they're not in text
2. Identify external source: UNBIS API (or CSV dump if API unavailable)
3. Create `UnMetadataProvider` implementing `MetadataProvider` protocol
4. Refactor pipeline: `extract_in_text_entities()` + `enrich_metadata()` + `get_metadata_with_fallback()`
5. Measure: API covers 71% of resolutions; CSV covers 80% of remainder; text fallback 5%

**Outcome:**
- Topic exact-match improved from 0% → 85% (via API lookup)
- Extraction time same (no training needed)
- Code simplified (fallback logic explicit, not buried in NER tuning)
