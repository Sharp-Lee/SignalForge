import json
import sqlite3
from pathlib import Path

from news_contracts.storage import ContractStore
from scripts.generate_digest import generate_digest


def _confirmed_thesis(thesis_id="thesis-digest-1", created_at="2026-06-11T08:00:00Z"):
    return {
        "id": thesis_id,
        "body": "AI服务器电源模块供给偏紧, 可能推动具备认证能力的A股供应商获得更多订单。",
        "source_signal_ids": ["sig-digest-1"],
        "substantive_claims": [
            {
                "text": "AI服务器电源模块交期拉长。",
                "source_signal_ids": ["sig-digest-1"],
            }
        ],
        "direction": "bullish",
        "origin_market": "global",
        "target_market": "CN-A",
        "transmission_path": [
            {
                "description": "全球AI服务器供应瓶颈传导到A股电源供应链。",
                "source_signal_ids": ["sig-digest-1"],
            }
        ],
        "status": "confirmed",
        "confidence": "medium",
        "uncertainty_tags": [],
        "completeness_critique": {
            "notes": ["检查订单是否真正转化为收入。"],
            "candidate_thesis_ids": [],
            "body_unchanged": True,
        },
        "adversarial_falsification": {
            "reviewer": "skeptic-reviewer",
            "review_session": {
                "thesis_author_id": "author-agent-1",
                "author_persona": "synthesis-author",
                "reviewer_instance_id": "reviewer-agent-1",
                "reviewer_persona": "skeptic-reviewer",
                "review_run_id": f"review-{thesis_id}",
            },
            "strongest_counterargument": "相关订单可能已经被市场提前计入估值。",
            "hedge_variables": ["订单兑现", "估值消化"],
        },
        "track_record": {
            "direction": "bullish",
            "falsifiable_expectation": "90天内相关供应商披露更多AI服务器订单。",
            "verification_window": {"start": "2026-06-11", "end": "2026-09-09"},
            "created_at": created_at,
        },
    }


def _signal(
    signal_id="sig-digest-1",
    published_at="2026-06-11T07:30:00Z",
    title="AI服务器电源模块交期拉长",
    body="AI服务器电源模块供给偏紧, 重点供应商产能排到明年。",
):
    return {
        "id": signal_id,
        "source": {
            "id": "rss:memory",
            "name": "Memory Supply News",
            "published_at": published_at,
            "url": f"https://example.com/{signal_id}",
        },
        "title": title,
        "body": body,
        "signal_origin": "news",
        "type_tag": "supply_demand_bottleneck",
        "triage": {"excluded": False, "reasons": [], "strategy": "zh_cn_heuristic_v0"},
        "raw_payload": {"fixture": signal_id},
    }


def _target(target_id="target-digest-1", thesis_id="thesis-digest-1"):
    return {
        "id": target_id,
        "symbol": "300308.SZ",
        "name": "中际旭创",
        "target_market": "CN-A",
        "thesis_ids": [thesis_id],
        "logic_score": {"score": 82, "rationale": "光模块环节与AI服务器扩容直接相关。"},
        "buy_point": {
            "status": "neutral",
            "rationale": "逻辑较强, 但短期涨幅需要观察。",
            "price_change_since_signal": 0.1234,
        },
        "state": "watch",
        "catalysts": [{"description": "新一代光模块订单或客户验证进展。"}],
        "exit_triggers": [{"description": "订单兑现不及预期。"}],
        "priced_in": {"price_change_since_signal": 0.1234, "risk": "medium"},
    }


def _target_without_conditions(target_id="target-empty-conditions", thesis_id="thesis-digest-1"):
    target = _target(target_id=target_id, thesis_id=thesis_id)
    target["catalysts"] = []
    target["exit_triggers"] = []
    return target


def _counts(path: Path):
    connection = sqlite3.connect(path)
    try:
        return {
            table: connection.execute(f"select count(*) from {table}").fetchone()[0]
            for table in ("theses", "targets", "track_record")
        }
    finally:
        connection.close()


