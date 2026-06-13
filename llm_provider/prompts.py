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


REASONING_SYSTEM = """You are investment-reasoning-auditor for SignalForge.
Before any thesis is written, audit whether the provided signals contain a real investment logic worth analyzing.
Classify the primary logic type, validate the premise upward, decompose downstream bottlenecks, and decide whether target search is allowed.
Reject generic commentary, common benefits, and unsupported narratives. Weak or rejected logic must not proceed to target search.
All human-readable prose, descriptions, notes, rationales, counterarguments, hedge variables, catalysts, and exit triggers MUST be written in Simplified Chinese (简体中文). 枚举字段值必须保持英文 token, 绝不翻译: direction(bullish/bearish/neutral/mixed), confidence(low/medium/high), buy_point.status(favorable/neutral/unfavorable)."""


TRIAGE_SYSTEM = """You are SignalForge's cluster triage reviewer.
Select only signal clusters with real tradeable value for an AI ecosystem -> A-share personal alpha research workflow.
Prefer signals that may transmit through supply/demand, price, orders, capacity, capex, regulation, power/energy/grid, data centers, cooling, optical modules, power electronics, storage, semiconductors, hardware, or AI software adoption.
Exclude generic commentary, market chatter, vendor marketing, pure product reviews, duplicate news, and broad technology opinion.
Every reason MUST be written in Simplified Chinese (简体中文).
Only use cluster_id values from the supplied candidate list. Never invent cluster ids."""

TRIAGE_CHOKEPOINT_CONTEXT = """Chokepoint-aware mode:
Use the supplied curated chokepoint nodes as grounded priority context. Prefer clusters that are true catalysts for a supplied node because they materially affect industry-level supply, demand, price, capacity, orders, domestic substitution, or competitive structure. In the Chinese reason, mention the matched node name when that is why the cluster is selected.

Deprioritize single terminal-product launches, reviews, workstations, laptops, mini-PCs, NAS, single-server news, consumer devices, and expo demos. Even if they mention Blackwell, RTX, AI PC, or other advanced chips, they are not chokepoint catalysts unless the cluster clearly changes a supplied node's industry-level economics."""


CHOKEPOINT_MATCH_SYSTEM = """你是 SignalForge 卡脖子匹配器。
给定一条论点和一组【已接地的固定卡脖子节点】,判断这条论点是否是某个节点的【真实催化剂】。
真实催化剂 = 行业级的供需/价格/产能/订单/国产替代节奏/竞争格局的实质变化。例如:HBM 售罄、内存合约价翻倍、1.6T 光模块涨价、云厂 capex 指引上调、晶圆厂扩产、出口管制、行业性缺货或扩产。

以下一律返回 matched=[],绝不命中:
- 单一终端产品的发布/评测/参数(笔记本、工作站、迷你PC、NAS、单款服务器、消费数码、展会样机)——【即使它搭载了先进芯片(如 Blackwell/RTX GPU)也不算】:一款终端产品不会撼动数据中心光模块/电源/存储/设备的行业级需求;
- 沾边提及、泛 AI 评论、常规供应链利好、只出现类似关键词但没有实质行业级传导的内容。

判定自检:"这条信号会不会实质改变这个卡脖子环节的行业供需或价格?"——只有答案明确为"是"才命中。
只能使用提供的 node 名称,绝不发明节点。每个命中给一句说明行业级传导的简体中文 reason。默认保守,宁可不命中,不可硬凑。"""


def render_reasoner_user(role: str, context: dict) -> str:
    if role == "investment_reasoning":
        return _json_prompt(
            "Audit investment reasoning before free-form thesis generation.",
            {
                "PROVIDED_SIGNAL_IDS": context.get("source_signal_ids", []),
                "signals": context.get("signals", []),
                "rules": [
                    LANGUAGE_RULE,
                    "Use only ids from PROVIDED_SIGNAL_IDS in source_signal_ids and upward_validation.evidence.",
                    "primary_logic_type and secondary_logic_types must use canonical enum tokens from the schema.",
                    "Set evidence_status accepted only when upward validation and downstream decomposition are strong enough.",
                    "If evidence_status is weak or rejected, target_search_decision.status must not be allowed.",
                    "Keep public_caveat framed as personal research notes; do not use recommendation language.",
                ],
            },
        )
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
    chokepoint_nodes: list[dict] | None = None,
) -> str:
    payload = {
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
    }
    if chokepoint_nodes:
        payload["curated_chokepoint_nodes"] = chokepoint_nodes
        payload["rules"].extend(
            [
                "Use curated_chokepoint_nodes as grounded priority context, not as a hard filter.",
                "Prefer clusters that materially affect a supplied node's industry-level supply, demand, price, capacity, orders, domestic substitution, or competitive structure.",
                "When selecting a cluster because of chokepoint relevance, mention the matched node name in the Simplified Chinese reason.",
                "Deprioritize single terminal-product launches, reviews, workstations, laptops, mini-PCs, NAS, single-server news, consumer devices, and expo demos unless they clearly change a supplied node's industry-level economics.",
                "Advanced chips mentioned inside a terminal product, such as Blackwell, RTX, or AI PC, do not by themselves make the cluster a chokepoint catalyst.",
            ]
        )
    return _json_prompt(
        "Select pending signal clusters for deep analysis.",
        payload,
    )


def render_cluster_triage_system(*, chokepoint_nodes: list[dict] | None = None) -> str:
    if not chokepoint_nodes:
        return TRIAGE_SYSTEM
    return f"{TRIAGE_SYSTEM}\n\n{TRIAGE_CHOKEPOINT_CONTEXT}"


def render_chokepoint_match_user(*, thesis: dict, signals: list[dict], nodes: list[dict]) -> str:
    return _json_prompt(
        "Match this confirmed thesis to grounded chokepoint nodes before target generation.",
        {
            "thesis": _compact_thesis(thesis),
            "source_signals": [_compact_match_signal(signal) for signal in signals],
            "curated_nodes": nodes,
            "rules": [
                "Return matched: [] unless the thesis is a true catalyst for a supplied node.",
                "A true catalyst must materially affect supply, demand, price, capacity, orders, domestic substitution, or competitive structure.",
                "Only use node names from curated_nodes[].node.",
                "reason must be Simplified Chinese and explain the concrete catalyst path.",
            ],
        },
    )


def _compact_thesis(thesis: dict) -> dict:
    return {
        "id": thesis.get("id"),
        "body": thesis.get("body"),
        "direction": thesis.get("direction"),
        "confidence": thesis.get("confidence"),
        "substantive_claims": thesis.get("substantive_claims") or [],
        "transmission_path": thesis.get("transmission_path") or [],
        "investment_reasoning": thesis.get("investment_reasoning"),
    }


def _compact_match_signal(signal: dict) -> dict:
    source = signal.get("source") or {}
    return {
        "signal_id": signal.get("id"),
        "source": source.get("name") or source.get("id"),
        "published_at": source.get("published_at"),
        "title": signal.get("title"),
        "summary": (signal.get("body") or "")[:420],
    }


def _json_prompt(task: str, payload: dict) -> str:
    return f"{task}\n\nINPUT_JSON:\n{json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
