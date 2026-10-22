---
name: bentoml-service
visibility: public
description: Create production-ready ML API services with BentoML. Use when deploying ML models, RAG systems, embedding services, or classification APIs. Covers service definition, lifecycle management, endpoint creation, Pydantic validation, and deployment configuration.
---

# BentoML API Service Development

The required shape for a BentoML service — lifecycle hooks, Pydantic
validation, error handling, health check — is canonical policy in
`.claude/instructions/api-service-standards.instructions.md`. Read that
first; this skill covers what policy doesn't: sizing the runtime knobs for
the actual project instead of copying fixed numbers.

## Before writing the service

Check the real project instead of assuming defaults:

```bash
uv run python -c "import bentoml; print(bentoml.__version__)"
grep -n "bentoml" pyproject.toml
```

- **`traffic.timeout` / `max_concurrency`** — size from the model's real
  inference latency and the deployment's expected concurrent load. A slow
  LLM call needs a longer timeout than a fast embedding lookup; do not copy
  a fixed `120`/`50` without checking.
- **`workers`** — typically one worker per GPU for GPU-bound models;
  CPU-bound services may want more. Check what the target deployment (see
  `deploy-service`) actually provisions.
- **CORS `access_control_allow_origins`** — a wildcard (`["*"]`) is a
  local-dev convenience only. A production service must list its actual
  allowed origins; this is a security control, not a style choice, so don't
  ship the wildcard as a default.
- **Model name / config defaults** — read from this project's actual config
  or environment convention, not a hardcoded model string.

## Lifecycle skeleton (example)

```python
"""BentoML service."""
import logging
import os

import bentoml

logger = logging.getLogger(__name__)


@bentoml.service(
    traffic={"timeout": TIMEOUT_SEC, "max_concurrency": MAX_CONCURRENCY},
    http={"cors": {"enabled": True, "access_control_allow_origins": ALLOWED_ORIGINS}},
    workers=WORKER_COUNT,
)
class MLService:
    """BentoML service for ML inference."""

    def __init__(self) -> None:
        self.model_name = os.environ["MODEL_NAME"]  # required, no silent default
        self.model = None

    @bentoml.on_startup
    async def on_startup(self) -> None:
        """Initialize model once at startup."""
        logger.info("Loading model: %s", self.model_name)
        # self.model = await load_model_async(self.model_name)

    @bentoml.on_shutdown
    async def on_shutdown(self) -> None:
        """Cleanup on shutdown."""
        logger.info("Shutting down service")
```

`TIMEOUT_SEC`, `MAX_CONCURRENCY`, `ALLOWED_ORIGINS`, and `WORKER_COUNT` stand
in for values derived per "Before writing the service" above. See
`api-service-standards.instructions.md` for the required request/response,
Pydantic validation, and error-handling shape around this skeleton.

## bentofile.yaml

Match `python_version` to what this project actually pins — check
`pyproject.toml` rather than assuming a fixed version:

```yaml
service: "service.py:MLService"
include:
  - "service.py"
  - "src/"
python:
  requirements_txt: "requirements.txt"
docker:
  python_version: "3.12"   # match this project's actual pinned version
  env:
    MODEL_NAME: "${MODEL_NAME}"
```

## Build and Local Serve

```bash
bentoml serve service.py:MLService --reload  # Local dev
uv run bentoml build                          # Build bento
```

See `deploy-service` for containerization, health checks, and the full
deployment workflow.
