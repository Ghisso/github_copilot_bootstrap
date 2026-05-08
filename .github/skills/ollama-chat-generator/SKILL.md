---
name: ollama-chat-generator
description: |
  Fix common Ollama integration issues in Haystack pipelines. Triggers:
  - System prompt is silently ignored
  - format="json" has no effect on output
  - 30-60s startup timeouts
  - warm_up() method missing in newer versions
user-invocable: false
---

## Problem

`OllamaGenerator` is the text-completion interface — it does NOT support
`system`, `format`, or chat-style message history. These features only
work with `OllamaChatGenerator`.

```python
# WRONG — system and format are silently ignored
from haystack_integrations.components.generators.ollama import OllamaGenerator

generator = OllamaGenerator(
    model="llama3",
    system="You are a helpful assistant.",   # silently ignored
    generation_kwargs={"format": "json"},    # has no effect
)
```

## Solution

Use `OllamaChatGenerator` and pass the system prompt as a `ChatMessage`:

```python
from haystack.dataclasses import ChatMessage
from haystack_integrations.components.generators.ollama import OllamaChatGenerator


def create_chat_generator(model: str, system_prompt: str) -> OllamaChatGenerator:
    return OllamaChatGenerator(
        model=model,
        generation_kwargs={
            "temperature": 0.1,
            "num_predict": 512,
        },
    )


def run_chat(generator: OllamaChatGenerator, user_query: str, system_prompt: str) -> str:
    messages = [
        ChatMessage.from_system(system_prompt),
        ChatMessage.from_user(user_query),
    ]
    result = generator.run(messages=messages)
    return result["replies"][0].content
```

## JSON Output

Pass `response_format="json"` (not `format="json"` inside `generation_kwargs`):

```python
generator = OllamaChatGenerator(
    model="llama3",
    generation_kwargs={
        "response_format": "json",
        "temperature": 0.0,
    },
)
```

## Timeout & warm_up()

- Default Ollama timeout is 30s. For large models, increase:
  ```python
  OllamaChatGenerator(model="llama3", timeout=120)
  ```
- **`warm_up()` was removed in `ollama-haystack >= 6.1.0`** — do not call it.
  Remove any `generator.warm_up()` calls; the model loads on first request.

## Pipeline Integration

```python
from haystack import Pipeline
from haystack.components.builders import ChatPromptBuilder

prompt_template = """
Given these documents: {% for doc in documents %}{{ doc.content }}{% endfor %}
Answer: {{ query }}
"""

pipeline = Pipeline()
pipeline.add_component("prompt_builder", ChatPromptBuilder(template=prompt_template))
pipeline.add_component("generator", OllamaChatGenerator(model="llama3"))
pipeline.connect("prompt_builder.prompt", "generator.messages")

result = pipeline.run({
    "prompt_builder": {
        "documents": retrieved_docs,
        "query": user_query,
        "system_prompt": "You are a UN expert.",
    }
})
answer = result["generator"]["replies"][0].content
```

## Anti-Patterns

- **`OllamaGenerator` with `system=`** — silently ignored; use `OllamaChatGenerator`
- **`generation_kwargs={"format": "json"}`** — use `response_format="json"` instead
- **`generator.warm_up()`** — removed in ≥ 6.1.0; raises `AttributeError`
- **Low timeout (default 30s)** — increase to 120s+ for large models
