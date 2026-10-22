---
applicability:
  - service.py
  - bentofile.yaml
  - gradio_app/**
  - streamlit_app/**
  - deployment/**
---

# Deployment Standards

## Pre-Deployment Checklist

- [ ] All tests passing: `uv run pytest tests/ -q`
- [ ] No type errors: `uv run mypy src/ --ignore-missing-imports`
- [ ] Zero lint violations: `uv run ruff check src/ tests/`
- [ ] Service imports cleanly: `uv run python -c "import service; print('OK')"`
- [ ] Health check endpoint exists and returns 200
- [ ] All secrets in environment variables (not hardcoded)
- [ ] `.env.example` documents all required env vars

## BentoML Deployment

```bash
# Local development
bentoml serve service.py:ServiceName --reload

# Build bento
uv run bentoml build

# Containerize
uv run bentoml containerize service_name:latest
```

## bentofile.yaml Requirements

```yaml
service: "service.py:ServiceName"
include:
  - "service.py"
  - "src/**/*.py"
  - "pyproject.toml"
python:
  packages:
    - package-name
```

## Docker / docker-compose

- Never hardcode credentials in `docker-compose.yaml`
- Use `${ENV_VAR:-default}` syntax for env var substitution
- Map secrets from `.env` file via `env_file: .env`

## Health Check

Every service MUST expose a health check endpoint:

```python
@bentoml.api(route="/health")
async def health(self) -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
```

Test with: `curl http://localhost:3000/health`

## Rollback

```bash
uv run bentoml list                    # Find previous version tag
bentoml serve service_name:prev_tag   # Serve previous version
```
