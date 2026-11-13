---
name: bentoml-service
visibility: public
description: Create production-ready ML API services with BentoML and deploy them. Use when deploying ML models, RAG systems, embedding services, or classification APIs, or when asked to build a Docker image. Covers service definition, lifecycle, Pydantic validation, bento build, containerize, health check.
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
  CPU-bound services may want more. Check what the target deployment
  actually provisions.
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

See Deploy below for containerization, health checks, and the full
deployment workflow.

## Deploy

The required checklist (tests, types, lint, health check, secrets in env,
`.env.example`) is canonical policy in
`.claude/instructions/deployment.instructions.md`. This section is the
step-by-step sequence for running that checklist plus the surrounding
build/containerize/rollback commands.

### Step 0: Confirm the Actual Service Details

Do not assume a fixed service name or port — read them from this project:

```bash
cat bentofile.yaml   # service entrypoint name
grep -n "port" service.py bentofile.yaml 2>/dev/null  # actual bound port, if overridden from the BentoML default
```

### Pre-Checks
```bash
uv run python -c "import service; print('Service imports OK')"
uv run pytest tests/ -q --tb=short
```

### Step 1: Local Serve
```bash
bentoml serve service.py:ServiceName --reload
# Health: curl http://localhost:${PORT:-3000}/healthz
# Test:   curl -X POST http://localhost:${PORT:-3000}/predict \
#           -H "Content-Type: application/json" \
#           -d '{"text": "test"}'
```

### Step 2: Build Bento
```bash
uv run bentoml build
uv run bentoml list
```

### Step 3: Containerize
```bash
uv run bentoml containerize service_name:latest
docker images | grep service_name
```

### Step 4: Test Container

Use the port this project's `bentofile.yaml`/service actually binds
(confirmed in Step 0), not a hardcoded assumption:

```bash
docker run -p ${PORT:-3000}:${PORT:-3000} service_name:latest &
sleep 5
curl http://localhost:${PORT:-3000}/healthz
# Repeat endpoint tests
```

### Step 5: Report
```
Deployment Status:
  Service: [name]
  Local test: PASS/FAIL
  Build: PASS/FAIL
  Container: PASS/FAIL
  Health check: PASS/FAIL
```

### Rollback
```bash
uv run bentoml list           # Find previous version
bentoml serve service_name:previous_tag
```
