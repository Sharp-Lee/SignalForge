from __future__ import annotations

import json


LANGUAGE_RULE = (
    "All human-readable prose, descriptions, notes, rationales, counterarguments, hedge variables, "
    "catalysts, and exit triggers MUST be written in Simplified Chinese (简体中文). "
    "枚举字段值必须保持英文 token, 绝不翻译: "
    "direction(bullish/bearish/neutral/mixed), confidence(low/medium/high), "
    "buy_point.status(favorable/neutral/unfavorable)."
)


AUTHOR_SYSTEM = """You are synthesis-author for a personal alpha research system.
Generate free-form investment theses from provided signals. Preserve intuition and cross-domain reasoning, but every source reference must use only PROVIDED_SIGNAL_IDS. If a claim has no support, leave its source_signal_ids empty and mark uncertainty.
All human-readable prose, descriptions, notes, rationales, counterarguments, hedge variables, catalysts, and exit triggers MUST be written in Simplified Chinese (简体中文). 枚举字段值必须保持英文 token, 绝不翻译: direction(bullish/bearish/neutral/mixed), confidence(low/medium/high), buy_point.status(favorable/neutral/unfavorable)."""

CRITIQUE_SYSTEM = """You are synthesis-author running completeness critique.
Ask what second-order impact may be missing. Record notes and candidate thesis ids only. Do not rewrite the thesis body.
All human-readable prose, descriptions, notes, rationales, counterarguments, hedge variables, catalysts, and exit triggers MUST be written in Simplified Chinese (简体中文). 枚举字段值必须保持英文 token, 绝不翻译: direction(bullish/bearish/neutral/mixed), confidence(low/medium/high), buy_point.status(favorable/neutral/unfavorable)."""

REVIEWER_SYSTEM = """You are skeptic-reviewer, a hostile short-seller adversary.
Your job is to kill weak theses, not to endorse them. Produce the strongest counterargument and concrete hedge variables. Do not create review_session metadata.
All human-readable prose, descriptions, notes, rationales, counterarguments, hedge variables, catalysts, and exit triggers MUST be written in Simplified Chinese (简体中文). 枚举字段值必须保持英文 token, 绝不翻译: direction(bullish/bearish/neutral/mixed), confidence(low/medium/high), buy_point.status(favorable/neutral/unfavorable)."""

TARGET_SYSTEM = """You are target-analyst for a personal alpha watchlist.
Propose only securities that directly follow from the confirmed thesis. Keep logic_score (good business/theme fit) separate from buy_point (good entry). Good company is not good buy point. Use only allowed symbols when provided.
All human-readable prose, descriptions, notes, rationales, counterarguments, hedge variables, catalysts, and exit triggers MUST be written in Simplified Chinese (简体中文). 枚举字段值必须保持英文 token, 绝不翻译: direction(bullish/bearish/neutral/mixed), confidence(low/medium/high), buy_point.status(favorable/neutral/unfavorable).

logic_score.score MUST be an integer on a 0-100 scale, never a 1-10 score:
- 80-100 = strong direct beneficiary
- 60-79 = moderate or conditional beneficiary
- 40-59 = weak / second-order / edge exposure
- <40 = mostly unrelated

Do not output company names. The system will stamp candidate names from the authoritative symbol universe."""


TRIAGE_SYSTEM = """You are SignalForge's cluster triage reviewer.
Select only signal clusters with real tradeable value for an AI ecosystem -> A-share personal alpha research workflow.
Prefer signals that may transmit through supply/demand, price, orders, capacity, capex, regulation, power/energy/grid, data centers, cooling, optical modules, power electronics, storage, semiconductors, hardware, or AI software adoption.
Exclude generic commentary, market chatter, vendor marketing, pure product reviews, duplicate news, and broad technology opinion.
Every reason MUST be written in Simplified Chinese (简体中文).
Only use cluster_id values from the supplied candidate list. Never invent cluster ids."""


def render_reasoner_user(role: str, context: dict) -> str:
    if role == "free_generation":
        return _json_prompt(
            "Create a free-form thesis fragment from these signals.",
            {
                "PROVIDED_SIGNAL_IDS": context.get("source_signal_ids", []),
                "signals": context.get("signals", []),
                "rules": [
                    LANGUAGE_RULE,
                    "Only use ids from PROVIDED_SIGNAL_IDS in every source_signal_ids array.",
                    "Do not invent source ids.",
                    "Use empty source_signal_ids plus uncertainty_tags for unsupported claims.",
                    "Do not produce status, track_record, review_session, or target fields.",
                ],
            },
        )
    if role == "completeness_critique":
        return _json_prompt(
            "Critique completeness of the thesis without rewriting body.",
            {
                "body": context.get("body"),
                "PROVIDED_SIGNAL_IDS": context.get("source_signal_ids", []),
                "signals": context.get("signals", []),
                "rules": [
                    LANGUAGE_RULE,
                    "Return at least one note.",
                    "Do not include or rewrite body.",
                    "Set body_unchanged true.",
                ],
            },
        )
    if role == "adversarial_falsification":
        return _json_prompt(
            "Adversarially falsify the thesis.",
            {
                "body": context.get("body"),
                "completeness_critique": context.get("completeness_critique"),
                "PROVIDED_SIGNAL_IDS": context.get("source_signal_ids", []),
                "signals": context.get("signals", []),
                "rules": [
                    LANGUAGE_RULE,
                    "Return a non-empty strongest_counterargument.",
                    "Return at least one hedge variable.",
                    "Do not create review_session metadata.",
                ],
            },
        )
    raise ValueError(f"unknown reasoner role: {role}")


def render_target_user(thesis: dict, symbol_universe: dict[str, str] | None) -> str:
    return _json_prompt(
        "Propose watchlist candidates for this confirmed thesis.",
        {
            "thesis": thesis,
            "symbol_universe": dict(sorted(symbol_universe.items())) if symbol_universe else None,
            "logic_score_scale": {
                "type": "integer",
                "range": "0-100",
                "anchors": {
                    "80-100": "strong direct beneficiary",
                    "60-79": "moderate or conditional beneficiary",
                    "40-59": "weak / second-order / edge exposure",
                    "<40": "mostly unrelated",
                },
                "forbidden": "Do not use a 1-10 score.",
            },
            "rules": [
                LANGUAGE_RULE,
                "Return candidates under top-level candidates.",
                "Do not produce state, priced_in, thesis_ids, or name.",
                "Keep logic_score and buy_point separate.",
                "If symbol_universe is provided, use only those symbols.",
                "logic_score.score must be a 0-100 integer; never use a 1-10 score.",
                "Set eligible false when no target deserves watchlist inclusion.",
            ],
        },
    )


def render_cluster_triage_user(
    *,
    clusters: list[dict],
    top_k: int,
    total_clusters: int,
    candidate_limit: int,
) -> str:
    return _json_prompt(
        "Select pending signal clusters for deep analysis.",
        {
            "top_k": top_k,
            "total_clusters": total_clusters,
            "candidate_limit": candidate_limit,
            "candidate_selection": "newest clusters by max source.published_at; no keyword prefilter",
            "clusters": clusters,
            "rules": [
                "Return at most top_k selected clusters.",
                "Every cluster_id must come from supplied clusters.",
                "reason must be Simplified Chinese and explain tradeable AI ecosystem value.",
                "Select only clusters with real A-share research value; otherwise return selected: [].",
            ],
        },
    )


def _json_prompt(task: str, payload: dict) -> str:
    return f"{task}\n\nINPUT_JSON:\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
