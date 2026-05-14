# Performance Review Profile

Use for I/O-heavy paths, data pipelines, ML inference, and async code.

## Checklist

- Models and expensive resources load once, not per request.
- Connections are pooled or reused appropriately.
- File handles and external resources are closed.
- Async functions avoid blocking calls.
- Independent async work uses concurrency carefully.
- Large data is streamed or iterated lazily where practical.
- Large tensors, embeddings, and dataframes are not copied unnecessarily.
- Batch operations are used for embeddings, inference, and bulk I/O.
- Repeated expensive calls are cached when correctness allows.

## Severity

- Critical: Per-request model loading, blocking calls in async hot paths, or clear memory leaks.
- Major: Missing batching, N+1 expensive calls, avoidable large copies, or no caching for repeated expensive work.
- Minor: Generator opportunities or local optimization suggestions.

