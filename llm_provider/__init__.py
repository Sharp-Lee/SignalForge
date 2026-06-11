"""Claude provider boundary for analysis and target generation."""

from .schemas import (
    ADVERSARIAL_SCHEMA,
    COMPLETENESS_SCHEMA,
    FREE_GENERATION_SCHEMA,
    TARGET_PROPOSAL_SCHEMA,
)
from .transport import (
    AnthropicCompletion,
    Completion,
    LlmProviderError,
    OpenAICompatibleCompletion,
    ResponsesAPICompletion,
    UsageRecord,
)
from .validation import (
    enforce_adversarial_output,
    enforce_completeness_output,
    enforce_free_generation_output,
    enforce_target_candidates,
    schema_allowed_fields,
)

__all__ = [
    "ADVERSARIAL_SCHEMA",
    "AnthropicCompletion",
    "COMPLETENESS_SCHEMA",
    "Completion",
    "FREE_GENERATION_SCHEMA",
    "LlmProviderError",
    "OpenAICompatibleCompletion",
    "ResponsesAPICompletion",
    "TARGET_PROPOSAL_SCHEMA",
    "UsageRecord",
    "enforce_adversarial_output",
    "enforce_completeness_output",
    "enforce_free_generation_output",
    "enforce_target_candidates",
    "schema_allowed_fields",
]
