"""End-to-end pipeline orchestration."""

from .core import (
    PipelineError,
    PipelineResult,
    analyze_pending,
    capture_sources,
    pending_signals,
    run_pipeline,
    signal_analysis_counts,
)

__all__ = [
    "PipelineError",
    "PipelineResult",
    "analyze_pending",
    "capture_sources",
    "pending_signals",
    "run_pipeline",
    "signal_analysis_counts",
]
