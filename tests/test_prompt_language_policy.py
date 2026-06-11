import json

from llm_provider import prompts


def _input_payload(prompt: str) -> dict:
    marker = "INPUT_JSON:\n"
    return json.loads(prompt.split(marker, 1)[1])


def test_system_prompts_require_simplified_chinese_prose_and_english_enums():
    for system_prompt in [
        prompts.AUTHOR_SYSTEM,
        prompts.CRITIQUE_SYSTEM,
        prompts.REVIEWER_SYSTEM,
        prompts.TARGET_SYSTEM,
    ]:
        assert "简体中文" in system_prompt
        assert "枚举" in system_prompt
        assert "direction(bullish/bearish/neutral/mixed)" in system_prompt
        assert "confidence(low/medium/high)" in system_prompt
        assert "buy_point.status(favorable/neutral/unfavorable)" in system_prompt


def test_user_prompts_repeat_simplified_chinese_and_english_enum_rules():
    reasoner_payloads = [
        _input_payload(prompts.render_reasoner_user("free_generation", {"source_signal_ids": ["sig-1"]})),
        _input_payload(prompts.render_reasoner_user("completeness_critique", {"source_signal_ids": ["sig-1"]})),
        _input_payload(prompts.render_reasoner_user("adversarial_falsification", {"source_signal_ids": ["sig-1"]})),
    ]
    target_payload = _input_payload(
        prompts.render_target_user(
            {"id": "thesis-1", "body": "test"},
            {"300308.SZ": "中际旭创"},
        )
    )

    for payload in [*reasoner_payloads, target_payload]:
        rules = "\n".join(payload["rules"])
        assert "简体中文" in rules
        assert "枚举" in rules
        assert "direction(bullish/bearish/neutral/mixed)" in rules
        assert "confidence(low/medium/high)" in rules
        assert "buy_point.status(favorable/neutral/unfavorable)" in rules
