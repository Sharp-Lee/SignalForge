import json
import sqlite3
from datetime import UTC, datetime

import pytest

from news_contracts.adapters.last30days import adapt_last30days_agent_output
from news_contracts.interfaces import (
    add_substantive_claim,
    add_transmission_step,
    create_adversarial_review,
    create_calibration_signal,
    create_completeness_critique,
    create_empty_recommendation,
    create_freeform_thesis,
    create_human_decision,
    create_market_move_signal,
    create_outcome_raw,
    create_track_record,
    update_target_state,
)
from news_contracts.schemas import load_contract_schema
from news_contracts.storage import ContractStore
from news_contracts.validation import (
    CalibrationNotImplemented,
    ContractError,
    DEFAULT_DEDUP_THRESHOLD,
    _jaccard,
    dedup_hash,
    validate_signal,
    validate_target,
    validate_thesis,
)


def valid_signal(**overrides):
    data = {
        "id": "sig-1",
        "source": {
            "id": "source-a",
            "name": "Source A",
            "published_at": "2026-06-09T08:00:00Z",
            "url": "https://example.com/news/1",
        },
        "title": "产能售罄且交期延长",
        "body": "某关键零部件产能售罄，交期从 4 周延长到 12 周。",
        "signal_origin": "news",
        "type_tag": "supply_demand_bottleneck",
        "triage": {"excluded": False, "reasons": []},
        "raw_payload": {"original": "payload"},
    }
    data.update(overrides)
    return data


def valid_thesis(**overrides):
    data = {
        "id": "thesis-1",
        "body": "厄尔尼诺导致强降雨，城市排水管网需求可能提前释放。",
        "source_signal_ids": ["sig-1"],
        "substantive_claims": [
            {"text": "强降雨会提高排水管网改造紧迫性", "source_signal_ids": ["sig-1"]}
        ],
        "direction": "bullish",
        "affected_industries": ["water_infrastructure"],
        "status": "draft",
        "confidence": "medium",
        "uncertainty_tags": [],
    }
    data.update(overrides)
    return data


def confirmed_thesis(**overrides):
    data = valid_thesis(
        status="confirmed",
        completeness_critique={
            "notes": ["还需要检查是否存在二阶受益标的"],
            "candidate_thesis_ids": [],
            "body_unchanged": True,
        },
        adversarial_falsification={
            "reviewer": "skeptic-persona",
            "review_session": {
                "thesis_author_id": "author-agent",
                "author_persona": "builder",
                "reviewer_instance_id": "reviewer-agent",
                "reviewer_persona": "skeptic",
                "review_run_id": "review-run-1",
            },
            "strongest_counterargument": "地方财政压力可能推迟项目落地。",
            "hedge_variables": ["专项债发行进度"],
        },
        track_record={
            "direction": "bullish",
            "falsifiable_expectation": "90 天内相关订单公告数量上升",
            "verification_window": {
                "start": "2026-06-09",
                "end": "2026-09-07",
            },
            "created_at": "2026-06-09T08:00:00Z",
        },
    )
    data.update(overrides)
    return data


def valid_target(**overrides):
    data = {
        "id": "target-1",
        "symbol": "PIPE",
        "name": "Pipe Co",
        "target_market": "CN-A",
        "thesis_ids": ["thesis-1"],
        "logic_score": {"score": 82, "rationale": "主题贴合且订单弹性大"},
        "buy_point": {"status": "favorable", "rationale": "未明显定价", "price_change_since_signal": 0.05},
        "state": "watch",
        "catalysts": [{"kind": "date", "value": "2026-07-01", "description": "政策细则"}],
        "exit_triggers": [{"description": "政策细则低于预期"}],
        "priced_in": {"price_change_since_signal": 0.05, "risk": "low"},
    }
    data.update(overrides)
    return data


