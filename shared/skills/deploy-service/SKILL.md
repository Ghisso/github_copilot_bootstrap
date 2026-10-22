---
name: deploy-service
visibility: public
description: |
  BentoML/Docker deployment workflow. Pre-checks, local serve, build bento,
  containerize, and health check. Use when deploying an ML service, asked to
  deploy, or build a Docker image.
---

# deploy-service — Deployment Workflow

The required checklist (tests, types, lint, health check, secrets in env,
`.env.example`) is canonical policy in
`.claude/instructions/deployment.instructions.md`. This skill is the
step-by-step sequence for running that checklist plus the surrounding
build/containerize/rollback commands.

## Step 0: Confirm the Actual Service Details

Do not assume a fixed service name or port — read them from this project:

```bash
cat bentofile.yaml   # service entrypoint name
grep -n "port" service.py bentofile.yaml 2>/dev/null  # actual bound port, if overridden from the BentoML default
```

## Pre-Checks
```bash
uv run python -c "import service; print('Service imports OK')"
uv run pytest tests/ -q --tb=short
```

## Step 1: Local Serve
```bash
bentoml serve service.py:ServiceName --reload
# Health: curl http://localhost:${PORT:-3000}/healthz
# Test:   curl -X POST http://localhost:${PORT:-3000}/predict \
#           -H "Content-Type: application/json" \
#           -d '{"text": "test"}'
```

## Step 2: Build Bento
```bash
uv run bentoml build
uv run bentoml list
```

## Step 3: Containerize
```bash
uv run bentoml containerize service_name:latest
docker images | grep service_name
```

## Step 4: Test Container

Use the port this project's `bentofile.yaml`/service actually binds
(confirmed in Step 0), not a hardcoded assumption:

```bash
docker run -p ${PORT:-3000}:${PORT:-3000} service_name:latest &
sleep 5
curl http://localhost:${PORT:-3000}/healthz
# Repeat endpoint tests
```

## Step 5: Report
```
Deployment Status:
  Service: [name]
  Local test: PASS/FAIL
  Build: PASS/FAIL
  Container: PASS/FAIL
  Health check: PASS/FAIL
```

## Rollback
```bash
uv run bentoml list           # Find previous version
bentoml serve service_name:previous_tag
```
