---
name: bentoml-service
description: Create production-ready ML API services with BentoML. Use when deploying ML models, RAG systems, embedding services, or classification APIs. Covers service definition, lifecycle management, endpoint creation, Pydantic validation, and deployment configuration.
---

# BentoML API Service Development

## Core Principles

1. **Lifecycle Management**: Initialize expensive resources once in `on_startup`
2. **Async First**: Use async/await for I/O operations
3. **Type Safety**: Validate inputs/outputs with Pydantic models
4. **Environment Driven**: Configure via environment variables
5. **Production Ready**: Proper timeouts, CORS, error handling, logging

---

## Service Definition Pattern

```python
"""BentoML service."""
import os
import logging

import bentoml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@bentoml.service(
    traffic={"timeout": 120, "max_concurrency": 50},
    http={"cors": {"enabled": True, "access_control_allow_origins": ["*"]}},
    workers=1,
)
class MLService:
    """BentoML service for ML inference."""

    def __init__(self) -> None:
        self.model_name = os.getenv("MODEL_NAME", "bert-base-uncased")
        self.model = None

    @bentoml.on_startup
    async def on_startup(self) -> None:
        """Initialize model once at startup."""
        logger.info("Loading model: %s", self.model_name)
        # self.model = await load_model_async(self.model_name)
        logger.info("Service startup complete")

    @bentoml.on_shutdown
    async def on_shutdown(self) -> None:
        """Cleanup on shutdown."""
        logger.info("Shutting down service")

    @bentoml.api()
    async def predict(self, request: PredictRequest) -> PredictResponse:
        """Prediction endpoint."""
        try:
            result = "example"
            return PredictResponse(prediction=result, confidence=0.95)
        except Exception as e:
            logger.error("Prediction failed: %s", e)
            raise


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1)
    max_length: int = Field(512, ge=1, le=2048)


class PredictResponse(BaseModel):
    prediction: str
    confidence: float = Field(..., ge=0, le=1)
```

---

## Error Handling

```python
from bentoml.exceptions import BentoMLException

try:
    result = await self._run_inference(request.text)
except ValueError as e:
    logger.warning("Invalid input: %s", e)
    raise BentoMLException(f"Invalid input: {e}", error_code=400)
except Exception as e:
    logger.error("Inference failed: %s", e, exc_info=True)
    raise BentoMLException("Internal server error", error_code=500) from e
```

---

## bentofile.yaml

```yaml
service: "service.py:MLService"
include:
  - "service.py"
  - "src/"
python:
  requirements_txt: "requirements.txt"
docker:
  python_version: "3.12"
  env:
    MODEL_NAME: "bert-base-uncased"
```

---

## Build and Deployment

```bash
bentoml serve service.py:MLService --reload  # Local dev
uv run bentoml build                          # Build bento
uv run bentoml containerize ml_service:latest # Containerize
docker run -p 3000:3000 ml_service:latest     # Run container
```

---

## Testing

```python
@pytest.mark.asyncio
async def test_service_startup() -> None:
    service = MLService()
    await service.on_startup()
    assert service.model is not None

@pytest.mark.asyncio
async def test_predict_endpoint() -> None:
    service = MLService()
    await service.on_startup()
    request = PredictRequest(text="test", max_length=128)
    response = await service.predict(request)
    assert response.prediction is not None
    assert 0 <= response.confidence <= 1
```
