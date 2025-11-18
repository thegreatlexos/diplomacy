# LLM Routing Design Document

## Current Architecture

### Overview

The Diplomacy game engine currently uses AWS Bedrock exclusively for all LLM interactions. Each power (nation) in the game is controlled by an LLM, and a separate LLM generates season summaries.

### Component Structure

```
Gamemaster
├── PhaseManager (handles phase transitions)
├── LLMPlayer (one per power)
│   └── BedrockClient (AWS Bedrock API)
├── Summarizer
│   └── BedrockClient (AWS Bedrock API)
└── TokenTracker (tracks usage and costs)
```

### Current LLM Flow

1. **Gamemaster** orchestrates the game
2. **LLMPlayer** needs to generate orders/press
3. **LLMPlayer** calls `BedrockClient.generate()`
4. **BedrockClient** makes AWS Bedrock API call
5. Response is parsed and returned
6. **TokenTracker** logs usage and calculates cost

### Current Limitations

- **Single Provider**: Only AWS Bedrock models supported
- **Limited Model Selection**: Restricted to Bedrock's catalog
- **Pricing**: All costs calculated using Bedrock pricing
- **No Flexibility**: Cannot mix providers in same game

### What Works Well

✓ Token tracking with model ID
✓ Per-power cost breakdown
✓ CSV logging of all calls
✓ Comprehensive reporting
✓ Model-specific pricing (for Bedrock models)

---

## Proposed LLM Routing Architecture

### Goals

1. **Multi-Provider Support**: Route to Bedrock OR OpenRouter based on model ID
2. **Backward Compatibility**: Existing Bedrock-only games continue to work
3. **Flexible Configuration**: Mix providers in same game
4. **Accurate Pricing**: Use correct rates for each provider
5. **Testability**: Easy to test without API credentials

### Architecture Design

```
Gamemaster
├── PhaseManager
├── LLMPlayer (one per power)
│   └── LLMClientFactory
│       ├── BedrockClient (for AWS models)
│       └── OpenRouterClient (for OpenRouter models)
├── Summarizer
│   └── LLMClientFactory
│       ├── BedrockClient
│       └── OpenRouterClient
└── TokenTracker
```

### Component Descriptions

#### 1. Abstract LLM Client Interface

```python
class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.

        Returns:
            Dict with 'content' and 'usage' keys
            usage contains: input_tokens, output_tokens, total_tokens
        """
        pass
```

#### 2. Bedrock Client Wrapper

```python
class BedrockClientWrapper(LLMClient):
    """Wrapper around existing BedrockClient."""

    def __init__(self, region: str, profile: Optional[str] = None):
        self.client = BedrockClient(region, profile)

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # Call existing BedrockClient
        response = self.client.generate(prompt, **kwargs)
        # Return in standard format
        return {
            'content': response['content'],
            'usage': response['usage']
        }
```

#### 3. OpenRouter Client

```python
class OpenRouterClient(LLMClient):
    """Client for OpenRouter API."""

    def __init__(self, api_key: str):
        from openrouter import OpenRouter
        self.client = OpenRouter(api_key=api_key)

    def generate(self, prompt: str, model_id: str, **kwargs) -> Dict[str, Any]:
        # Call OpenRouter API
        response = self.client.chat.send(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        # Return in standard format
        return {
            'content': response.choices[0].message.content,
            'usage': {
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
        }
```

#### 4. LLM Client Factory

```python
class LLMClientFactory:
    """Factory for creating appropriate LLM client based on model ID."""

    @staticmethod
    def create_client(model_id: str, **config) -> LLMClient:
        """
        Create appropriate client based on model ID format.

        Bedrock models: eu.anthropic.*, us.anthropic.*, etc.
        OpenRouter models: Everything else
        """
        if LLMClientFactory.is_bedrock_model(model_id):
            return BedrockClientWrapper(
                region=config.get('aws_region', 'eu-west-1'),
                profile=config.get('aws_profile')
            )
        else:
            return OpenRouterClient(
                api_key=config.get('openrouter_api_key')
            )

    @staticmethod
    def is_bedrock_model(model_id: str) -> bool:
        """Check if model ID is for AWS Bedrock."""
        bedrock_prefixes = ['eu.', 'us.', 'ap-', 'ca-']
        return any(model_id.startswith(prefix) for prefix in bedrock_prefixes)
```