def test_daily_digest_generates_markdown_and_inline_html(tmp_path):
    db_path = tmp_path / "store.db"
    store = ContractStore(db_path)
    thesis = _confirmed_thesis()
    store.add_signal(_signal())
    store.add_thesis(thesis)
    store.add_target(_target())
    before = _counts(db_path)

    result = generate_digest(store_path=db_path, date="2026-06-11", out_dir=tmp_path / "digests")

    md = result.markdown_path.read_text(encoding="utf-8")
    html = result.html_path.read_text(encoding="utf-8")
    assert "# SignalForge 每日研究笔记 - 2026-06-11" in md
    assert "本文为个人投资研究笔记" in md
    assert "## 今日逻辑链路" in md
    assert "### 逻辑 1: 看多 / 信心中" in md
    assert "#### 触发信息" in md
    assert "AI服务器电源模块交期拉长" in md
    assert "来源: Memory Supply News" in md
    assert "时间: 2026-06-11T07:30:00Z" in md
    assert "链接: https://example.com/sig-digest-1" in md
    assert "#### 世界大环境" in md
    assert "global → CN-A" in md
    assert "#### 推导出的支撑逻辑" in md
    assert "全球AI服务器供应瓶颈传导到A股电源供应链" in md
    assert "#### 确认后的逻辑" in md
    assert "信心: 中" in md
    assert "#### 最强反方观点" in md
    assert "相关订单可能已经被市场提前计入估值" in md
    assert "#### 这条逻辑的观察对象" in md
    assert "中际旭创 (300308.SZ)" in md
    assert "与逻辑相关度: 82" in md
    assert "观察条件" in md
    assert "新一代光模块订单或客户验证进展" in md
    assert "失效条件" in md
    assert "订单兑现不及预期" in md
    assert "信号以来涨跌幅: 12.34%" in md
    assert "priced-in 风险: 中" in md
    assert "买点" not in md
    assert "建议买入" not in md
    assert "推荐" not in md
    assert "选票" not in md

    assert result.html_path.name == "2026-06-11.html"
    assert "<style" not in html.lower()
    assert "<script" not in html.lower()
    assert 'style="' in html
    assert "本文为个人投资研究笔记" in html
    assert "触发信息" in html
    assert "这条逻辑的观察对象" in html
    assert "观察条件" in html
    assert "失效条件" in html
    assert "买点" not in html
    assert "选票" not in html
    assert _counts(db_path) == before


def test_daily_digest_target_conditions_fallback_when_missing(tmp_path):
    db_path = tmp_path / "store.db"
    store = ContractStore(db_path)
    thesis = _confirmed_thesis()
    store.add_signal(_signal())
    store.add_thesis(thesis)
    target = _target_without_conditions()
    store.connection.execute(
        "insert into targets (id, symbol, state, payload_json) values (?, ?, ?, ?)",
        (target["id"], target["symbol"], target["state"], json.dumps(target, ensure_ascii=False)),
    )
    store.connection.commit()

    result = generate_digest(store_path=db_path, date="2026-06-11", out_dir=tmp_path / "digests")

    md = result.markdown_path.read_text(encoding="utf-8")
    html = result.html_path.read_text(encoding="utf-8")
    assert "暂无观察条件" in md
    assert "暂无失效条件" in md
    assert "暂无观察条件" in html
    assert "暂无失效条件" in html
    assert "买点" not in md
    assert "买点" not in html


def test_daily_digest_empty_store_writes_no_new_content(tmp_path):
    db_path = tmp_path / "empty.db"
    ContractStore(db_path)

    result = generate_digest(store_path=db_path, date="2026-06-11", out_dir=tmp_path / "digests")

    md = result.markdown_path.read_text(encoding="utf-8")
    html = result.html_path.read_text(encoding="utf-8")
    assert "今日无新增" in md
    assert "今日无新增" in html
    assert "本文为个人投资研究笔记" in md


def test_daily_digest_filters_theses_by_created_date_but_keeps_watchlist(tmp_path):
    db_path = tmp_path / "store.db"
    store = ContractStore(db_path)
    old = _confirmed_thesis(thesis_id="thesis-old", created_at="2026-06-10T08:00:00Z")
    today = _confirmed_thesis(thesis_id="thesis-today", created_at="2026-06-11T09:00:00Z")
    today["source_signal_ids"] = ["sig-today"]
    today["substantive_claims"][0]["source_signal_ids"] = ["sig-today"]
    today["transmission_path"][0]["source_signal_ids"] = ["sig-today"]
    store.add_signal(
        _signal(
            signal_id="sig-old",
            published_at="2026-06-10T07:30:00Z",
            title="欧洲零售企业更新门店软件",
            body="欧洲零售企业发布门店软件升级计划, 关注收银效率和库存盘点, 与服务器硬件供应链无关。",
        )
    )
    store.add_signal(_signal(signal_id="sig-today", published_at="2026-06-11T07:30:00Z"))
    store.add_thesis(old)
    store.add_thesis(today)
    store.add_target(_target(target_id="target-today", thesis_id="thesis-today"))
    store.add_target(
        _target(
            target_id="target-old",
            thesis_id="thesis-old",
        )
        | {"symbol": "000001.SZ", "name": "旧标的"}
    )

    result = generate_digest(store_path=db_path, date="2026-06-11", out_dir=tmp_path / "digests")

    md = result.markdown_path.read_text(encoding="utf-8")
    assert "thesis-old" not in md
    assert "今日 1 条新逻辑" in md
    assert "中际旭创 (300308.SZ)" in md
    assert "旧标的" not in md