SERVE_THE_HOME_RSS_ITEMS = [
    {
        "title": "Minisforum S5 All-Flash NAS Shown Based on Intel’s Wildcat Lake Platform",
        "body": """<p>At Computex 2026 Minisforum was showing off their upcoming S5 NAS, a mid-range all-flash NAS. With 5 M.2 SSD slots and 10GbE networking, the fanless NAS punches up</p>
<p>The post <a href="https://www.servethehome.com/minisforum-s5-all-flash-nas-shown-based-on-intels-wildcat-lake-platform/">Minisforum S5 All-Flash NAS Shown Based on Intel&#8217;s Wildcat Lake Platform</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    },
    {
        "title": "ServeTheHome Turns 17 The Places You Will Go",
        "body": """<p>ServeTheHome is now 17 years old, starting from posting about using RAID controllers and 2.5" hard drives and taking us all over</p>
<p>The post <a href="https://www.servethehome.com/servethehome-turns-17-the-places-you-will-go/">ServeTheHome Turns 17 The Places You Will Go</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    },
    {
        "title": "NXP Computex Keynote 2026 Coverage",
        "body": """<p>The final keynote for Computex 2026 comes from NXP, where CEO Rafael Sotomayor is talking all about what it takes to deliver AI for edge devices and robotics in the real world, and how NXP is well-positioned to accomplish this</p>
<p>The post <a href="https://www.servethehome.com/nxp-computex-keynote-2026-coverage/">NXP Computex Keynote 2026 Coverage</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    },
    {
        "title": "A 40-Node 1U Cluster Gigabyte R1C7-K0A-AS1",
        "body": """<p>At Computex 2026, we found the Gigabyte R1C7-K0A-AS1 which can put 40 nodes with 320 cores, 40 iGPUs and 80 SSDs in just 1U</p>
<p>The post <a href="https://www.servethehome.com/a-40-node-1u-cluster-gigabyte-r1c7-k0a-as1/">A 40-Node 1U Cluster Gigabyte R1C7-K0A-AS1</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    },
    {
        "title": "Scoping Out RTX Spark SFF Mini-PCs at Computex 2026",
        "body": """<p>While at Computex, we caught a look at some of the upcoming SFF mini-PCs based on NVIDIA's RTX Spark SoC, including systems from ASUS, Dell, Lenovo, and MSI</p>
<p>The post <a href="https://www.servethehome.com/scoping-out-rtx-spark-sff-mini-pcs-at-computex-2026/">Scoping Out RTX Spark SFF Mini-PCs at Computex 2026</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    },
    {
        "title": "Microsoft to Join the AI Dev Mini-PC Market With Upcoming Surface RTX Spark Dev Box",
        "body": """<p>Microsoft is joining the AI dev box mini-PC market with the announcement of the Surface RTX Spark Dev Box. Due later this year, it will offer a pre-loaded dev environment, powered by NVIDIA's new RTX Spark SoC</p>
<p>The post <a href="https://www.servethehome.com/microsoft-to-join-the-ai-dev-mini-pc-market-with-upcoming-surface-rtx-spark-dev-box/">Microsoft to Join the AI Dev Mini-PC Market With Upcoming Surface RTX Spark Dev Box</a> appeared first on <a href="https://www.servethehome.com">ServeTheHome</a>.</p>""",
    },
]

CHINESE_DIFFERENT_SIGNALS = [
    "北美云厂商上调800G光模块采购计划，2026年二季度订单环比增加35%，交付周期延长到10周。",
    "台系ODM反馈高功率电源模块交期从6周拉长到14周，主要受AI整机机柜功耗提升影响。",
    "HBM3E供应商表示2026年产能已被大客户预订超过80%，先进封装排产延后到四季度。",
    "欧洲数据中心液冷改造项目在2026年下半年启动，单柜功率目标提升到120千瓦。",
    "高速PCB材料厂6月上调BT载板报价12%，交换机与服务器主板需求拉动排产。",
    "墨西哥服务器整机新产线开始试产，预计2026年底月产能提升至3万台。",
]


def serve_the_home_signal(index: int, **overrides):
    item = SERVE_THE_HOME_RSS_ITEMS[index]
    data = valid_signal(
        id=f"sth-{index + 1}",
        source={
            "id": "rss:servethehome",
            "name": "ServeTheHome",
            "published_at": f"2026-06-09T0{index}:00:00Z",
            "url": f"https://www.servethehome.com/item-{index + 1}/",
        },
        title=item["title"],
        body=item["body"],
        type_tag="technology_inflection",
        raw_payload=item,
    )
    data.update(overrides)
    return data


def chinese_signal(index: int, body: str, **overrides):
    data = valid_signal(
        id=f"zh-{index + 1}",
        source={
            "id": "fixture:cn",
            "name": "Chinese Fixture",
            "published_at": f"2026-06-09T1{index}:00:00Z",
            "url": f"https://example.com/cn/{index + 1}",
        },
        title=f"AI供应链信号 {index + 1}",
        body=body,
        raw_payload={"fixture": "chinese-dedup"},
    )
    data.update(overrides)
    return data


def test_schema_files_exist_for_all_three_contracts():
    assert load_contract_schema("signal-contract")["title"] == "signal-contract"
    assert load_contract_schema("thesis-contract")["title"] == "thesis-contract"
    assert load_contract_schema("target-contract")["title"] == "target-contract"


def test_signal_scenario_missing_date_is_rejected():
    signal = valid_signal(source={"id": "source-a", "name": "Source A", "url": "https://example.com/news/1"})

    with pytest.raises(ContractError, match="published_at"):
        validate_signal(signal)


def test_signal_scenario_complete_provenance_is_accepted():
    assert validate_signal(valid_signal()).accepted is True


def test_signal_scenario_duplicate_reports_are_merged_or_dropped():
    first = valid_signal(id="sig-1", body="COD 排放标准提升 30%，预计带动 300 亿治理投资")
    duplicate = valid_signal(
        id="sig-2",
        source={
            "id": "source-b",
            "name": "Source B",
            "published_at": "2026-06-09T09:00:00Z",
            "url": "https://example.com/news/2",
        },
        body="COD 排放标准提升 30%，预计带动 300 亿治理投资",
    )

    result = validate_signal(duplicate, existing=[first])

    assert result.accepted is False
    assert result.reason == "near_duplicate"
    assert result.duplicate_of == "sig-1"


def test_signal_dedup_accepts_distinct_serve_the_home_articles(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    max_similarity = max(
        _jaccard(left["body"], right["body"])
        for left_index, left in enumerate(SERVE_THE_HOME_RSS_ITEMS)
        for right in SERVE_THE_HOME_RSS_ITEMS[left_index + 1 :]
    )

    # The tightest approved margin is English distinct content: real max ~0.096 vs threshold 0.14.
    # If this regresses, raise the English threshold or split thresholds by language; do not lower the global threshold.
    assert 0.09 < max_similarity < DEFAULT_DEDUP_THRESHOLD

    for index in range(len(SERVE_THE_HOME_RSS_ITEMS)):
        store.add_signal(serve_the_home_signal(index))

    count = store.connection.execute("select count(*) as count from signals").fetchone()["count"]
    assert count == 6


def test_signal_dedup_rejects_english_true_near_duplicate():
    first = serve_the_home_signal(0)
    duplicate = serve_the_home_signal(
        0,
        id="sth-near-duplicate",
        source={
            "id": "rss:other-tech",
            "name": "Other Tech",
            "published_at": "2026-06-09T08:00:00Z",
            "url": "https://example.com/minisforum-s5-near-duplicate",
        },
        title="Minisforum shows S5 all-flash NAS at Computex 2026",
        body=(
            "At Computex 2026, Minisforum showed off the upcoming S5 NAS, a mid-range "
            "all-flash NAS with five M.2 SSD slots, 10GbE networking, and a fanless design."
        ),
    )

    result = validate_signal(duplicate, existing=[first])

    assert result.accepted is False
    assert result.reason == "near_duplicate"
    assert result.duplicate_of == "sth-1"


def test_signal_dedup_accepts_chinese_different_articles(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    for index, body in enumerate(CHINESE_DIFFERENT_SIGNALS):
        store.add_signal(chinese_signal(index, body))

    count = store.connection.execute("select count(*) as count from signals").fetchone()["count"]
    assert count == 6


def test_signal_dedup_rejects_chinese_true_near_duplicate():
    first = chinese_signal(
        0,
        "HBM3E供应商表示2026年产能已被大客户预订超过80%，先进封装排产因此延后到四季度。",
    )
    duplicate = chinese_signal(
        1,
        "HBM3E主要供应商称2026年产能预订已超过八成，大客户追加订单让先进封装排期推迟。",
        id="zh-near-duplicate",
        source={
            "id": "fixture:cn-alt",
            "name": "Chinese Alt Fixture",
            "published_at": "2026-06-09T18:00:00Z",
            "url": "https://example.com/cn/hbm-alt",
        },
    )

    result = validate_signal(duplicate, existing=[first])

    assert result.accepted is False
    assert result.reason == "near_duplicate"
    assert result.duplicate_of == "zh-1"


def test_signal_dedup_intentionally_misses_heavy_english_paraphrase():
    first = serve_the_home_signal(0)
    heavy_paraphrase = serve_the_home_signal(
        0,
        id="sth-heavy-paraphrase",
        source={
            "id": "rss:other-tech",
            "name": "Other Tech",
            "published_at": "2026-06-09T08:30:00Z",
            "url": "https://example.com/minisforum-s5-heavy-paraphrase",
        },
        title="Compact Minisforum storage box appears at Computex",
        body=(
            "A compact storage appliance from Minisforum surfaced at Computex. The system "
            "targets flash-based home-lab storage with several NVMe bays and fast Ethernet, "
            "but pricing and launch timing remain open."
        ),
    )

    # This is an intentional false negative. Heavy rewrites need semantic or embedding dedup in a later change.
    assert _jaccard(first["body"], heavy_paraphrase["body"]) < DEFAULT_DEDUP_THRESHOLD
    assert validate_signal(heavy_paraphrase, existing=[first]).accepted is True


def test_dedup_hash_still_uses_exact_title_and_body_material():
    first = valid_signal(id="hash-1", title="Same title", body="Same body")
    same_material = valid_signal(id="hash-2", title="same TITLE", body="same BODY")
    different_body = valid_signal(id="hash-3", title="Same title", body="Different body")

    assert dedup_hash(first) == dedup_hash(same_material)
    assert dedup_hash(first) != dedup_hash(different_body)


def test_signal_scenario_type_tag_routes_without_preseting_conclusion():
    result = validate_signal(valid_signal(type_tag="supply_demand_bottleneck"))

    assert result.record["route"] == "supply_demand_bottleneck"
    assert "reasoning_constraints" not in result.record


def test_signal_scenario_vague_news_is_excluded():
    signal = valid_signal(
        title="将出台有关文件",
        body="有关部门将出台相关政策，涉及相关领域。",
    )

    result = validate_signal(signal)

    assert result.accepted is False
    assert result.reason == "lightweight_triage"
    assert {"time_vague", "content_vague"}.issubset(set(result.triage_reasons))


def test_signal_scenario_passed_signal_has_no_extra_reasoning_constraints():
    result = validate_signal(valid_signal())

    assert result.accepted is True
    assert result.record["body"] == valid_signal()["body"]
    assert "must_reason_as" not in result.record


def test_signal_scenario_raw_payload_is_retained_for_schema_reprocessing():
    result = validate_signal(valid_signal(raw_payload={"headline": "original headline"}))

    assert result.record["raw_payload"] == {"headline": "original headline"}


def test_signal_scenario_market_move_origin_is_required_for_reverse_intake():
    signal = create_market_move_signal(
        signal_id="sig-market-1",
        title="A股管网板块盘后异动",
        body="管网板块成交额较 20 日均值放大 120%，盘后倒查到海外洪涝新闻。",
        source={
            "id": "market-scan",
            "name": "Market Move Scan",
            "published_at": "2026-06-09T16:00:00Z",
            "url": "https://example.com/market-move/1",
        },
        raw_payload={"move": "volume_spike"},
        trigger_reason={
            "source_strength": True,
            "quantified_impact": True,
            "cross_market_transmission": True,
            "significant_market_move": True,
            "summary": "显著异动且有量化成交额变化",
        },
    )

    result = validate_signal(signal)

    assert result.accepted is True
    assert result.record["signal_origin"] == "market_move"
    assert result.record["trigger_reason"]["summary"] == "显著异动且有量化成交额变化"


def test_signal_scenario_weak_event_trigger_is_rejected():
    signal = valid_signal(signal_origin="market_move", trigger_reason={"summary": "只有模糊异动"})

    with pytest.raises(ContractError, match="trigger_reason"):
        validate_signal(signal)


def test_thesis_scenario_freeform_narrative_is_accepted():
    thesis = create_freeform_thesis(
        thesis_id="thesis-1",
        body="厄尔尼诺内涝 -> 城市排水管网，这个判断不按固定字段顺序展开。",
        source_signal_ids=["sig-1"],
    )

    assert validate_thesis(thesis).accepted is True
    assert thesis.get("substantive_claims", []) == []


def test_thesis_scenario_freeform_body_is_not_auto_claimed():
    thesis = create_freeform_thesis(
        thesis_id="thesis-1",
        body="强降雨推升排水管网需求; 某公司可能拿到大订单。",
        source_signal_ids=["sig-1"],
    )

    result = validate_thesis(thesis)

    assert result.pending_verification_claims == []
    assert "substantive_claims" not in result.record or result.record["substantive_claims"] == []


def test_thesis_scenario_multi_claim_one_missing_source_is_pending():
    thesis = create_freeform_thesis(
        thesis_id="thesis-1",
        body="强降雨推升排水管网需求; 某公司可能拿到大订单。",
        source_signal_ids=["sig-1"],
    )
    thesis = add_substantive_claim(thesis, "强降雨推升排水管网需求", source_signal_ids=["sig-1"])
    thesis = add_substantive_claim(thesis, "某公司可能拿到大订单")

    result = validate_thesis(thesis)

    assert result.pending_verification_claims == ["某公司可能拿到大订单"]


def test_thesis_scenario_system_does_not_require_reasoning_template():
    thesis = valid_thesis()
    thesis.pop("affected_industries")

    assert validate_thesis(thesis).accepted is True


def test_thesis_scenario_freeform_does_not_require_cross_market_fields():
    thesis = create_freeform_thesis(
        thesis_id="thesis-1",
        body="海外洪涝可能带来城市排水改造需求。",
        source_signal_ids=["sig-1"],
    )

    assert validate_thesis(thesis).accepted is True


def test_thesis_scenario_cross_market_transmission_path_is_auditable():
    thesis = create_freeform_thesis(
        thesis_id="thesis-1",
        body="海外洪涝增加排水基础设施关注,反推 A股管网公司订单弹性。",
        source_signal_ids=["sig-1"],
    )
    thesis["origin_market"] = "GLOBAL"
    thesis["target_market"] = "CN-A"
    thesis = add_transmission_step(
        thesis,
        description="海外洪涝提高城市排水改造优先级",
        source_signal_ids=["sig-1"],
    )

    result = validate_thesis(thesis)

    assert result.accepted is True
    assert result.record["transmission_path"][0]["description"] == "海外洪涝提高城市排水改造优先级"


def test_thesis_scenario_completeness_critique_preserves_body():
    thesis = create_freeform_thesis(
        thesis_id="thesis-1",
        body="海外洪涝可能带来城市排水改造需求。",
        source_signal_ids=["sig-1"],
    )

    updated = create_completeness_critique(
        thesis,
        notes=["还有没有二阶影响:泵、管材、检测设备"],
        candidate_thesis_ids=["thesis-2"],
    )

    assert updated["body"] == thesis["body"]
    assert updated["completeness_critique"]["body_unchanged"] is True
    assert updated["completeness_critique"]["candidate_thesis_ids"] == ["thesis-2"]


def test_thesis_scenario_confirmed_requires_completeness_critique():
    thesis = confirmed_thesis()
    thesis.pop("completeness_critique")

    with pytest.raises(ContractError, match="completeness_critique"):
        validate_thesis(thesis)


def test_thesis_scenario_unsupported_claim_is_marked_pending_verification():
    thesis = valid_thesis(
        substantive_claims=[
            {"text": "某公司会拿到大订单", "source_signal_ids": []},
        ]
    )

    result = validate_thesis(thesis)

    assert result.accepted is True
    assert result.pending_verification_claims == ["某公司会拿到大订单"]


def test_thesis_scenario_unfalsified_thesis_cannot_be_confirmed():
    thesis = valid_thesis(
        status="confirmed",
        completeness_critique=confirmed_thesis()["completeness_critique"],
    )

    with pytest.raises(ContractError, match="adversarial_falsification"):
        validate_thesis(thesis)


def test_thesis_scenario_falsification_records_counterargument_and_hedge():
    review = create_adversarial_review(
        thesis_author_id="author-agent",
        author_persona="builder",
        reviewer_instance_id="reviewer-agent",
        reviewer_persona="skeptic",
        review_run_id="review-run-1",
        reviewer="skeptic-persona",
        strongest_counterargument="库存周期可能抵消需求增量。",
        hedge_variables=["渠道库存"],
    )
    thesis = valid_thesis(status="confirmed", adversarial_falsification=review)
    thesis["track_record"] = confirmed_thesis()["track_record"]
    thesis["completeness_critique"] = confirmed_thesis()["completeness_critique"]

    assert validate_thesis(thesis).record["adversarial_falsification"] == review


def test_thesis_scenario_same_author_and_reviewer_cannot_confirm():
    review = create_adversarial_review(
        thesis_author_id="same-agent",
        author_persona="builder",
        reviewer_instance_id="same-agent",
        reviewer_persona="skeptic",
        review_run_id="review-run-1",
        reviewer="skeptic-persona",
        strongest_counterargument="这是自导自演的反方。",
        hedge_variables=["渠道库存"],
    )
    thesis = valid_thesis(status="confirmed", adversarial_falsification=review)
    thesis["track_record"] = confirmed_thesis()["track_record"]
    thesis["completeness_critique"] = confirmed_thesis()["completeness_critique"]

    with pytest.raises(ContractError, match="independent"):
        validate_thesis(thesis)


def test_thesis_scenario_same_persona_cannot_confirm():
    review = create_adversarial_review(
        thesis_author_id="author-agent",
        author_persona="builder",
        reviewer_instance_id="reviewer-agent",
        reviewer_persona="builder",
        review_run_id="review-run-1",
        reviewer="skeptic-persona",
        strongest_counterargument="persona 没有隔离。",
        hedge_variables=["渠道库存"],
    )
    thesis = valid_thesis(status="confirmed", adversarial_falsification=review)
    thesis["track_record"] = confirmed_thesis()["track_record"]
    thesis["completeness_critique"] = confirmed_thesis()["completeness_critique"]

    with pytest.raises(ContractError, match="persona"):
        validate_thesis(thesis)


def test_thesis_scenario_confirmed_thesis_creates_track_record():
    track = create_track_record(
        direction="bullish",
        falsifiable_expectation="60 天内订单公告增多",
        verification_window={"start": "2026-06-09", "end": "2026-08-08"},
        created_at=datetime(2026, 6, 9, 8, 0, tzinfo=UTC),
    )
    thesis = confirmed_thesis(track_record=track)

    assert validate_thesis(thesis).record["track_record"]["direction"] == "bullish"


def test_thesis_scenario_track_record_result_can_be_backfilled(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    store.add_thesis(confirmed_thesis())

    store.backfill_track_record_result("thesis-1", {"actual": "orders_up", "hit": True})

    row = store.connection.execute(
        "select result_json from track_record where thesis_id = ?", ("thesis-1",)
    ).fetchone()
    assert json.loads(row["result_json"]) == {"actual": "orders_up", "hit": True}


def test_feedback_scenario_outcome_raw_does_not_auto_generate_calibration_signal():
    outcome = create_outcome_raw(
        thesis_id="thesis-1",
        observed_at="2026-06-20T08:00:00Z",
        result={"actual": "orders_not_yet_visible"},
        maturity={
            "verification_window_expired": False,
            "event_occurred": False,
            "confidence_sufficient": False,
        },
    )

    assert outcome["kind"] == "outcome_raw"
    assert create_calibration_signal(outcome) is None


def test_feedback_scenario_mature_outcome_generates_calibration_signal():
    outcome = create_outcome_raw(
        thesis_id="thesis-1",
        observed_at="2026-09-10T08:00:00Z",
        result={"actual": "orders_up", "hit": True},
        maturity={
            "verification_window_expired": True,
            "event_occurred": True,
            "confidence_sufficient": True,
        },
    )

    signal = create_calibration_signal(outcome)

    assert signal["kind"] == "calibration_signal"
    assert signal["thesis_id"] == "thesis-1"


def test_thesis_scenario_calibration_is_explicitly_not_implemented(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    with pytest.raises(CalibrationNotImplemented):
        store.calibrate()


def test_thesis_scenario_single_source_is_tagged_and_confidence_not_overstated():
    result = validate_thesis(valid_thesis(source_signal_ids=["sig-1"]))

    assert "single_source" in result.record["uncertainty_tags"]
    assert result.record["confidence"] != "high"


def test_thesis_scenario_no_source_is_tagged_and_confidence_low():
    result = validate_thesis(valid_thesis(source_signal_ids=[], confidence="high"))

    assert "no_source" in result.record["uncertainty_tags"]
    assert result.record["confidence"] == "low"


def test_target_scenario_good_company_bad_entry_is_watch_not_now_buy():
    target = valid_target(
        logic_score={"score": 95, "rationale": "强逻辑"},
        buy_point={"status": "unfavorable", "rationale": "已大涨", "price_change_since_signal": 0.6},
        state="buy-zone",
    )

    with pytest.raises(ContractError, match="buy_point"):
        validate_target(target, confirmed_thesis_ids={"thesis-1"})


def test_target_scenario_rejects_single_total_score():
    target = valid_target()
    target.pop("logic_score")
    target.pop("buy_point")
    target["total_score"] = 88

    with pytest.raises(ContractError, match="single total score"):
        validate_target(target, confirmed_thesis_ids={"thesis-1"})


def test_target_scenario_requires_target_market():
    target = valid_target()
    target.pop("target_market")

    with pytest.raises(ContractError, match="target_market"):
        validate_target(target, confirmed_thesis_ids={"thesis-1"})


def test_target_scenario_watchlist_requires_catalyst_and_exit_trigger():
    target = valid_target(catalysts=[], exit_triggers=[])

    with pytest.raises(ContractError, match="catalyst"):
        validate_target(target, confirmed_thesis_ids={"thesis-1"})


def test_target_scenario_catalyst_condition_advances_watch_to_review_required():
    target = valid_target(state="watch")

    updated = update_target_state(target, satisfied_catalysts=["政策细则"])

    assert updated["state"] == "review-required"
    assert updated["needs_review"] is True


def test_target_scenario_large_price_move_marks_priced_in_risk():
    target = valid_target(
        buy_point={"status": "neutral", "rationale": "涨幅偏大", "price_change_since_signal": 0.35},
        priced_in={"price_change_since_signal": 0.35, "risk": "unknown"},
    )

    result = validate_target(target, confirmed_thesis_ids={"thesis-1"})

    assert result.record["priced_in"]["risk"] == "high"


def test_target_scenario_rejects_target_without_confirmed_thesis_support():
    with pytest.raises(ContractError, match="confirmed thesis"):
        validate_target(valid_target(thesis_ids=[]), confirmed_thesis_ids={"thesis-1"})


def test_target_scenario_store_rejects_target_with_unconfirmed_thesis(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    store.add_thesis(valid_thesis(status="draft"))

    with pytest.raises(ContractError, match="confirmed thesis"):
        store.add_target(valid_target())


def test_target_scenario_store_accepts_target_with_confirmed_thesis(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    store.add_thesis(confirmed_thesis())

    assert store.add_target(valid_target()) == "target-1"


def test_storage_does_not_write_draft_transmission_path_to_map(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = add_transmission_step(
        valid_thesis(status="draft"),
        description="海外洪涝提高城市排水改造优先级",
        source_signal_ids=["sig-1"],
    )

    store.add_thesis(thesis)

    count = store.connection.execute("select count(*) as count from transmission_map").fetchone()["count"]
    assert count == 0


def test_storage_writes_confirmed_transmission_path_to_map(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    thesis = add_transmission_step(
        confirmed_thesis(),
        description="海外洪涝提高城市排水改造优先级",
        source_signal_ids=["sig-1"],
    )

    store.add_thesis(thesis)

    row = store.connection.execute("select description from transmission_map where thesis_id = ?", ("thesis-1",)).fetchone()
    assert row["description"] == "海外洪涝提高城市排水改造优先级"


def test_target_schema_rejects_unknown_buy_point_status():
    target = valid_target(buy_point={"status": "maybe", "rationale": "bad enum", "price_change_since_signal": 0.0})

    with pytest.raises(ContractError, match="buy_point"):
        validate_target(target, confirmed_thesis_ids={"thesis-1"})


def test_empty_recommendation_records_reason_without_targets():
    recommendation = create_empty_recommendation(
        period="2026-W24",
        reasons=["没有标的同时满足逻辑、买点和催化剂门槛"],
    )

    assert recommendation["kind"] == "empty_recommendation"
    assert recommendation["targets"] == []
    assert recommendation["reasons"] == ["没有标的同时满足逻辑、买点和催化剂门槛"]


def test_storage_creates_sqlite_tables_with_cursors_and_dedup_hash(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    tables = {
        row["name"]
        for row in store.connection.execute("select name from sqlite_master where type = 'table'")
    }
    signal_columns = {
        row["name"]
        for row in store.connection.execute("pragma table_info(signals)")
    }

    assert {
        "signals",
        "theses",
        "targets",
        "track_record",
        "source_cursors",
        "human_decisions",
        "transmission_map",
    }.issubset(tables)
    assert "dedup_hash" in signal_columns


def test_human_decision_is_stored_separately_from_track_record(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    decision = create_human_decision(
        subject_type="target",
        subject_id="target-1",
        decision="rejected",
        reason="买点不够好",
        decided_at="2026-06-09T20:00:00Z",
    )

    store.add_human_decision(decision)

    row = store.connection.execute("select decision, reason from human_decisions where subject_id = ?", ("target-1",)).fetchone()
    assert dict(row) == {"decision": "rejected", "reason": "买点不够好"}
    assert store.connection.execute("select count(*) as count from track_record").fetchone()["count"] == 0


def test_store_rejects_near_duplicate_signal_on_write_path(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    store.add_signal(valid_signal(id="sig-1", body="COD 排放标准提升 30%，预计带动 300 亿治理投资"))

    with pytest.raises(ContractError, match="near_duplicate"):
        store.add_signal(
            valid_signal(
                id="sig-2",
                source={
                    "id": "source-b",
                    "name": "Source B",
                    "published_at": "2026-06-09T09:00:00Z",
                    "url": "https://example.com/news/2",
                },
                body="COD 排放标准提升 30%，预计带动 300 亿治理投资",
            )
        )


def test_signal_triage_records_strategy_and_detects_vague_impact_without_tradable_anchors():
    signal = valid_signal(title="将出台有关文件", body="有关部门将出台相关政策，涉及相关领域。")

    result = validate_signal(signal)

    assert result.record["triage"]["strategy"] == "zh_cn_heuristic_v0"
    assert "impact_vague" in result.triage_reasons


def test_last30days_adapter_maps_agent_output_as_attention_source():
    output = json.dumps(
        [
            {
                "title": "AI 服务器交期拉长",
                "body": "交期从 4 周延长至 12 周。",
                "url": "https://example.com/ai",
                "published_at": "2026-06-09T08:00:00Z",
            }
        ]
    )

    signals = adapt_last30days_agent_output(output)

    assert signals[0]["source"]["id"] == "last30days"
    assert signals[0]["source_weight"] == "attention_only"
    assert validate_signal(signals[0]).accepted is True


def test_last30days_adapter_maps_real_emit_json_report_shape():
    output = json.dumps(
        {
            "topic": "AI server supply chain",
            "generated_at": "2026-06-09T14:00:20Z",
            "items_by_source": {
                "reddit": [
                    {
                        "candidate_id": "https://reddit.com/r/stocks/comments/example",
                        "cluster_id": "cluster-12",
                        "snippet": "Supply chain checks show AI server backlog expanded 25%.",
                        "source_items": [
                            {
                                "title": "AI server backlog expands",
                                "body": "Supply chain checks show AI server backlog expanded 25%.",
                                "url": "https://reddit.com/r/stocks/comments/example",
                                "published_at": "2026-06-08",
                                "source": "reddit",
                                "container": "stocks",
                            }
                        ],
                    }
                ]
            },
        }
    )

    signals = adapt_last30days_agent_output(output)

    assert len(signals) == 1
    assert signals[0]["source"]["url"] == "https://reddit.com/r/stocks/comments/example"
    assert signals[0]["source"]["published_at"] == "2026-06-08"
    assert signals[0]["raw_payload"]["last30days_topic"] == "AI server supply chain"
    assert signals[0]["raw_payload"]["last30days_cluster_id"] == "cluster-12"
    assert validate_signal(signals[0]).accepted is True


def test_store_validates_schema_and_invariants_before_writing(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    with pytest.raises(ContractError):
        store.add_signal(valid_signal(source={"id": "source-a", "name": "Source A"}))

    store.add_signal(valid_signal())
    count = store.connection.execute("select count(*) as count from signals").fetchone()["count"]
    assert count == 1