### Model ID Format Detection

**Bedrock Models:**

- Format: `{region}.{provider}.{model}:{version}`
- Examples:
  - `eu.anthropic.claude-haiku-4-5-20251001-v1:0`
  - `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

**OpenRouter Models:**

- Format: `{provider}/{model}`
- Examples:
  - `anthropic/claude-4.5-sonnet`
  - `google/gemini-2.5-flash`
  - `openai/gpt-5`
  - `meta-llama/llama-4-maverick`

### Configuration

**.env file:**

```env
# AWS Bedrock
AWS_REGION=eu-west-1
AWS_PROFILE=sf-datadev-dataeng

# OpenRouter
OPENROUTER_API_KEY=your_key_here

# Model Assignments (mix providers!)
MODEL_ENGLAND=eu.anthropic.claude-haiku-4-5-20251001-v1:0  # Bedrock
MODEL_FRANCE=anthropic/claude-4.5-sonnet                    # OpenRouter
MODEL_GERMANY=google/gemini-2.5-flash                       # OpenRouter
MODEL_ITALY=openai/gpt-5                                    # OpenRouter
MODEL_AUSTRIA=meta-llama/llama-4-scout                      # OpenRouter
MODEL_RUSSIA=deepseek/deepseek-v3-1-terminus                # OpenRouter
MODEL_TURKEY=x-ai/grok-4-fast                               # OpenRouter
```

### Implementation Steps

1. **Phase 1: Create Separate Module**

   - Create `llm_routing/` folder
   - Implement all components
   - Write comprehensive tests
   - Test with mock responses

2. **Phase 2: Integration**

   - Update `LLMPlayer` to use factory
   - Update `Summarizer` to use factory
   - Update `Gamemaster` to pass config
   - Test with real API calls

3. **Phase 3: Validation**
   - Run test game with mixed providers
   - Verify token tracking works
   - Verify costs are calculated correctly
   - Verify all model types work

### Testing Strategy

#### Unit Tests

- Test model ID detection (Bedrock vs OpenRouter)
- Test factory creates correct client type
- Test each client's response format
- Test error handling

#### Integration Tests

- Test with mock API responses
- Test token tracking integration
- Test cost calculation accuracy

#### End-to-End Tests

- Run small game with Bedrock models
- Run small game with OpenRouter models
- Run game with mixed providers
- Verify all outputs are correct

### Migration Path

**Step 1: No Changes to Existing Code**

- Develop routing module separately
- Test thoroughly in isolation

**Step 2: Minimal Integration**

- Add factory to `LLMPlayer.__init__()`
- Keep existing `BedrockClient` as fallback
- Test with current Bedrock models

**Step 3: Full Deployment**

- Enable OpenRouter models
- Update documentation
- Provide example configurations

### Risk Mitigation

**Risks:**

1. Breaking existing Bedrock functionality
2. Incorrect cost calculations
3. API compatibility issues
4. Performance degradation

**Mitigations:**

1. Separate module development + comprehensive tests
2. Extensive validation of pricing logic
3. Mock testing before real API calls
4. Performance benchmarking

### Success Criteria

✓ All existing Bedrock games work unchanged
✓ Can configure OpenRouter models via .env
✓ Token tracking includes correct model IDs
✓ Costs calculated using correct provider pricing
✓ Reports show per-model breakdown
✓ No performance degradation
✓ Comprehensive test coverage

---

## Next Steps

1. Create design document (this file) ✓
2. Review and approve design
3. Create separate `llm_routing/` module
4. Implement and test components
5. Integrate into main codebase
6. Validate with real games
