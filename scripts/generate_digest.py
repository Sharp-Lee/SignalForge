#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sqlite3
from dataclasses import dataclass
from datetime import date as date_type
from pathlib import Path
from typing import Any
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORE = PROJECT_ROOT / ".local" / "news-data" / "live-store.db"
DEFAULT_OUT_DIR = PROJECT_ROOT / ".local" / "news-data" / "digests"
DISCLAIMER = "本文为个人投资研究笔记,仅供交流参考,不构成任何投资建议;股市有风险,据此操作风险自负。"


@dataclass(frozen=True)
class DigestResult:
    markdown_path: Path
    html_path: Path
    thesis_count: int
    target_count: int


@dataclass(frozen=True)
class DigestCard:
    thesis: dict
    signals: list[dict]
    targets: list[dict]


def generate_digest(
    *,
    store_path: str | Path = DEFAULT_STORE,
    date: str | None = None,
    out_dir: str | Path = DEFAULT_OUT_DIR,
) -> DigestResult:
    digest_date = date or date_type.today().isoformat()
    store = Path(store_path).expanduser()
    output_dir = Path(out_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    cards = _load_digest_data(store, digest_date)
    markdown = _render_markdown(digest_date, cards)
    html_output = _render_html(digest_date, cards)

    markdown_path = output_dir / f"{digest_date}.md"
    html_path = output_dir / f"{digest_date}.html"
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(html_output, encoding="utf-8")
    return DigestResult(
        markdown_path=markdown_path,
        html_path=html_path,
        thesis_count=len(cards),
        target_count=sum(len(card.targets) for card in cards),
    )


def _load_digest_data(store_path: Path, digest_date: str) -> list[DigestCard]:
    if not store_path.exists():
        return []

    connection = _open_readonly(store_path)
    connection.row_factory = sqlite3.Row
    try:
        if not _has_tables(connection, {"theses", "targets", "track_record"}):
            return []
        thesis_rows = connection.execute(
            """
            select t.payload_json, tr.created_at
            from theses t
            join track_record tr on tr.thesis_id = t.id
            where substr(tr.created_at, 1, 10) = ?
            order by tr.created_at asc, t.id asc
            """,
            (digest_date,),
        ).fetchall()
        signal_rows = (
            connection.execute("select id, payload_json from signals").fetchall()
            if _has_tables(connection, {"signals"})
            else []
        )
        target_rows = connection.execute(
            """
            select payload_json
            from targets
            order by symbol asc, id asc
            """
        ).fetchall()
    finally:
        connection.close()

    signals_by_id = {row["id"]: _loads_json(row["payload_json"]) for row in signal_rows}
    targets_by_thesis: dict[str, list[dict]] = {}
    for row in target_rows:
        target = _loads_json(row["payload_json"])
        for thesis_id in target.get("thesis_ids") or []:
            targets_by_thesis.setdefault(thesis_id, []).append(target)

    cards: list[DigestCard] = []
    for row in thesis_rows:
        thesis = _loads_json(row["payload_json"])
        thesis["_digest_created_at"] = row["created_at"]
        source_ids = [value for value in thesis.get("source_signal_ids") or [] if isinstance(value, str)]
        card_signals = [signals_by_id.get(signal_id) or {"id": signal_id} for signal_id in source_ids]
        card_targets = list(targets_by_thesis.get(thesis.get("id"), []))
        card_targets.sort(key=lambda item: (-_logic_score(item), str(item.get("symbol") or "")))
        cards.append(DigestCard(thesis=thesis, signals=card_signals, targets=card_targets))
    return cards


def _open_readonly(path: Path) -> sqlite3.Connection:
    uri_path = quote(str(path.resolve()), safe="/:")
    return sqlite3.connect(f"file:{uri_path}?mode=ro", uri=True)


def _has_tables(connection: sqlite3.Connection, tables: set[str]) -> bool:
    rows = connection.execute(
        "select name from sqlite_master where type = 'table' and name in ({})".format(
            ",".join("?" for _ in tables)
        ),
        tuple(tables),
    ).fetchall()
    return {row["name"] for row in rows} == tables


def _loads_json(value: str | bytes | None) -> dict:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _render_markdown(digest_date: str, cards: list[DigestCard]) -> str:
    lines = [
        f"# SignalForge 每日研究笔记 - {digest_date}",
        "",
        f"**{DISCLAIMER}**",
        "",
        _summary_sentence(cards),
        "",
    ]

    if not cards:
        lines.extend(
            [
                "## 今日无新增",
                "",
                "今天没有新增研究逻辑,因此没有新的逻辑链路需要展开。",
                "",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    lines.extend(["## 今日逻辑链路", ""])
    for index, card in enumerate(cards, start=1):
        lines.extend(_logic_card_markdown(index, card))

    return "\n".join(lines).rstrip() + "\n"


def _logic_card_markdown(index: int, card: DigestCard) -> list[str]:
    thesis = card.thesis
    lines = [
        f"### 逻辑 {index}: {_direction_label(thesis.get('direction'))} / 信心{_confidence_label(thesis.get('confidence'))}",
        "",
        "#### 触发信息",
        "",
    ]
    lines.extend(_signals_markdown(card.signals))
    lines.extend(
        [
            "#### 世界大环境",
            "",
            _environment_context(thesis, card.signals),
            "",
            "#### 推导出的支撑逻辑",
            "",
        ]
    )
    lines.extend(_support_logic_markdown(thesis))
    lines.extend(
        [
            "#### 确认后的逻辑",
            "",
            f"- 信心: {_confidence_label(thesis.get('confidence'))}",
            f"- 逻辑摘要: {_body_summary(thesis.get('body'), max_chars=220)}",
            f"- 验证窗口: {_verification_window(thesis)}",
            "",
            "#### 最强反方观点",
            "",
            _counterargument(thesis),
            "",
            "#### 这条逻辑的观察对象",
            "",
        ]
    )
    lines.extend(_targets_markdown(card.targets))
    return lines


def _signals_markdown(signals: list[dict]) -> list[str]:
    if not signals:
        return ["- 暂无可回查的信息源记录", ""]
    lines: list[str] = []
    for signal in signals:
        source = signal.get("source") if isinstance(signal.get("source"), dict) else {}
        lines.extend(
            [
                f"- {_format_value(signal.get('title') or signal.get('id'))}",
                f"  - 来源: {_format_value(source.get('name'))}",
                f"  - 时间: {_format_value(source.get('published_at'))}",
                f"  - 链接: {_format_value(source.get('url'))}",
            ]
        )
    lines.append("")
    return lines


def _support_logic_markdown(thesis: dict) -> list[str]:
    items = _support_logic_items(thesis)
    if not items:
        return ["- 暂无单独记录的支撑逻辑", ""]
    return [f"- {item}" for item in items] + [""]


def _targets_markdown(targets: list[dict]) -> list[str]:
    if not targets:
        return ["这条逻辑暂未形成观察对象。", ""]
    lines: list[str] = []
    for target in targets:
        buy_point = target.get("buy_point") if isinstance(target.get("buy_point"), dict) else {}
        priced_in = target.get("priced_in") if isinstance(target.get("priced_in"), dict) else {}
        lines.extend(
            [
                f"- {_target_name(target)}",
                f"  - 与逻辑相关度: {_format_value(_nested(target, 'logic_score', 'score'))}",
                f"  - 信号以来涨跌幅: {_format_percent(_first_present(buy_point.get('price_change_since_signal'), priced_in.get('price_change_since_signal')))}",
                f"  - priced-in 风险: {_risk_label(priced_in.get('risk'))}",
                "  - 观察条件:",
            ]
        )
        lines.extend(_condition_items_markdown(target.get("catalysts"), "暂无观察条件"))
        lines.append("  - 失效条件:")
        lines.extend(_condition_items_markdown(target.get("exit_triggers"), "暂无失效条件"))
    lines.append("")
    return lines


def _render_html(digest_date: str, cards: list[DigestCard]) -> str:
    parts = [
        '<article style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;color:#1f2933;line-height:1.7;font-size:16px;">',
        f'<h1 style="font-size:22px;margin:0 0 12px 0;">SignalForge 每日研究笔记 - {_escape(digest_date)}</h1>',
        f'<p style="font-weight:700;color:#9f1d1d;background:#fff2f0;padding:10px 12px;border-left:4px solid #d64545;margin:0 0 16px 0;">{_escape(DISCLAIMER)}</p>',
        f'<p style="margin:0 0 18px 0;">{_escape(_summary_sentence(cards))}</p>',
    ]

    if not cards:
        parts.extend(
            [
                '<h2 style="font-size:19px;margin:20px 0 8px 0;">今日无新增</h2>',
                '<p style="margin:0 0 12px 0;">今天没有新增研究逻辑,因此没有新的逻辑链路需要展开。</p>',
                "</article>",
            ]
        )
        return "\n".join(parts)

    parts.append('<h2 style="font-size:19px;margin:20px 0 8px 0;">今日逻辑链路</h2>')
    for index, card in enumerate(cards, start=1):
        parts.append(_logic_card_html(index, card))
    parts.append("</article>")
    return "\n".join(parts)


def _logic_card_html(index: int, card: DigestCard) -> str:
    thesis = card.thesis
    return "\n".join(
        [
            '<section style="border:1px solid #d8dee4;border-radius:8px;padding:12px;margin:0 0 12px 0;">',
            f'<h3 style="font-size:17px;margin:0 0 8px 0;">逻辑 {index}: {_escape(_direction_label(thesis.get("direction")))} / 信心{_escape(_confidence_label(thesis.get("confidence")))}</h3>',
            '<h4 style="font-size:16px;margin:12px 0 4px 0;">触发信息</h4>',
            _signals_html(card.signals),
            '<h4 style="font-size:16px;margin:12px 0 4px 0;">世界大环境</h4>',
            f'<p style="margin:4px 0;">{_escape(_environment_context(thesis, card.signals))}</p>',
            '<h4 style="font-size:16px;margin:12px 0 4px 0;">推导出的支撑逻辑</h4>',
            _support_logic_html(thesis),
            '<h4 style="font-size:16px;margin:12px 0 4px 0;">确认后的逻辑</h4>',
            f'<p style="margin:4px 0;"><strong>信心:</strong> {_escape(_confidence_label(thesis.get("confidence")))}</p>',
            f'<p style="margin:4px 0;"><strong>逻辑摘要:</strong> {_escape(_body_summary(thesis.get("body"), max_chars=220))}</p>',
            f'<p style="margin:4px 0;"><strong>验证窗口:</strong> {_escape(_verification_window(thesis))}</p>',
            '<h4 style="font-size:16px;margin:12px 0 4px 0;">最强反方观点</h4>',
            f'<p style="margin:4px 0;">{_escape(_counterargument(thesis))}</p>',
            '<h4 style="font-size:16px;margin:12px 0 4px 0;">这条逻辑的观察对象</h4>',
            _targets_html(card.targets),
            "</section>",
        ]
    )


def _signals_html(signals: list[dict]) -> str:
    if not signals:
        return '<p style="margin:4px 0;">暂无可回查的信息源记录</p>'
    items = []
    for signal in signals:
        source = signal.get("source") if isinstance(signal.get("source"), dict) else {}
        items.append(
            "<li>"
            f"{_escape(_format_value(signal.get('title') or signal.get('id')))}"
            f'<div style="margin:2px 0 0 0;color:#52616b;">来源: {_escape(_format_value(source.get("name")))} | 时间: {_escape(_format_value(source.get("published_at")))} | 链接: {_escape(_format_value(source.get("url")))}</div>'
            "</li>"
        )
    return '<ul style="padding-left:18px;margin:4px 0;">' + "".join(items) + "</ul>"


def _support_logic_html(thesis: dict) -> str:
    items = _support_logic_items(thesis)
    if not items:
        return '<p style="margin:4px 0;">暂无单独记录的支撑逻辑</p>'
    return (
        '<ul style="padding-left:18px;margin:4px 0;">'
        + "".join(f"<li>{_escape(item)}</li>" for item in items)
        + "</ul>"
    )


def _targets_html(targets: list[dict]) -> str:
    if not targets:
        return '<p style="margin:4px 0;">这条逻辑暂未形成观察对象。</p>'
    items = []
    for target in targets:
        buy_point = target.get("buy_point") if isinstance(target.get("buy_point"), dict) else {}
        priced_in = target.get("priced_in") if isinstance(target.get("priced_in"), dict) else {}
        items.append(
            "<li>"
            f"{_escape(_target_name(target))}"
            f'<div style="margin:2px 0 0 0;color:#52616b;">与逻辑相关度: {_escape(_format_value(_nested(target, "logic_score", "score")))} | 信号以来涨跌幅: {_escape(_format_percent(_first_present(buy_point.get("price_change_since_signal"), priced_in.get("price_change_since_signal"))))} | priced-in 风险: {_escape(_risk_label(priced_in.get("risk")))}</div>'
            f'<div style="margin:4px 0 0 0;"><strong>观察条件:</strong>{_condition_items_html(target.get("catalysts"), "暂无观察条件")}</div>'
            f'<div style="margin:4px 0 0 0;"><strong>失效条件:</strong>{_condition_items_html(target.get("exit_triggers"), "暂无失效条件")}</div>'
            "</li>"
        )
    return '<ul style="padding-left:18px;margin:4px 0;">' + "".join(items) + "</ul>"


def _summary_sentence(cards: list[DigestCard]) -> str:
    targets = [target for card in cards for target in card.targets]
    trend = _target_trend_label(targets)
    return f"今日 {len(cards)} 条新逻辑,对应 {len(targets)} 个后续跟踪对象,{trend}。"


def _target_trend_label(targets: list[dict]) -> str:
    changes = []
    for target in targets:
        buy_point = target.get("buy_point") if isinstance(target.get("buy_point"), dict) else {}
        priced_in = target.get("priced_in") if isinstance(target.get("priced_in"), dict) else {}
        value = _first_present(buy_point.get("price_change_since_signal"), priced_in.get("price_change_since_signal"))
        if isinstance(value, (int, float)):
            changes.append(float(value))
    if not changes:
        return "名单涨跌暂无足够数据"
    average = sum(changes) / len(changes)
    if average >= 0.02:
        return "名单整体偏上涨"
    if average <= -0.02:
        return "名单整体偏回落"
    return "名单整体变化不大"


def _environment_context(thesis: dict, signals: list[dict]) -> str:
    origin = thesis.get("origin_market") or "未知来源市场"
    target = thesis.get("target_market") or "未知目标市场"
    type_tags = sorted(
        {
            str(signal.get("type_tag"))
            for signal in signals
            if isinstance(signal.get("type_tag"), str) and signal.get("type_tag")
        }
    )
    suffix = f"涉及信号类型: {', '.join(type_tags)}。" if type_tags else "涉及信号类型暂未标明。"
    return f"这条逻辑从 {origin} → {target} 的跨市场传导出发,{suffix}"


def _support_logic_items(thesis: dict) -> list[str]:
    transmission_path = thesis.get("transmission_path")
    if isinstance(transmission_path, list):
        items = [
            step.get("description", "").strip()
            for step in transmission_path
            if isinstance(step, dict) and isinstance(step.get("description"), str) and step.get("description").strip()
        ]
        if items:
            return items

    claims = thesis.get("substantive_claims")
    if isinstance(claims, list):
        return [
            claim.get("text", "").strip()
            for claim in claims
            if isinstance(claim, dict) and isinstance(claim.get("text"), str) and claim.get("text").strip()
        ]
    return []


def _body_summary(body: Any, max_chars: int = 90) -> str:
    if not isinstance(body, str) or not body.strip():
        return "暂无可展示的逻辑摘要"
    text = " ".join(body.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _counterargument(thesis: dict) -> str:
    adversarial = thesis.get("adversarial_falsification")
    if isinstance(adversarial, dict):
        value = adversarial.get("strongest_counterargument")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "暂无反方观点记录"


def _verification_window(thesis: dict) -> str:
    track = thesis.get("track_record") if isinstance(thesis.get("track_record"), dict) else {}
    window = track.get("verification_window") if isinstance(track.get("verification_window"), dict) else {}
    start = window.get("start") or "未知"
    end = window.get("end") or "未知"
    return f"{start} 至 {end}"


def _target_name(target: dict) -> str:
    name = target.get("name") or "未知公司"
    symbol = target.get("symbol") or "未知代码"
    return f"{name} ({symbol})"


def _condition_items_markdown(value: Any, empty_text: str) -> list[str]:
    descriptions = _descriptions(value)
    if not descriptions:
        return [f"    - {empty_text}"]
    return [f"    - {description}" for description in descriptions]


def _condition_items_html(value: Any, empty_text: str) -> str:
    descriptions = _descriptions(value)
    if not descriptions:
        return f'<span style="color:#52616b;"> {_escape(empty_text)}</span>'
    return (
        '<ul style="padding-left:18px;margin:2px 0;">'
        + "".join(f"<li>{_escape(description)}</li>" for description in descriptions)
        + "</ul>"
    )


def _descriptions(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    descriptions = []
    for item in value:
        if isinstance(item, dict) and isinstance(item.get("description"), str) and item["description"].strip():
            descriptions.append(item["description"].strip())
    return descriptions


def _logic_score(target: dict) -> float:
    value = _nested(target, "logic_score", "score")
    if isinstance(value, (int, float)):
        return float(value)
    return -1.0


def _nested(record: dict, *keys: str) -> Any:
    value: Any = record
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _format_percent(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "暂无"
    return f"{float(value) * 100:.2f}%"


def _format_value(value: Any) -> str:
    if value is None:
        return "暂无"
    return str(value)


def _direction_label(value: Any) -> str:
    return {
        "bullish": "看多",
        "bearish": "看空",
        "neutral": "中性",
        "mixed": "分歧",
    }.get(str(value), "未标明")


def _confidence_label(value: Any) -> str:
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
    }.get(str(value), "未标明")


def _risk_label(value: Any) -> str:
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
    }.get(str(value), "暂无")


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a daily SignalForge research digest.")
    parser.add_argument("--store", default=str(DEFAULT_STORE), help=f"SQLite store path (default: {DEFAULT_STORE})")
    parser.add_argument("--date", default=date_type.today().isoformat(), help="Digest date in YYYY-MM-DD")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help=f"Output directory (default: {DEFAULT_OUT_DIR})")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = generate_digest(store_path=args.store, date=args.date, out_dir=args.out)
    print(f"digest_date={args.date}")
    print(f"thesis_count={result.thesis_count}")
    print(f"target_count={result.target_count}")
    print(f"markdown={result.markdown_path}")
    print(f"html={result.html_path}")


if __name__ == "__main__":
    main()
