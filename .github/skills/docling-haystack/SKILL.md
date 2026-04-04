---
name: docling-haystack
description: |
  Integrate Docling with Haystack for PDF ingestion. Triggers:
  - TypeError when passing pipeline_options= directly to DoclingConverter
  - OCR performance issues (60s/PDF vs 2-5s without OCR)
  - Configuring Docling's DocumentConverter format options from Haystack
---

## Problem

Passing `pipeline_options=` directly to Haystack's `DoclingConverter` raises
a `TypeError` — that parameter does not exist on the Haystack wrapper. The
`pipeline_options` must be wrapped in a `PdfFormatOption` and passed via
a `DocumentConverter` instance.

```python
# WRONG — TypeError: DoclingConverter.__init__() got unexpected kwarg
from haystack_integrations.components.converters.docling import DoclingConverter
converter = DoclingConverter(pipeline_options=pdf_pipeline_options)
```

## Solution

Build a `DocumentConverter` with `format_options` and pass it via `converter=`:

```python
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from haystack_integrations.components.converters.docling import DoclingConverter


def _build_converter(do_ocr: bool) -> DoclingConverter:
    pipeline_options = PdfPipelineOptions(
        do_ocr=do_ocr,
        do_table_structure=True,
        ocr_options=EasyOcrOptions(lang=["en"]) if do_ocr else None,
    )
    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    return DoclingConverter(converter=doc_converter)
```

## OCR Performance Guide

| Mode | Time per PDF | When to use |
|------|-------------|-------------|
| `do_ocr=False` | ~2-5s | Digital-native PDFs (text layer present) |
| `do_ocr=True` | ~60s | Scanned/image-based PDFs |

Check whether PDFs have a text layer before deciding:

```python
import pdfplumber

def has_text_layer(pdf_path: str) -> bool:
    """Return True if the PDF has an extractable text layer."""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                return True
    return False
```

## Haystack Pipeline Integration

```python
from haystack import Pipeline
from haystack.components.writers import DocumentWriter
from haystack_integrations.components.converters.docling import DoclingConverter
from haystack_integrations.document_stores.in_memory import InMemoryDocumentStore


def build_indexing_pipeline(do_ocr: bool = False) -> Pipeline:
    converter = _build_converter(do_ocr)
    store = InMemoryDocumentStore()

    pipeline = Pipeline()
    pipeline.add_component("converter", converter)
    pipeline.add_component("writer", DocumentWriter(document_store=store))
    pipeline.connect("converter.documents", "writer.documents")
    return pipeline


# Run
pipeline = build_indexing_pipeline(do_ocr=False)
pipeline.run({"converter": {"sources": ["doc1.pdf", "doc2.pdf"]}})
```

## Anti-Patterns

- **`DoclingConverter(pipeline_options=...)`** — TypeError, parameter doesn't exist
- **Always using OCR** — 30× slower for digital PDFs; check for text layer first
- **Forgetting `do_table_structure=True`**  — tables become unstructured text
- **Hardcoding language in EasyOcrOptions** — parameterize via config
