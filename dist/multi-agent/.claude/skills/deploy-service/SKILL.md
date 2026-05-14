---
name: deploy-service
description: |
  BentoML/Docker deployment workflow. Pre-checks, local serve, build bento,
  containerize, and health check. Use when deploying an ML service, asked to
  deploy, or build a Docker image.
---

# deploy-service — Deployment Workflow

## Pre-Checks
```bash
uv run python -c "import service; print('Service imports OK')"
uv run pytest tests/ -q --tb=short
cat bentofile.yaml
```

## Step 1: Local Serve
```bash
bentoml serve service.py:ServiceName --reload
# Health: curl http://localhost:3000/healthz
# Test:   curl -X POST http://localhost:3000/predict \
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
```bash
docker run -p 3000:3000 service_name:latest &
sleep 5
curl http://localhost:3000/healthz
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
