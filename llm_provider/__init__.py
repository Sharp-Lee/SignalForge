"""Claude provider boundary for analysis and target generation."""

from .schemas import (
    ADVERSARIAL_SCHEMA,
    CLUSTER_TRIAGE_SCHEMA,
    COMPLETENESS_SCHEMA,
    FREE_GENERATION_SCHEMA,
    INVESTMENT_REASONING_SCHEMA,
    TARGET_PROPOSAL_SCHEMA,
)
from .transport import (
    AnthropicCompletion,
    Completion,
    LlmProviderError,
    OpenAICompatibleCompletion,
    UsageRecord,
)
from .triage import LlmClusterTriageSelector, TriageSelection
from .validation import (
    enforce_adversarial_output,
    enforce_cluster_triage_output,
    enforce_completeness_output,
    enforce_free_generation_output,
    enforce_investment_reasoning_output,
    enforce_target_candidates,
    schema_allowed_fields,
)

__all__ = [
    "ADVERSARIAL_SCHEMA",
    "AnthropicCompletion",
    "CLUSTER_TRIAGE_SCHEMA",
    "COMPLETENESS_SCHEMA",
    "Completion",
    "FREE_GENERATION_SCHEMA",
    "INVESTMENT_REASONING_SCHEMA",
    "LlmClusterTriageSelector",
    "LlmProviderError",
    "OpenAICompatibleCompletion",
    "TARGET_PROPOSAL_SCHEMA",
    "TriageSelection",
    "UsageRecord",
    "enforce_adversarial_output",
    "enforce_cluster_triage_output",
    "enforce_completeness_output",
    "enforce_free_generation_output",
    "enforce_investment_reasoning_output",
    "enforce_target_candidates",
    "schema_allowed_fields",
]
