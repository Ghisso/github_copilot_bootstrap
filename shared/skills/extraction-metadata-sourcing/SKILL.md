---
name: extraction-metadata-sourcing
visibility: background
description: |
  Distinguish between in-text entities (suitable for NER/regex extraction) and
  curated metadata fields (requiring external sources). Use when building CSV
  extraction pipelines or document-to-structured-data systems. Prevents wasted
  effort optimizing NER for fields that don't exist in source text and identifies
  the correct source (API, CSV, external database) for low-confidence extraction
  results.
  
  Triggers:
  - "NER/regex extraction is failing on specific columns (0% match)"
  - "Some CSV fields extract well, others never improve despite optimization"
  - "Trying to extract curated taxonomy mappings from unstructured text"
  - "Wondering why vote counts, topics, or metadata can't be extracted from resolution text"
  - Graph/CSV extraction pipeline is bottlenecked on low-confidence fields
user-invocable: false
---

## Problem

Document extraction projects often conflate two distinct field types, leading to wasted optimization effort:

1. **In-text entities** (extract via NER/regex)
   - Information embedded in document prose/tables: names, dates, symbols, contact info
   - Extractable from text alone
   - Examples: resolution symbol `(S/RES/2024/123)`, vote (e.g., "13 in favor, 1 abstention"), paragraph numbers

2. **Curated metadata** (source from external APIs/databases/CSV)
   - Information maintained separately: taxonomy classifications, subject tags, internal IDs
   - Not reliably embedded in document text (or embedded inconsistently)
   - Examples: UNBIS topic tags, UNESCO subject classifications, internal document codes, vote counts as metadata

