---
name: pdf
description: |
  Use when working with PDF files in any way: reading/extracting text or tables,
  merging, splitting, rotating, adding watermarks, creating new PDFs, filling
  forms, encrypting/decrypting, extracting images, or OCR on scanned PDFs.
---

## Python Libraries Quick Reference

| Task | Library |
|------|---------|
| Read/merge/split/rotate | `pypdf` |
| Extract text with layout | `pdfplumber` |
| Extract tables | `pdfplumber` |
| Create PDFs | `reportlab` |
| OCR (scanned PDFs) | `pytesseract` + `pdf2image` |

---

## pypdf — Basic Operations

```python
from pypdf import PdfReader, PdfWriter

# Read
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")
text = "".join(page.extract_text() for page in reader.pages)

# Merge
writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)
with open("merged.pdf", "wb") as f:
    writer.write(f)

# Split (one file per page)
for i, page in enumerate(PdfReader("input.pdf").pages):
    w = PdfWriter()
    w.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as f:
        w.write(f)

# Rotate
reader = PdfReader("input.pdf")
writer = PdfWriter()
page = reader.pages[0]
page.rotate(90)  # clockwise
writer.add_page(page)
with open("rotated.pdf", "wb") as f:
    writer.write(f)

# Metadata
meta = PdfReader("document.pdf").metadata
print(meta.title, meta.author)
```

---

## pdfplumber — Text and Table Extraction

```python
import pdfplumber
import pandas as pd

# Text
with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)

# Tables
with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        for table in page.extract_tables():
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

combined = pd.concat(all_tables, ignore_index=True) if all_tables else pd.DataFrame()
```

---

## reportlab — Create PDFs

```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = [
    Paragraph("Report Title", styles["Title"]),
    Spacer(1, 12),
    Paragraph("Body text " * 20, styles["Normal"]),
    PageBreak(),
    Paragraph("Page 2", styles["Heading1"]),
]
doc.build(story)
```

**IMPORTANT — Subscripts/Superscripts in reportlab:**
Never use Unicode subscript/superscript characters (₀₁₂, ⁰¹²) — built-in fonts
lack these glyphs and render them as solid black boxes. Use XML markup instead:

```python
# Subscripts
chemical = Paragraph("H<sub>2</sub>O", styles["Normal"])

# Superscripts
squared = Paragraph("x<super>2</super> + y<super>2</super>", styles["Normal"])
```

---

## OCR — Scanned PDFs

```python
import pytesseract
from pdf2image import convert_from_path

images = convert_from_path("scanned.pdf")
text = ""
for i, image in enumerate(images):
    text += f"Page {i+1}:\n{pytesseract.image_to_string(image)}\n\n"
```

---

## Command-Line Tools

```bash
# pdftotext (poppler-utils)
pdftotext input.pdf output.txt
pdftotext -layout input.pdf output.txt       # preserve layout
pdftotext -f 1 -l 5 input.pdf output.txt    # pages 1-5

# qpdf
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
qpdf input.pdf output.pdf --rotate=+90:1

# pdftk (if available)
pdftk file1.pdf file2.pdf cat output merged.pdf
pdftk input.pdf burst                        # split to individual pages
pdftk input.pdf rotate 1east output rotated.pdf
```

---

## Anti-Patterns

- **Unicode subscripts in reportlab** — renders as black boxes; use `<sub>` tags
- **Not checking for text layer before OCR** — digital PDFs don't need OCR (30× slower)
- **`page.extract_text()` for table data** — use `page.extract_tables()` instead
