---
applyTo: "service.py,src/api/**/*.py"
---

# API & Service Standards

## BentoML Service Pattern

```python
@bentoml.service(
    traffic={"timeout": 120, "max_concurrency": 50},
    http={"cors": {"enabled": True, "access_control_allow_origins": ["*"]}},
    workers=1,
)
class MyService:
    """Service description."""

    def __init__(self) -> None:
        self.model_name = os.getenv("MODEL_NAME", "default")
        self.model = None

    @bentoml.on_startup
    async def on_startup(self) -> None:
        """Initialize expensive resources once at startup."""
        self.model = await load_model(self.model_name)

    @bentoml.api()
    async def predict(self, request: PredictRequest) -> PredictResponse:
        """Endpoint with Pydantic validation."""
        ...
```

## Required Elements

1. **Lifecycle management**: `@bentoml.on_startup` for expensive initialization
2. **Pydantic validation**: All request/response types as Pydantic models with `Field` validators
3. **Async-first**: Use `async` for I/O-bound endpoints
4. **Error handling**: Catch exceptions, log, return structured errors
5. **Health check**: Endpoint to verify service is alive
6. **CORS configuration**: Enable in service decorator
7. **Environment-driven config**: Use `os.getenv()` for all configuration

## Pydantic Models

```python
from pydantic import BaseModel, Field, field_validator

class QueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    mode: Literal["local", "global", "hybrid"] = Field("global")
    top_k: int = Field(50, ge=1, le=100)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace")
        return v.strip()
```

## Error Handling

```python
from bentoml.exceptions import BentoMLException

try:
    result = await self._process(request)
except ValueError as e:
    logger.warning("Invalid input: %s", e)
    raise BentoMLException(f"Invalid input: {e}", error_code=400)
except Exception as e:
    logger.error("Processing failed: %s", e, exc_info=True)
    raise BentoMLException("Internal server error", error_code=500) from e
```

## Testing Services

```python
@pytest.mark.asyncio
async def test_service_startup() -> None:
    service = MyService()
    await service.on_startup()
    assert service.model is not None


@pytest.mark.asyncio
async def test_predict_validates_input() -> None:
    service = MyService()
    await service.on_startup()
    with pytest.raises(Exception):
        await service.predict(QueryRequest(message=""))
```
