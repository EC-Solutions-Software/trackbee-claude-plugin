"""TrackBee Growth Report — orchestrator.

Loads each transform / insight in sequence, then stamps the HTML shell.
Single window pair (current vs prior 7d). The answer narrative is merged
into the hero header so it's the first thing the viewer sees.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
import sys
import html
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
SKILL_ROOT = HERE.parent
CHROME = HERE / "chrome"
TRANSFORMS = HERE / "transforms"
INSIGHTS = HERE / "insights"


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


def _load_raw(inputs_dir: Path, name: str) -> dict:
    path = inputs_dir / name
    if not path.is_file():
        return {}
    data = _read_json(path)
    if not isinstance(data, dict):
        return {}
    if "result" in data and isinstance(data["result"], dict):
        return data["result"]
    return data


def _esc(s) -> str:
    # quote=True so the same helper is safe in both text and attribute
    # context (the metric rows stamp values into data-* attributes).
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def _render_split_items(items: list[dict]) -> str:
    out = []
    for item in items or []:
        out.append(
            '<li>'
            f'<strong>{_esc(item.get("title"))}</strong>'
            f'<div class="why">{_esc(item.get("why"))}</div>'
            '</li>'
        )
    if not out:
        out.append('<li><span class="muted">Nothing notable in this category for this window.</span></li>')
    return "".join(out)


def _render_metrics_rows(rows: list[dict]) -> str:
    out = []
    for r in rows or []:
        importance = r.get("importance") or "Medium"
        imp_cls = importance.lower()
        signal = (r.get("signal") or "flat").lower()
        out.append(
            f'<tr data-importance="{_esc(importance)}" data-signal="{_esc(signal)}">'
            f'<td><div class="metric-name">{_esc(r.get("name"))}</div></td>'
            f'<td><div class="metric-indicates">{_esc(r.get("indicates"))}</div></td>'
            f'<td><span class="imp {imp_cls}">{_esc(importance)}</span></td>'
            f'<td class="num">{_esc(r.get("value_current"))}</td>'
            f'<td class="num">{_esc(r.get("value_prior"))}</td>'
            f'<td><div class="interp">{_esc(r.get("interpretation"))}</div></td>'
            '</tr>'
        )
    return "".join(out)


def build(inputs_dir: Path, config: dict) -> str:
    # ----- Static chrome -----
    shell = _read(CHROME / "shell.html")
    theme = _read(CHROME / "theme.css")
    metric_filter_js = _read(CHROME / "metric_filter.js")
    logos_mod = _load_module(CHROME / "logos.py")

    # ----- Raw MCP payloads -----
    raws = {
        "overview_current":            _load_raw(inputs_dir, "overview_current.json"),
        "overview_prior":              _load_raw(inputs_dir, "overview_prior.json"),
        "funnel_current":              _load_raw(inputs_dir, "funnel_current.json"),
        "funnel_prior":                _load_raw(inputs_dir, "funnel_prior.json"),
        "platform_footprints_current": _load_raw(inputs_dir, "platform_footprints_current.json"),
        "meta_recommendations":        _load_raw(inputs_dir, "meta_recommendations.json"),
        "meta_campaigns":              _load_raw(inputs_dir, "meta_campaigns.json"),
        "google_campaigns":            _load_raw(inputs_dir, "google_campaigns.json"),
        "anomalies":                   _load_raw(inputs_dir, "anomalies.json"),
    }

    # ----- Exclusion note -----
    # Resolve the user-chosen campaign exclusions back to names so the report
    # can state, in plain language, which campaigns it left out. Nothing is
    # hidden silently.
    exclude = {str(x) for x in ((config.get("scope") or {}).get("exclude_campaign_ids") or [])}
    excluded_names = []
    if exclude:
        for key in ("meta_campaigns", "google_campaigns"):
            for c in ((raws.get(key) or {}).get("campaigns") or []):
                if str(c.get("campaign_id")) in exclude:
                    excluded_names.append(c.get("campaign_name") or str(c.get("campaign_id")))
    if excluded_names:
        _names = ", ".join(_esc(n) for n in excluded_names)
        exclusion_note = (f'<div class="exclusion-note">Excluded at your request: '
                          f'{len(excluded_names)} campaign(s) — {_names}.</div>')
    else:
        exclusion_note = ""

    # ----- Transforms + insights -----
    headline_mod = _load_module(TRANSFORMS / "headline_kpis.py")
    headline = headline_mod.transform(
        inputs={"overview_current": raws["overview_current"],
                "overview_prior":   raws["overview_prior"]},
        config=config,
    )

    drivers_mod = _load_module(TRANSFORMS / "drivers.py")
    drivers_payload = drivers_mod.transform(
        inputs={
            "headline":                    headline,
            "overview_current":            raws["overview_current"],
            "overview_prior":              raws["overview_prior"],
            "platform_footprints_current": raws["platform_footprints_current"],
        },
        config=config,
    )

    metrics_mod = _load_module(TRANSFORMS / "metrics_table.py")
    metrics_payload = metrics_mod.transform(
        inputs={
            "headline":                    headline,
            "overview_current":            raws["overview_current"],
            "overview_prior":              raws["overview_prior"],
            "funnel_current":              raws["funnel_current"],
            "funnel_prior":                raws["funnel_prior"],
            "platform_footprints_current": raws["platform_footprints_current"],
            "meta_recommendations":        raws["meta_recommendations"],
            "anomalies":                   raws["anomalies"],
        },
        config=config,
    )

    answer_mod = _load_module(INSIGHTS / "answer.py")
    answer = answer_mod.build(headline, drivers_payload, config, raws=raws)

    # ----- Window labels -----
    windows = config.get("windows") or {}
    cur_w = (windows.get("current") or {})
    prv_w = (windows.get("prior") or {})
    current_label = f"{cur_w.get('start', '')} → {cur_w.get('end', '')}".strip(" →")
    prior_label   = f"{prv_w.get('start', '')} → {prv_w.get('end', '')}".strip(" →")
    window_pill = f"Current 7d · {current_label}" if current_label else "Current 7d"
    current_header = f"Value · current ({current_label})" if current_label else "Value · current"
    prior_header   = f"Value · prior ({prior_label})" if prior_label else "Value · prior"

    # ----- Stamp the shell -----
    # Single-pass substitution: each placeholder is replaced exactly once and
    # replacement text is never re-scanned. This matters because some values
    # carry merchant-authored strings (campaign names, Meta free-text) that, if
    # a chained .replace() were used, could themselves contain a later token
    # like "{METRICS_ROWS}" and get the report's own HTML spliced into them.
    substitutions = {
        "{STORE_NAME}":       _esc(config.get("store_name") or ""),
        "{STORE_ID}":         _esc(config.get("store_id") or ""),
        "{INLINE_THEME_CSS}": theme,
        "{INLINE_METRIC_FILTER_JS}": metric_filter_js,
        "{BRAND_WORDMARK}":   logos_mod.WORDMARK,
        "{WINDOW_LABEL}":     _esc(window_pill),
        "{HERO_HEADLINE}":    _esc(answer["hero_headline"]),
        "{ANSWER_BLOCK}":     answer["answer_block"],
        "{WORKING_LIST}":     _render_split_items(drivers_payload.get("working") or []),
        "{BREAKING_LIST}":    _render_split_items(drivers_payload.get("breaking") or []),
        "{EXCLUSION_NOTE}":   exclusion_note,
        "{CURRENT_HEADER}":   _esc(current_header),
        "{PRIOR_HEADER}":     _esc(prior_header),
        "{METRICS_ROWS}":     _render_metrics_rows(metrics_payload.get("rows") or []),
        "{CURRENT_LABEL}":    _esc(current_label),
        "{PRIOR_LABEL}":      _esc(prior_label),
        "{GENERATED_DATE}":   dt.date.today().isoformat(),
    }
    token_re = re.compile("|".join(re.escape(token) for token in substitutions))
    # lambda return is treated literally, so replacement text is never re-parsed
    return token_re.sub(lambda m: substitutions[m.group(0)], shell)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out",    required=True)
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
