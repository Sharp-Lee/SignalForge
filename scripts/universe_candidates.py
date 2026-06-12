"""Phase-A universe candidate puller (grounding-critical, Shenwan-2021 based).

Pulls AUTHORITATIVE constituents of hand-picked Shenwan (申万) L2 industries that
sit in the AI ecosystem's power + hardware + infra chain, stamps each with the
latest total market cap, and emits a review table for HUMAN curation.

Safety property: this script NEVER writes to market_data/universe.py. It emits
review files under .local/universe/ (gitignored). No code is chosen from memory
or from an LLM; every code<->name<->industry triple is stamped by Tushare's
index_member_all / stock_basic. Curation = selecting rows from this stamped
table, nothing typed by hand.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from market_data.core import scoped_no_proxy  # noqa: E402
from market_data.universe import DEFAULT_A_SHARE_ALLOWLIST  # noqa: E402

OUT_DIR = REPO_ROOT / ".local" / "universe"
CAP_PER_L2 = 30

# Hand-picked Shenwan-2021 L2 industries for the AI ecosystem. (L1, L2, l2_code)
# Power chain (算力需要电) + AI hardware (datacenter physical) + AI infra/software.
PICKED_L2: list[tuple[str, str, str]] = [
    ("电力设备", "电网设备", "801738.SI"),
    ("电力设备", "电池", "801737.SI"),
    ("电力设备", "光伏设备", "801735.SI"),
    ("电力设备", "风电设备", "801736.SI"),
    ("电力设备", "其他电源设备Ⅱ", "801733.SI"),
    ("电力设备", "电机Ⅱ", "801731.SI"),
    ("公用事业", "电力", "801161.SI"),
    ("电子", "光学光电子", "801084.SI"),
    ("电子", "半导体", "801081.SI"),
    ("电子", "元件", "801083.SI"),
    ("电子", "电子化学品Ⅱ", "801086.SI"),
    ("通信", "通信设备", "801102.SI"),
    ("通信", "通信服务", "801223.SI"),
    ("计算机", "计算机设备", "801101.SI"),
    ("计算机", "IT服务Ⅱ", "801103.SI"),
    ("计算机", "软件开发", "801104.SI"),
]


def _recent_open_days(pro) -> list[str]:
    today = date.today()
    start = today - timedelta(days=20)
    try:
        with scoped_no_proxy():
            cal = pro.trade_cal(
                exchange="SSE", is_open="1",
                start_date=start.strftime("%Y%m%d"),
                end_date=today.strftime("%Y%m%d"),
            )
        return sorted((str(r.get("cal_date")) for r in cal.to_dict("records")), reverse=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] trade_cal failed ({exc}); skipping market cap", file=sys.stderr)
        return []


def _market_caps(pro, open_days: list[str]) -> tuple[str | None, dict[str, float]]:
    # Today's daily_basic is not posted until after close, so step back.
    for trade_date in open_days[:6]:
        try:
            with scoped_no_proxy():
                df = pro.daily_basic(trade_date=trade_date, fields="ts_code,total_mv")
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] daily_basic {trade_date} failed ({exc})", file=sys.stderr)
            continue
        caps = {
            str(r["ts_code"]): float(r["total_mv"])
            for r in (df.to_dict("records") if df is not None else [])
            if r.get("total_mv") is not None
        }
        if caps:
            return trade_date, caps
    print("[warn] no daily_basic data in recent open days", file=sys.stderr)
    return None, {}


def _is_current(row: dict) -> bool:
    out = row.get("out_date")
    return out is None or str(out).strip() in ("", "None", "nan", "NaT")


def main() -> int:
    token = os.environ.get("TUSHARE_TOKEN")
    if not token:
        print("TUSHARE_TOKEN not set (source ~/.config/news-llm/keys.env)", file=sys.stderr)
        return 2

    import tushare as ts

    pro = ts.pro_api(token)

    # Coarse stock_basic, used only to stamp the EXISTING universe for context.
    with scoped_no_proxy():
        basic = pro.stock_basic(
            exchange="", list_status="L", fields="ts_code,name,industry")
    basic_by_code = {str(r["ts_code"]): r for r in basic.to_dict("records")}
    print(f"[info] stock_basic rows: {len(basic_by_code)}")

    trade_date, caps = _market_caps(pro, _recent_open_days(pro))
    print(f"[info] trade_date={trade_date} market_caps={len(caps)}")

    existing = set(DEFAULT_A_SHARE_ALLOWLIST)
    code_to_l2: dict[str, tuple[str, str]] = {}
    members: dict[tuple[str, str, str], list[dict]] = {}
    for l1, l2, l2_code in PICKED_L2:
        try:
            with scoped_no_proxy():
                df = pro.index_member_all(l2_code=l2_code)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] index_member_all {l2} ({l2_code}) failed: {exc}", file=sys.stderr)
            members[(l1, l2, l2_code)] = []
            continue
        rows = [r for r in df.to_dict("records") if _is_current(r)]
        cleaned = []
        for r in rows:
            code = str(r.get("ts_code") or "").strip()
            name = str(r.get("name") or "").strip()
            if not code or not name:
                continue
            code_to_l2[code] = (l1, l2)
            cleaned.append({"code": code, "name": name, "l1": l1, "l2": l2,
                            "total_mv_yi": round(caps[code] / 10000.0, 1) if code in caps else None})
        members[(l1, l2, l2_code)] = cleaned
        print(f"[info] {l1}/{l2}: current members={len(cleaned)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Candidates: picked-L2 members minus existing minus ST, mktcap desc ---
    payload: dict[str, list[dict]] = {}
    for l1, l2, l2_code in PICKED_L2:
        items = [m for m in members[(l1, l2, l2_code)]
                 if m["code"] not in existing and "ST" not in m["name"].upper()]
        items.sort(key=lambda d: (-(d["total_mv_yi"] or 0.0), d["name"]))
        payload[f"{l1}/{l2}"] = items
    (OUT_DIR / "universe_candidates.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Universe 候选(申万2021 成分股,tushare 权威盖章,待 curation)\n\n",
        f"- 现有 universe {len(existing)} 只 / 市值日期 {trade_date or 'N/A'} / 每桶上限 {CAP_PER_L2}(按总市值降序)\n",
        "- 勾选你要的,我再核对每个 code↔name 落地 universe.py(运行时由 tushare 盖名)\n",
    ]
    last_l1 = None
    for l1, l2, l2_code in PICKED_L2:
        if l1 != last_l1:
            lines.append(f"\n# {l1}\n")
            last_l1 = l1
        items = payload[f"{l1}/{l2}"]
        shown = items[:CAP_PER_L2]
        trunc = "" if len(items) <= CAP_PER_L2 else f"(共 {len(items)},列前 {CAP_PER_L2})"
        lines.append(f"\n## {l2} — {len(items)} 只候选 {trunc}\n\n")
        lines.append("| 代码 | 名称 | 总市值(亿) |\n|---|---|---|\n")
        for d in shown:
            mv = "—" if not d["total_mv_yi"] else f"{d['total_mv_yi']:.0f}"
            lines.append(f"| {d['code']} | {d['name']} | {mv} |\n")
    (OUT_DIR / "universe_candidates.md").write_text("".join(lines), encoding="utf-8")

    # --- Existing-universe coverage snapshot (what 40 already cover) ---
    cov = ["# 现有 universe 覆盖快照\n\n", "| 代码 | 名称 | 申万L2/粗行业 | 总市值(亿) |\n|---|---|---|---|\n"]
    by_sector: dict[str, int] = defaultdict(int)
    for code in sorted(existing):
        name = str(basic_by_code.get(code, {}).get("name") or "?").strip()
        if code in code_to_l2:
            sector = f"{code_to_l2[code][0]}/{code_to_l2[code][1]}"
        else:
            sector = f"(粗){basic_by_code.get(code, {}).get('industry') or '?'}"
        by_sector[sector] += 1
        mv = caps.get(code)
        mvs = "—" if not mv else f"{mv / 10000.0:.0f}"
        cov.append(f"| {code} | {name} | {sector} | {mvs} |\n")
    cov.append("\n## 按板块计数\n\n| 板块 | 数量 |\n|---|---|\n")
    for sector, n in sorted(by_sector.items(), key=lambda kv: -kv[1]):
        cov.append(f"| {sector} | {n} |\n")
    (OUT_DIR / "existing_universe_coverage.md").write_text("".join(cov), encoding="utf-8")

    total = sum(len(v) for v in payload.values())
    print(f"[done] candidates: {total} across {len(PICKED_L2)} L2 industries")
    for p in ("universe_candidates.md", "existing_universe_coverage.md"):
        print(f"[out] {OUT_DIR / p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
