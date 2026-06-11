from __future__ import annotations

import json
from hashlib import sha1


def adapt_last30days_agent_output(agent_output: str | list[dict]) -> list[dict]:
    payload = json.loads(agent_output) if isinstance(agent_output, str) else agent_output
    items = _extract_signal_items(payload)
    signals = []
    for item in items:
        body = item.get("body") or item.get("summary") or item.get("title", "")
        title = item.get("title", body[:60])
        signals.append(
            {
                "id": item.get("id") or f"last30days-{sha1((title + body).encode('utf-8')).hexdigest()[:12]}",
                "source": {
                    "id": "last30days",
                    "name": "last30days",
                    "published_at": item["published_at"],
                    "url": item["url"],
                },
                "title": title,
                "body": body,
                "signal_origin": "last30days_attention",
                "type_tag": item.get("type_tag") or _infer_type_tag(title, body),
                "triage": {"excluded": False, "reasons": []},
                "raw_payload": item,
                "source_weight": "attention_only",
            }
        )
    return signals


def _extract_signal_items(payload: list[dict] | dict) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("last30days output must be a JSON object or array")

    extracted = []
    topic = payload.get("topic")
    generated_at = payload.get("generated_at")
    for source, source_items in (payload.get("items_by_source") or {}).items():
        for item in source_items:
            for source_item in item.get("source_items") or [item]:
                extracted.append(
                    {
                        **source_item,
                        "id": source_item.get("url") or item.get("candidate_id") or item.get("item_id"),
                        "title": source_item.get("title") or item.get("title", ""),
                        "body": source_item.get("body") or item.get("snippet") or item.get("title", ""),
                        "url": source_item.get("url") or item.get("url") or item.get("candidate_id"),
                        "published_at": source_item.get("published_at") or item.get("published_at") or generated_at,
                        "last30days_topic": topic,
                        "last30days_source": source,
                        "last30days_candidate_id": item.get("candidate_id"),
                        "last30days_cluster_id": item.get("cluster_id"),
                    }
                )
    return extracted


def _infer_type_tag(title: str, body: str) -> str:
    text = f"{title}\n{body}"
    if any(term in text for term in ("交期", "产能", "售罄", "长协", "锁单")):
        return "supply_demand_bottleneck"
    if any(term in text for term in ("政策", "新规", "监管")):
        return "policy"
    if any(term in text for term in ("厄尔尼诺", "降雨", "天气", "气候")):
        return "weather_climate"
    if any(term in text for term in ("出口管制", "制裁", "地缘")):
        return "export_control_geopolitics"
    if any(term in text for term in ("技术", "突破", "拐点")):
        return "technology_inflection"
    return "other"
