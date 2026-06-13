from __future__ import annotations

from dataclasses import dataclass

from .prompts import CHOKEPOINT_MATCH_SYSTEM, render_chokepoint_match_user
from .schemas import CHOKEPOINT_MATCH_SCHEMA
from .transport import Completion
from .validation import enforce_chokepoint_match_output


@dataclass(frozen=True)
class ChokepointMatch:
    node: str
    reason: str


class LlmChokepointMatcher:
    def __init__(self, transport: Completion, max_tokens: int = 1400):
        self.transport = transport
        self.max_tokens = max_tokens

    def match(self, thesis: dict, *, signals: list[dict], nodes: list[dict]) -> list[ChokepointMatch]:
        output = self.transport(
            system=CHOKEPOINT_MATCH_SYSTEM,
            user=render_chokepoint_match_user(thesis=thesis, signals=signals, nodes=nodes),
            schema=CHOKEPOINT_MATCH_SCHEMA,
            max_tokens=self.max_tokens,
            thinking=None,
        )
        allowed = {node["node"] for node in nodes}
        matched = enforce_chokepoint_match_output(output, allowed)
        return [ChokepointMatch(item["node"], item["reason"]) for item in matched]
