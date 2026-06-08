"""TrackBee Daily Store Pulse — orchestrator.

Loads each transform / insight per store in sequence, renders one pulse card per
store from the view template, computes the portfolio header from the per-store
verdicts, and stamps the page shell.

Data is baked in at build time — the artifact makes no MCP calls at runtime. A
paired scheduled task re-runs the skill daily at 08:00 and overwrites the
artifact in place using the same id.

When a store's payload is missing or empty the card still renders: the verdict
reads "Watch — no data for yesterday yet" and each section degrades to a plain
notice instead of failing the whole build.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # components/
CHROME = HERE / "chrome"
TRANSFORMS = HERE / "transforms"
INSIGHTS = HERE / "insights"
CHARTS = HERE / "charts"
VIEWS = HERE / "views"


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _esc(s) -> str:
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def _load_raw(inputs_dir: Path, store_id: str, role: str) -> dict:
    """Load <store_id>__<role>.json, unwrapping a top-level {"result": {...}}."""
    path = inputs_dir / f"{store_id}__{role}.json"
    if not path.is_file():
        return {}
    try:
        data = _read_json(path)
    except (json.JSONDecodeError, OSError):
        return {}
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        return data["result"]
    return data if isinstance(data, dict) else {}


def _stamp(template: str, subs: dict) -> str:
    """Single-pass token substitution — replacement text is never re-scanned, so
    merchant-authored strings (store/campaign names) can't splice in later
    tokens."""
    if not subs:
        return template
    token_re = re.compile("|".join(re.escape(t) for t in subs))
    return token_re.sub(lambda m: subs[m.group(0)], template)


# ---- section renderers ------------------------------------------------------

def _render_kpis(tiles) -> str:
    out = []
    for t in tiles or []:
        out.append(
            '<div class="kpi">'
            f'<div class="kpi-label">{_esc(t["label"])}</div>'
            f'<div class="kpi-value">{_esc(t["value"])}</div>'
            '<div class="kpi-foot">'
            f'<span class="kpi-base">{_esc(t["base"])}</span>'
            f'<span class="kpi-delta {_esc(t["delta_class"])}">{_esc(t["delta_str"])}</span>'
            '</div></div>'
        )
    return "".join(out)


def _render_mtd(mtd, spark_svg, trend_label) -> str:
    parts = []
    if spark_svg:
        parts.append(
            '<div class="mtd-spark">'
            f'<span class="kpi-base">{_esc(trend_label)}</span>'
            f'{spark_svg}'
            '</div>'
        )
    rows_html = []
    for r in mtd.get("rows", []):
        if r.get("fill_pct") is None:
            bar = '<div class="mtd-bar"></div>'
            figures = '<span class="mtd-figures muted">No data to compare</span>'
            proj = ''
        else:
            bar = (
                '<div class="mtd-bar">'
                f'<div class="fill {_esc(r["kind"])}" style="width:{r["fill_pct"]}%"></div>'
                f'<div class="mtd-pace-tick" style="left:{r["tick_pct"]}%"></div>'
                '</div>'
            )
            figures = (
                f'<span class="mtd-figures">{_esc(r["actual_str"])} MTD '
                f'<span class="muted">vs {_esc(r["same_last_str"])} same days last month</span> '
                f'<span class="{_esc(r["vs_delta_class"])}">{_esc(r["vs_delta_str"])}</span></span>'
            )
            proj = (
                '<div class="mtd-proj">On pace for '
                f'<strong>{_esc(r["projected_str"])}</strong> vs {_esc(r["last_full_str"])} last month '
                f'<span class="{_esc(r["proj_delta_class"])}">{_esc(r["proj_delta_str"])}</span></div>'
            )
        rows_html.append(
            '<div class="mtd-metric">'
            f'<div class="mtd-top"><span class="mtd-name">{_esc(r["name"])}</span>{figures}</div>'
            f'{bar}{proj}</div>'
        )
    parts.append('<div class="mtd-row">' + "".join(rows_html) + '</div>')
    parts.append(f'<div class="mtd-note">{_esc(mtd.get("note"))}</div>')
    return "".join(parts)


_ATT_GLYPH = {"high": "!", "medium": "•", "low": "i"}


def _render_attention(att) -> str:
    items = att.get("items", [])
    if not items:
        return '<div class="att-empty"><span>✓</span> Nothing flagged today.</div>'
    out = []
    for i in items:
        sev = i.get("sev", "low")
        out.append(
            f'<div class="att-item sev-{_esc(sev)}">'
            f'<span class="att-icon">{_esc(_ATT_GLYPH.get(sev, "i"))}</span>'
            '<div>'
            f'<div class="att-title">{_esc(i.get("title"))}</div>'
            f'<div class="att-sowhat">{_esc(i.get("sowhat"))}</div>'
            '</div></div>'
        )
    return "".join(out)


def _render_movers(movers) -> str:
    if not movers:
        return ('<div class="mover"><div class="mover-name muted">'
                'No notable campaign spend changes since yesterday.</div></div>')
    out = []
    for m in movers:
        out.append(
            '<div class="mover">'
            '<div>'
            f'<div class="mover-name">{_esc(m["name"])}</div>'
            f'<div class="mover-platform">{_esc(m["platform"])}</div>'
            '</div>'
            '<div class="mover-delta">'
            f'<div class="mover-now">{_esc(m["now_str"])}</div>'
            f'<div class="mover-change {_esc(m["delta_class"])}">{_esc(m["delta_str"])}</div>'
            '</div></div>'
        )
    return "".join(out)


def _render_dock(items) -> str:
    out = []
    for it in items or []:
        out.append(
            f'<button type="button" class="dock-link" data-prompt="{_esc(it["prompt"])}">'
            f'<span class="dock-cmd">{_esc(it["cmd"])}</span>'
            f'<span class="dock-desc">{_esc(it["desc"])}</span>'
            '<span class="dock-cta">Open →</span>'
            '</button>'
        )
    return "".join(out)


def _render_store_chips(chips) -> str:
    out = ['<button type="button" class="store-chip active" data-store="all" aria-pressed="true">All stores</button>']
    for c in chips:
        out.append(
            f'<button type="button" class="store-chip" data-store="{_esc(c["id"])}" aria-pressed="false">'
            f'<span class="chip-dot {_esc(c["dot"])}"></span>{_esc(c["name"])}</button>'
        )
    return "".join(out)


def _render_attention_stores(attention) -> str:
    if not attention:
        return ""
    chips = []
    for a in attention:
        lvl = a.get("level", "watch")
        chips.append(
            '<span class="att-chip">'
            f'<span class="dot {_esc(lvl)}"></span>{_esc(a["name"])}</span>'
        )
    return '<div class="attention-stores">' + "".join(chips) + '</div>'


# ---- per-store card ---------------------------------------------------------

def _build_card(card_tpl, store_cfg, inputs_dir, windows, mtd_meta, baseline_days, mods):
    store_id = str(store_cfg.get("store_id"))

    # Assemble this store's raw payloads.
    campaigns = {}
    for platform in (store_cfg.get("platforms") or []):
        campaigns[platform] = {
            "yday": _load_raw(inputs_dir, store_id, f"cmp_{platform}_yday"),
            "prev": _load_raw(inputs_dir, store_id, f"cmp_{platform}_prev"),
        }
    raws = {
        "overview_yday": _load_raw(inputs_dir, store_id, "overview_yday"),
        "overview_base": _load_raw(inputs_dir, store_id, "overview_base"),
        "overview_mtd":  _load_raw(inputs_dir, store_id, "overview_mtd"),
        "overview_prev_month_mtd":  _load_raw(inputs_dir, store_id, "overview_prev_month_mtd"),
        "overview_prev_month_full": _load_raw(inputs_dir, store_id, "overview_prev_month_full"),
        "daily":         _load_raw(inputs_dir, store_id, "daily"),
        "poas_yday":     _load_raw(inputs_dir, store_id, "poas_yday"),
        "poas_base":     _load_raw(inputs_dir, store_id, "poas_base"),
        "anomalies":     _load_raw(inputs_dir, store_id, "anomalies"),
        "meta_recs":     _load_raw(inputs_dir, store_id, "meta_recs"),
        "campaigns":     campaigns,
    }

    summary = mods["loader"].normalize(store_cfg, raws, windows)
    attention = mods["attention"].build(summary)
    verdict = mods["verdict"].build_store(summary, attention, baseline_days)
    kpis = mods["kpis"].build(summary, baseline_days)
    mtd = mods["mtd"].build(summary, mtd_meta)
    movers = mods["movers"].build(summary, store_cfg.get("fx_to_store") or {})
    dock = mods["dock"].build(summary, verdict, attention)

    series = summary.get("daily_revenue") or []
    n_days = len(series)
    spark_labels = _spark_labels(n_days, windows)
    spark = mods["sparkline"].svg(series, spark_labels, summary.get("currency") or "",
                                  f"{summary['store_name']} daily revenue")
    trend_label = f"Daily revenue, trailing {n_days} days" if n_days >= 2 else ""

    subs = {
        "{STORE_ID}":       _esc(store_id),
        "{STORE_NAME}":     _esc(summary["store_name"]),
        "{VERDICT_CLASS}":  _esc(verdict["class"]),
        "{VERDICT_LABEL}":  _esc(verdict["label"]),
        "{VERDICT_WHY}":    _esc(verdict["why"]),
        "{KPI_TILES}":      _render_kpis(kpis),
        "{MTD_BLOCK}":      _render_mtd(mtd, spark, trend_label),
        "{ATTENTION_ITEMS}": _render_attention(attention),
        "{MOVERS}":         _render_movers(movers),
        "{DOCK_LINKS}":     _render_dock(dock),
    }
    card_html = _stamp(card_tpl, subs)

    return {
        "html": card_html,
        "store_name": summary["store_name"],
        "verdict": verdict,
    }


# ---- top-level build --------------------------------------------------------

def build(inputs_dir: Path, config: dict) -> str:
    shell = _read(CHROME / "shell.html")
    theme = _read(CHROME / "theme.css")
    store_filter_js = _read(CHROME / "store_filter.js")
    dock_js = _read(CHROME / "dock.js")
    spark_js = _read(CHROME / "spark.js")
    card_tpl = _read(VIEWS / "pulse_card.html")
    logos_mod = _load_module(CHROME / "logos.py")

    mods = {
        "loader":    _load_module(TRANSFORMS / "loader.py"),
        "kpis":      _load_module(TRANSFORMS / "kpis.py"),
        "mtd":       _load_module(TRANSFORMS / "mtd.py"),
        "movers":    _load_module(TRANSFORMS / "movers.py"),
        "attention": _load_module(INSIGHTS / "attention.py"),
        "verdict":   _load_module(INSIGHTS / "verdict.py"),
        "dock":      _load_module(INSIGHTS / "dock.py"),
        "sparkline": _load_module(CHARTS / "sparkline.py"),
    }

    windows = config.get("windows") or {}
    mtd_meta = {
        "days_elapsed": (config.get("mtd") or {}).get("days_elapsed"),
        "days_total":   (config.get("mtd") or {}).get("days_total"),
        "this_month_label": (config.get("mtd") or {}).get("this_month_label"),
        "prev_month_label": (config.get("mtd") or {}).get("prev_month_label"),
    }
    baseline_days = config.get("baseline_days") or 7
    stores = config.get("stores") or []
    artifact_id = config.get("artifact_id") or "trackbee-daily-store-pulse"

    cards = []
    chips = []
    verdicts = []
    for store_cfg in stores:
        card = _build_card(card_tpl, store_cfg, inputs_dir, windows, mtd_meta,
                            baseline_days, mods)
        cards.append(card["html"])
        verdicts.append({"store_name": card["store_name"], "verdict": card["verdict"]})
        chips.append({
            "id": str(store_cfg.get("store_id")),
            "name": card["store_name"],
            "dot": card["verdict"]["class"],   # ok | watch | act
        })

    portfolio = mods["verdict"].build_portfolio(verdicts)

    # Window / date labels.
    yday_w = windows.get("yesterday") or {}
    base_w = windows.get("baseline") or {}
    yesterday_label = yday_w.get("end") or yday_w.get("start") or ""
    baseline_label = (f"{base_w.get('start', '')} → {base_w.get('end', '')}".strip(" →")) or "—"
    date_pill = _date_pill(yesterday_label)
    n = len(stores)
    store_count_label = f"{n} store{'s' if n != 1 else ''}"

    if cards:
        store_cards_html = "".join(cards)
    else:
        store_cards_html = (
            '<div class="empty-state">No stores returned by <code>list_my_stores</code>. '
            'Connect a Shopify store in TrackBee and the pulse will populate here.</div>'
        )

    subs = {
        "{INLINE_THEME_CSS}":       theme,
        "{INLINE_STORE_FILTER_JS}": store_filter_js,
        "{INLINE_DOCK_JS}":         dock_js,
        "{INLINE_SPARK_JS}":        spark_js,
        "{BRAND_WORDMARK}":         logos_mod.WORDMARK,
        "{DATE_PILL}":              _esc(date_pill),
        "{ARTIFACT_ID}":            _esc(artifact_id),
        "{PORTFOLIO_HEADLINE}":     _esc(portfolio["headline"]),
        "{PORTFOLIO_VERDICT}":      portfolio["verdict"],   # intentional HTML, names pre-escaped
        "{ATTENTION_STORES}":       _render_attention_stores(portfolio["attention"]),
        "{STORE_CHIPS}":            _render_store_chips(chips),
        "{STORE_CARDS}":            store_cards_html,
        "{STORE_COUNT_LABEL}":      _esc(store_count_label),
        "{YESTERDAY_LABEL}":        _esc(yesterday_label),
        "{BASELINE_LABEL}":         _esc(baseline_label),
        "{GENERATED_DATE}":         _esc(config.get("generated_date") or dt.date.today().isoformat()),
    }
    return _stamp(shell, subs)


def _spark_labels(n: int, windows: dict) -> list:
    """Per-point date labels for the trend sparkline. The daily-stats rows carry
    no date, so labels are derived by counting back from the trend window's end
    (the most recent point is the last day). Falls back to empty when the end
    date is unparseable — the chart then labels points 'Day N'."""
    if n <= 0:
        return []
    end_iso = (windows.get("trend") or {}).get("end") \
        or (windows.get("yesterday") or {}).get("end") or ""
    try:
        end = dt.date.fromisoformat(end_iso)
    except (ValueError, TypeError):
        return []
    return [(end - dt.timedelta(days=(n - 1 - i))).strftime("%-d %b") for i in range(n)]


def _date_pill(iso_date: str) -> str:
    """Human date for the header pill, e.g. 'Tue 3 Jun 2026'. Falls back to the
    raw string if it isn't an ISO date."""
    try:
        d = dt.date.fromisoformat(iso_date)
        return "Yesterday · " + d.strftime("%a %-d %b %Y")
    except (ValueError, TypeError):
        return f"Yesterday · {iso_date}" if iso_date else "Daily pulse"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", required=False, default=None)
    args = ap.parse_args(argv)

    inputs_dir = Path(args.inputs)
    cfg_path = Path(args.config) if args.config else (inputs_dir / "config.json")
    cfg = _read_json(cfg_path)
    html_out = build(inputs_dir=inputs_dir, config=cfg)
    Path(args.out).write_text(html_out, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
