---
name: pipeline-patterns
visibility: public
description: |
  Haystack pipeline construction patterns and component ordering rules. Use when
  building Haystack pipelines, debugging component connection errors, implementing
  conditional pipeline logic for multiple retrieval modes, or constructing query inputs.
---

## CRITICAL: Add Components Before Connecting

```python
# WRONG — causes ValueError
pipeline = Pipeline()
pipeline.connect("retriever.documents", "prompt_builder.documents")  # FAILS
pipeline.add_component("prompt_builder", prompt_builder)             # Too late

# CORRECT
pipeline = Pipeline()

# 1. Add ALL components first
pipeline.add_component("prompt_builder", PromptBuilder(template=template))
pipeline.add_component("generator", OllamaGenerator(...))
pipeline.add_component("retriever", InMemoryEmbeddingRetriever(...))

# 2. Then connect
pipeline.connect("retriever.documents", "prompt_builder.documents")
pipeline.connect("prompt_builder.prompt", "generator.prompt")
```

---

## Conditional Pipeline Building (Semantic / BM25 / Hybrid)

```python
def build(self) -> Pipeline:
    pipeline = Pipeline()

    # Add common components FIRST
    pipeline.add_component("prompt_builder", PromptBuilder(template=self.template))
    pipeline.add_component("generator", self._create_generator())

    if self.config.mode == "semantic":
        pipeline.add_component("embedder", self._create_embedder())
        pipeline.add_component("retriever", self._create_semantic_retriever())
        pipeline.connect("embedder.embedding", "retriever.query_embedding")
        pipeline.connect("retriever.documents", "prompt_builder.documents")

    elif self.config.mode == "bm25":
        pipeline.add_component("retriever", self._create_bm25_retriever())
        pipeline.connect("retriever.documents", "prompt_builder.documents")

    elif self.config.mode == "hybrid":
        pipeline.add_component("embedder", self._create_embedder())
        pipeline.add_component("semantic_retriever", self._create_semantic_retriever())
        pipeline.add_component("bm25_retriever", self._create_bm25_retriever())
        pipeline.add_component("joiner", self._create_joiner())
        pipeline.connect("embedder.embedding", "semantic_retriever.query_embedding")
        pipeline.connect("semantic_retriever.documents", "joiner.documents")
        pipeline.connect("bm25_retriever.documents", "joiner.documents")
        pipeline.connect("joiner.documents", "prompt_builder.documents")

    # Common final connection
    pipeline.connect("prompt_builder.prompt", "generator.prompt")
    return pipeline
```

---

## Query Input Construction

```python
def query(self, query_text: str) -> dict:
    if self.config.mode == "semantic":
        inputs = {
            "embedder": {"text": query_text},
            "prompt_builder": {"query": query_text},
        }
    elif self.config.mode == "bm25":
        inputs = {
            "retriever": {"query": query_text},
            "prompt_builder": {"query": query_text},
        }
    elif self.config.mode == "hybrid":
        inputs = {
            "embedder": {"text": query_text},
            "bm25_retriever": {"query": query_text},
            "prompt_builder": {"query": query_text},
        }

    return self.pipeline.run(inputs, include_outputs_from=["generator"])
```

**Key rules:**
1. Input keys must match exact `add_component()` names
2. All components without incoming edges need inputs
3. Only include components whose outputs you need in `include_outputs_from`

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Component named X not found` | Connected before adding | Add component first |
| `Component X has no input socket Y` | Wrong input name | Check component docs |
| Pipeline runs but no output | Missing `include_outputs_from` | Add component name |
| Silent empty output | Route output name typo | Check exact names in `connect()` |