Common mistakes:
- Trying to extract UNBIS topics from resolution text (they're curated in a separate database)
- Attempting regex on vote counts that appear as prose rather than structured data
- Optimizing NER models for fields that don't appear in text but in metadata headers
- Building complex heuristics for fields that should come from an authoritative external source

**Result:** 0% extraction rate despite weeks of tuning, false confidence in extraction quality.

## Context / Trigger Conditions

**When to use this skill:**
- Building document-to-CSV pipelines (PDFs, emails, webpages → structured data)
- CSV extraction showing wildly inconsistent per-column accuracy (some 99%, some 0%)
- NER/regex models plateau at low accuracy on specific fields despite increased training
- Reviewing extraction pipeline that's bottlenecked on metadata-heavy columns

**Exact symptoms / errors:**
- CSV comparison report shows: symbol 99% exact match, topics 0% exact match
- NER model trained on 1000+ examples, achieves 85% on entities but 5% on metadata tags
- Query: "Why does our extraction pipeline work for addresses but not for NAICS codes?"
- Analysis: "Vote extraction is stuck at 0% presence; regex patterns can't capture structured vote data"
- Reviewer: "We're trying to extract taxonomy topics from resolution text, but those live in a separate UNBIS database — should we be doing that?"

## Solution

### Step 1: Classify Fields into Categories

For each field/column in your target CSV/database:

**Is this information present in the document text?**

| Answer | Category | Source | Extraction Approach |
|--------|----------|--------|---------------------|
| Yes, embedded in text (e.g., "12 votes in favor") | In-text entity | Document text | NER / Regex / LLM extraction |
| Yes, but inconsistent location (e.g., headers, tables, footnotes) | Structured data (location-dependent) | Document structure | Layout-aware extraction + post-processing |
| No, information is curated externally or in metadata | Metadata field | External API / CSV / Database | Provider lookup or fallback chain |
| Maybe, but unreliable (e.g., "approved on Jan 15" vs "January 15th" vs just "Jan") | Weakly embedded | Text + external verification | Extract as feature, rank on confidence |

**Example classification (UNSC Resolution extraction):**

| Field | Category | Should Come From | Why Extract from Text Fails |
|-------|----------|-----------------|--------------------------|
| Symbol (S/RES/2024/123) | Structured data | Filename or metadata header | Consistent format in document =✅ regex works |
| Title | In-text entity | Document title section | Appears as heading =✅ extraction works |
| Vote (13 in favor, 2 against) | Structured data | Document vote section OR external DB | Prose format, varies by year = ⚠️ hard; external DB = ✅ reliable |
| Topic (Health, Security) | **Metadata field** | UNBIS taxonomy / external database | NOT in resolution text; curated separately = ❌ 0% extraction; external = ✅ 100% lookup |
| Subjects (Epidemiology, UN roles) | **Metadata field** | Subject classification system | Curated in library system, not in text =❌ extraction; external = ✅ lookup |
| Date adopted | In-text entity | Document body ("adopted on January 2024") or metadata | Clear date format = ✓ extraction works |
| Adopted (Y/N) | In-text entity | Vote section ("unanimously adopted") | Explicit language in vote section = ✓ extraction works |

### Step 2: Diagnose Pipeline Bottleneck

Run comparison analysis:

```python
# Pseudo-code for CSV comparison (like docs/CSV_COMPARISON_REPORT.md)

results = extract_all()  # Run NER + regex on all documents

for column_name, extracted_values in results.items():
    exact_match_rate = calculate_exact_match(extracted_values, golden_values[column_name])
    presence_rate = calculate_presence(extracted_values)
    
    print(f"{column_name:20} | exact_match: {exact_match_rate:5.1f}% | presence: {presence_rate:5.1f}%")

# Output:
# symbol               | exact_match: 99.2% | presence: 99.2%   <- In-text entity ✅
# body                 | exact_match: 100%  | presence: 100%    <- Metadata (constant) ✅
# title                | exact_match: 94.7% | presence: 94.7%   <- In-text entity ✅ (minor spelling)
# vote                 | exact_match:  8.3% | presence: 15.2%   <- Mixed (metadata + prose) ⚠️
# topic                | exact_match:  0.0% | presence:  0.0%   <- Metadata field ❌
# subjects             | exact_match:  0.0% | presence:  0.0%   <- Metadata field ❌
# adopted (Y/N)        | exact_match: 97.1% | presence: 97.1%   <- In-text entity ✅
```

**Decision logic:**
- 0% exact match + 0% presence → **Metadata field**: Don't optimize extraction; source externally
- 90%+ exact match in samples → **In-text entity**: Continue optimizing (high ROI)
- 10–89% exact match → **Weakly embedded or structured with format variance**: Hybrid approach (extract + validate against external)
- <5% presence → **Not reliably in text**: Switch to external source

### Step 3: Identify External Source

For metadata fields (0% extraction), determine authoritative source:

**Common metadata sources:**
- **Curated taxonomy database** (UNBIS, UNESCO, Library of Congress)
  - Examples: UNSC topic classifications, document subject codes
  - Access: API (if available) or CSV dump
  - Cost: API calls or periodic data sync

- **Government/institutional metadata systems**
  - Examples: UN member states, official document registries
  - Access: REST API, SOAP, CSV dumps, web scraping (if permitted)
  - Cost: Network latency + rate-limiting

- **Existing CSV / Structured data**
  - Examples: Previous UNSC extractions, manually classified documents
  - Access: File system or database
  - Cost: File I/O (fast) + maintenance (keep synchronized)

- **Hybrid Hugging Face Datasets or web sources**
  - Examples: Pre-built UNSC dataset on HF Hub
  - Access: HTTP + cache
  - Cost: Bandwidth + trust in external data quality

**Selection strategy:**
```
PRIORITY 1: Authoritative API (if exists + available)
  └─ Cached responses (24-48h TTL)
  └─ Fallback: Secondary source on timeout/401/429

PRIORITY 2: CSV/structured secondary source
  └─ Pre-loaded into memory or SQLite
  └─ Fallback: Text extraction (best-effort)

PRIORITY 3: Text extraction (confidence threshold)
  └─ Use only if scores >0.7
  └─ Mark as "uncertain" in output
```

### Step 4: Refactor Pipeline with Source Separation

Restructure extraction to make source explicit:

**Before (conflated):**
```python
def extract_all_fields(doc: Document) -> dict[str, str]:
    # Tries NER/regex for everything, confuses in-text entities with metadata
    return {
        "symbol": extract_symbol_regex(doc.text),  # ✅ works
        "topic": extract_topic_llm(doc.text),      # ❌ fails (0%)
        "vote": extract_vote_regex(doc.text),      # ⚠️ partial
    }
```

**After (separated by source):**
```python
def extract_in_text_entities(doc: Document) -> dict[str, str]:
    """Extract entities embedded in document text."""
    return {
        "symbol": extract_symbol_regex(doc.text),    # ✅ Regex on text
        "title": extract_title_nlp(doc.text),        # ✅ NER on text
        "adopted": extract_adopted_heuristic(doc),   # ✅ Boolean from text
    }

def enrich_metadata(extraction: ResolutionExtraction, 
                    api: MetadataProvider) -> EnrichedExtraction:
    """Enrich text extraction with external metadata."""
    meta = api.get_metadata(extraction.resolution_id)  # Lookup, don't extract
    
    return EnrichedExtraction(
        **extraction,
        topic=meta.get("topic"),     # From API, not text
        subjects=meta.get("subjects"), # From API, not text
        vote=meta.get("vote_summary"), # From external (more reliable than text)
    )

def aggregate_final_result(text_extraction: dict, 
                           metadata: dict) -> dict:
    """Merge valid extractions with authoritative metadata."""
    return {
        **text_extraction,          # In-text entities (high confidence)
        **metadata,                 # Curated metadata (authoritative)
    }
```

### Step 5: Define Fallback for Weak/Missing Metadata

For metadata fields where external source is unavailable:

```python
def get_metadata_with_fallback(resolution_id: str,
                               text_extraction: dict,
                               api: MetadataProvider | None,
                               csv_provider: MetadataProvider | None) -> dict:
    """Apply source priority: API → CSV → text (confidence threshold)."""
    
    # Priority 1: API (authoritative)
    if api:
        try:
            return api.get_metadata(resolution_id)
        except (ConnectionError, TimeoutError, KeyError):
            pass  # Fall through to secondary
    
    # Priority 2: CSV (secondary)
    if csv_provider:
        try:
            return csv_provider.get_metadata(resolution_id)
        except KeyError:
            pass  # Fall through to text
    
    # Priority 3: Text extraction (best-effort, confidence-gated)
    return {
        "topic": text_extraction.get("topic", None),  # May be None (0% extraction)
        "subjects": text_extraction.get("subjects", None),
        # Mark source as uncertain/fallback
        "_metadata_source": "text_extraction",
        "_metadata_confidence": 0.3,  # Low for curated fields
    }
```

### Step 6: Measure Source Coverage

After implementing source separation, measure what percentage of rows get metadata from each source:

```python
results = []
for resolution_id in all_resolution_ids:
    text_result = extract_in_text_entities(load_doc(resolution_id))
    metadata = get_metadata_with_fallback(resolution_id, text_result, api, csv)
    metadata["_source"] = metadata.get("_metadata_source", "api")  # Track source
    results.append(metadata)

# Measure source distribution
source_distribution = {
    source: sum(1 for r in results if r["_source"] == source)
    for source in ["api", "csv", "text_extraction"]
}

print("Metadata source distribution:")
for source, count in source_distribution.items():
    pct = 100 * count / len(results)
    print(f"  {source:20} {count:5d} ({pct:5.1f}%)")

# Example output:
# api                      2000 ( 71.4%)
# csv                       650 ( 23.2%)
# text_extraction           148 (  5.3%)
```

**Acceptance criteria:**
- Primary source (API) should cover ≥70% of corpus
- Secondary source (CSV) should catch ≥80% of remainder
- Text fallback acceptable only for <10% of total

## Verification

✅ **Step 1:** Fields classified into in-text vs metadata categories  
✅ **Step 2:** Comparison report shows 0% on metadata fields, 80%+ on in-text  
✅ **Step 3:** Authoritative external source identified and documented  
✅ **Step 4:** Extraction pipeline split by source (text vs metadata)  
✅ **Step 5:** Fallback chain implemented with source priority  
✅ **Step 6:** Source distribution measured (primary >70%, secondary >80% of remainder)  

## Example

**Scenario:** UNSC resolution extraction with 2798 documents.

**Observation:** Symbol extraction 99%, topic extraction 0%.

**Root cause analysis (using this skill):**
- Symbol: Present in filename and document header → in-text entity → regex extraction works
- Topic: Curated in UNBIS taxonomy database, not in document text → metadata field → extraction fails

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

---

## Related Patterns

- `.claude/skills/integration-gate-spike/SKILL.md` — How to validate external metadata API contracts
- `.claude/skills/csv-driven-integration-tests/SKILL.md` — Integration test datasets with field source tracking
- `.claude/skills/testing-patterns/SKILL.md` — Mocking external metadata providers in tests
