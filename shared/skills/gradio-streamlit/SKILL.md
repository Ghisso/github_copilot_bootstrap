---
name: gradio-streamlit
visibility: public
description: |
  Decision framework and patterns for building ML demos with Gradio or Streamlit.
  Use when creating interactive UIs for models, RAG pipelines, or data tools.
  Covers: Gradio lazy-loading pattern, Streamlit session state, async wrapping.
---

## Decision Framework

| Factor | Gradio | Streamlit |
|--------|--------|-----------|
| Number of inputs | ≤ 5 | Any |
| Complexity | Simple demo | Complex multi-page app |
| State management | Minimal | Rich (session_state) |
| Deployment | Share link built-in | Needs server |
| Best for | Model demos, API wrappers | Dashboards, data tools |

**Rule of thumb:** Use Gradio for quick demos with few inputs. Use Streamlit
for multi-step workflows, session state, or data exploration.

---

## Gradio: Lazy-Loading Pattern

Load heavy models only on first request to avoid blocking app startup:

```python
import asyncio
import gradio as gr
import nest_asyncio
from typing import Any

nest_asyncio.apply()  # Allow nested event loops in Jupyter / BentoML

_lock = asyncio.Lock()
_runner: Any = None  # Lazy singleton


async def _get_runner() -> Any:
    """Initialize runner on first call, reuse thereafter."""
    global _runner
    async with _lock:
        if _runner is None:
            from src.retrieval.query_runner import QueryRunner
            _runner = QueryRunner.from_env()
    return _runner


def _run_sync(coro):
    """Run an async coroutine from a sync context."""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def query(text: str, top_k: int) -> str:
    """Gradio handler — sync wrapper around async runner."""
    runner = _run_sync(_get_runner())
    return runner.run(text, top_k=top_k)


def build_app() -> gr.Blocks:
    with gr.Blocks(title="RAG Demo") as demo:
        gr.Markdown("# UNSC Resolution Search")
        with gr.Row():
            query_box = gr.Textbox(label="Query", lines=2)
            top_k = gr.Slider(1, 20, value=5, label="Top K")
        output = gr.Textbox(label="Answer", lines=10)
        query_box.submit(query, inputs=[query_box, top_k], outputs=output)
    return demo


if __name__ == "__main__":
    build_app().launch()
```

---

## Streamlit: Session State Pattern

```python
import streamlit as st
from src.retrieval.query_runner import QueryRunner


@st.cache_resource
def get_runner() -> QueryRunner:
    """Cached across all sessions — loads once per process."""
    return QueryRunner.from_env()


def main() -> None:
    st.title("UNSC Resolution Search")

    # Persist query across reruns
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""

    query = st.text_area("Query", value=st.session_state.last_query)
    top_k = st.slider("Top K", 1, 20, 5)

    if st.button("Search"):
        st.session_state.last_query = query
        with st.spinner("Searching..."):
            runner = get_runner()
            result = runner.run(query, top_k=top_k)
        st.markdown(result)


if __name__ == "__main__":
    main()
```

---

## Env Var Wiring

Both frameworks should read config from environment variables, not hardcoded values:

```python
import os

TOP_K = int(os.getenv("DEFAULT_TOP_K", "5"))
RETRIEVER_MODE = os.getenv("RETRIEVER_MODE", "hybrid")
```

---

## Anti-Patterns

- **Loading models at module level** — blocks app startup; use lazy init
- **Not using `@st.cache_resource`** for Streamlit — reloads model on every interaction
- **`nest_asyncio.apply()` missing** — causes `RuntimeError: This event loop is already running`
- **Hardcoded values** — use env vars for top_k, mode, model name
