"""TrackBee Creatives Report — orchestrator.

Loads transforms, insights, and chrome components on demand and stamps
the final HTML. No transform / scoring / insight logic lives here —
this module's only job is composition.

Public entry point:

    assemble.build(inputs_dir: Path, config: dict) -> str

The thin ``scripts/build_dashboard.py`` validates the config and calls
``build`` with the parsed dict; everything else is wired up here."""

from __future__ import annotations

import datetime as dt
import html as _html
import importlib.util
import json
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent      # .../creatives-report/
CHROME = HERE / "chrome"
TRANSFORMS = HERE / "transforms"
INSIGHTS = HERE / "insights"
VIEWS = HERE / "views"


# ── Component loader ────────────────────────────────────────────────
def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_raw(inputs_dir: Path, name: str) -> dict:
    """Read ``<name>.json``; tolerate ``{"result": {...}}`` wrappers and
    missing files (returns ``{}``)."""
    p = inputs_dir / name
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    if "result" in data and isinstance(data["result"], dict):
        return data["result"]
    return data


def _load_ads_by_camp(inputs_dir: Path, store_id, key_prefix: str) -> dict:
    """Return ``dict[campaign_id] → list[ad]`` for the named prefix.

    ``key_prefix`` is ``meta_ads`` or ``google_ads`` — one file per
    spending campaign, named ``{store_id}_{key_prefix}_{campaign_id}.json``.
    Tolerates both ``{"result": {...}}``-wrapped and already-unwrapped
    payloads, like ``_load_raw`` — a strict wrapper requirement here once
    cost a field run an empty-but-"successful" dashboard."""
    out: dict = {}
    for f in sorted(inputs_dir.glob(f"{store_id}_{key_prefix}_*.json")):
        cid = f.stem.split(f"{store_id}_{key_prefix}_", 1)[1]
        raw = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            out[cid] = []
            continue
        data = raw["result"] if isinstance(raw.get("result"), dict) else raw
        out[cid] = data.get("ads") or data.get("asset_groups") or []
    # All matched files parsed to zero ads → almost certainly an input-shape
    # problem, not a store with adless campaigns. Say so on stderr instead of
    # letting the build "succeed" into an empty dashboard.
    if out and not any(out.values()):
        sys.stderr.write(
            f"\nWarning: {len(out)} {key_prefix} file(s) matched for store "
            f"{store_id} but none contained ads — check that each file holds "
            "the tool's result payload (an object with an \"ads\" or "
            "\"asset_groups\" list, wrapped in {\"result\": ...} or not).\n"
        )
    return out


# ── HTML helpers ────────────────────────────────────────────────────
STATUS_ORDER = ["SCALE", "HOLD", "REFRESH", "KILL"]
STATUS_COLOR = {"SCALE": "scale", "HOLD": "hold",
                "REFRESH": "refresh", "KILL": "kill"}


def _esc(text) -> str:
    return _html.escape(str(text or ""))


def _attr(text) -> str:
    return _html.escape(str(text or ""), quote=True)


def _subst(template: str, mapping: dict) -> str:
    """Single-pass token substitution. Replacement values are emitted
    literally and never re-scanned, so an escaped merchant string that
    happens to equal a later token (e.g. a product named ``{ROWS}`` —
    ``html.escape`` leaves braces intact) can't splice the report's own
    HTML into the page. Mirrors growth-report's hardened substitution."""
    token_re = re.compile("|".join(re.escape(t) for t in mapping))
    return token_re.sub(lambda m: mapping[m.group(0)], template)


def _td(content: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f"<td{c}>{content}</td>"


def _th(content: str, sort_key: str = "", tooltip: str = "") -> str:
    tip = f' title="{_attr(tooltip)}"' if tooltip else ""
    sk  = f' data-sort="{sort_key}"' if sort_key else ""
    ind = ('<span class="sort-ind" aria-hidden="true">'
           '<span class="ar ar-up">▲</span>'
           '<span class="ar ar-down">▼</span>'
           '</span>') if sort_key else ""
    return f'<th{sk}{tip}>{content}{ind}</th>'


AD_HEADERS = [
    ("Creative",    "name",     "Ad name + ad-set + tags"),
    ("Status",      "status",   ""),
    ("Platform",    "platform", ""),
    ("Format",      "format",   ""),
    ("Product",     "product",  "Inferred from ad-set / campaign tokens"),
    ("Audit",       "audit",    "Fatigue tag — SCALE / HOLD / REFRESH / KILL"),
    ("Spend",       "spend",    "Total spend this week"),
    ("Revenue",     "revenue",  "Attributed revenue this week"),
    ("ROAS",        "roas",     "ROAS this week"),
    ("Purchases",   "purch",    "Purchases (Meta) / conversions (Google) this week"),
    ("CTR",         "ctr",      "Click-through rate (%)"),
    ("Freq",        "freq",     "Meta only — average frequency"),
    ("NNR share",   "nnr",      "Net new reach ÷ reach (Meta only)"),
    ("CPA",         "cpa",      "Spend ÷ purchases"),
    ("New cust.",   "nc",       "New customer purchases / conversions"),
    ("Age (d)",     "age",      "Days since first active (context only)"),
]


def _status_badge(status: str) -> str:
    s = (status or "").upper()
    if s in ("ACTIVE", "ENABLED"):
        return '<span class="badge active">Active</span>'
    if s == "PAUSED":
        return '<span class="badge paused">Paused</span>'
    return f'<span class="badge other">{_esc(status or "—")}</span>'


def _render_status_mix(counts) -> str:
    parts = []
    for s in STATUS_ORDER:
        n = counts.get(s, 0)
        if n > 0:
            parts.append(f'<span class="mix-pill mix-{STATUS_COLOR[s]}">'
                          f'{s[0]}{n}</span>')
    return "".join(parts) if parts else "—"


# ── Per-store rendering ─────────────────────────────────────────────
def _render_ad_row(a: dict, sid, H) -> str:
    sym = a["sym"]
    cls = f"ad-row status-{a['status_tag'].lower()}"
    tags_html = "".join(
        f'<span class="tag-chip">{_esc(t)}</span>' for t in a["tags"]
    ) if a["tags"] else ""
    name_html = (
        f'<div class="ad-name">{_esc(H.short(a["ad_name"], 60))}</div>'
        f'<div class="ad-subline">'
        f'<span class="ad-adset">{_esc(H.short(a["adset_name"], 38))}</span>'
        f' · <span class="ad-camp">{_esc(H.short(a["campaign_name"], 38))}</span>'
        f'</div>'
        + (f'<div class="ad-tags">{tags_html}</div>' if tags_html else "")
    )
    platform = a["platform"]
    plat_label = "Meta" if platform == "meta" else "Google"
    plat_html = f'<span class="plat-badge {platform}">{plat_label}</span>'

    fmt_slug = re.sub(r"[^a-z]", "", a["format"].lower())
    fmt_html = f'<span class="fmt-chip fmt{fmt_slug}">{_esc(a["format"])}</span>'

    action = (f'<span class="act-pill act-{STATUS_COLOR[a["status_tag"]]}">'
              f'{a["status_tag"]}</span>'
              f'<div class="reason" title="{_attr(a["reason"])}">'
              f'{_esc(H.short(a["reason"], 60))}</div>')

    # A genuine 0% (audience fully exhausted — the REFRESH trigger) must
    # render as "0%", not "—". Only a missing value (Google, no reach data)
    # collapses to "—".
    nnr_share_pct = (a["nnr_share"] * 100) if a["nnr_share"] is not None else None

    return (
        f'<tr class="{cls}" data-store="{sid}" '
        f'data-platform="{platform}" data-status="{a["status_tag"]}" '
        f'data-format="{_attr(a["format"])}" '
        f'data-product="{_attr(a["product"])}" '
        f'data-name="{_attr((a["ad_name"] or "").lower())}">'
        + _td(name_html)
        + _td(_status_badge(a["status"]))
        + _td(plat_html)
        + _td(fmt_html)
        + _td(_esc(a["product"]))
        + _td(action)
        + _td(H.fmt_money(a["spend"], sym), "num")
        + _td(H.fmt_money(a["revenue"], sym), "num")
        + _td(H.fmt_float(a["roas"], 2) if a["roas"] is not None else "—",
              f"num {H.roas_class(a['roas'])}")
        + _td(H.fmt_int(a["purchases"]) if a["purchases"] is not None else "—", "num")
        + _td(H.fmt_pct(a["ctr"]), "num")
        + _td(H.fmt_float(a["frequency"], 1) if a["frequency"] is not None else "—",
              f"num {H.freq_class(a['frequency']) if a['frequency'] is not None else ''}")
        + _td(H.fmt_pct(nnr_share_pct, 0) if nnr_share_pct is not None else "—", "num")
        + _td(H.fmt_money(a["cpa"], sym, 2) if a["cpa"] is not None else "—", "num")
        + _td(H.fmt_float(a["nc"], 0) if a["nc"] is not None else "—", "num")
        + _td(H.fmt_int(a["age_days"]) if a["age_days"] is not None else "—", "num")
        + "</tr>"
    )


def _render_kpi_bar(roll: dict, n_days: int, H) -> str:
    """Five-tile store KPI bar. Markup lives in views/kpi_bar.html;
    this just marshals the pre-formatted values into the placeholders."""
    sym = roll["sym"]
    sc = roll["status_counts"]
    fatigued_n = sc.get("REFRESH", 0) + sc.get("KILL", 0)
    fatigue_cls = ("bad" if fatigued_n >= max(roll["n_ads"] * 0.3, 3)
                   else "")
    template = _read(VIEWS / "kpi_bar.html")
    return (
        template
        .replace("{N_ADS}",        H.fmt_int(roll["n_ads"]))
        .replace("{TOTAL_SPEND}",  H.fmt_money(roll["total_spend"], sym))
        .replace("{N_DAYS}",       str(n_days))
        .replace("{ROAS_CLASS}",   H.roas_class(roll["blended_roas"]))
        .replace("{BLENDED_ROAS}", H.fmt_float(roll["blended_roas"], 2))
        .replace("{TOTAL_PURCH}",  H.fmt_int(roll["total_purch"]))
        .replace("{TOTAL_REV}",    H.fmt_money(roll["total_rev"], sym))
        .replace("{FATIGUE_CLASS}", fatigue_cls)
        .replace("{FATIGUED_N}",   H.fmt_int(fatigued_n))
        .replace("{REFRESH_N}",    H.fmt_int(sc.get("REFRESH", 0)))
        .replace("{KILL_N}",       H.fmt_int(sc.get("KILL", 0)))
        # `is not None`: an all-zero-frequency store shows 0.0×, not "—".
        .replace("{FREQ_CLASS}",   H.freq_class(roll["avg_freq"]))
        .replace("{FREQ}",         H.fmt_float(roll["avg_freq"], 1) if roll["avg_freq"] is not None else "—")
        .replace("{FREQ_SUFFIX}",  "×" if roll["avg_freq"] is not None else "")
    )


def _render_grid(grid: dict, H, sym: str) -> str:
    if not grid:
        return ""
    block_tpl = _read(VIEWS / "grid_product_block.html")
    sections = []
    for product, rows in sorted(
            grid.items(),
            key=lambda kv: -sum(r["total_spend"] for r in kv[1])):
        if not rows:
            continue
        body = []
        for r in rows:
            winner_cls = "row-winner" if r.get("is_winner") else ""
            winner_pill = (' <span class="winner-pill">winner</span>'
                           if r.get("is_winner") else "")
            # Low-sample chip when N < 3 — sits next to the ad count so
            # the median figures next to it still read as "directional".
            # Winners require N >= 3 by construction so the two chips
            # never appear on the same row.
            low_sample = (' <span class="low-sample-chip" '
                          'title="Median computed from fewer than 3 '
                          'ads — read as directional.">low sample</span>'
                          if r["insufficient"] else "")
            body.append(
                f'<tr class="{winner_cls}">'
                f'<td><strong>{_esc(r["format"])}</strong>{winner_pill}</td>'
                f'<td>{H.fmt_int(r["n"])}{low_sample}</td>'
                f'<td class="num">{H.fmt_money(r["total_spend"], sym)}</td>'
                f'<td class="num">{H.fmt_int(r["total_purch"])}</td>'
                # `is not None`: a genuine 0.00 median (all-KILL cell) must
                # render as 0.00×, not be mistaken for missing data.
                f'<td class="num {H.roas_class(r["median_roas"])}">'
                f'{H.fmt_float(r["median_roas"], 2) if r["median_roas"] is not None else "—"}'
                f'{"×" if r["median_roas"] is not None else ""}</td>'
                f'<td class="num">{H.fmt_pct(r["median_ctr"]) if r["median_ctr"] is not None else "—"}</td>'
                f'<td class="num">{H.fmt_money(r["median_cpa"], sym, 2) if r["median_cpa"] is not None else "—"}</td>'
                f'<td>{_render_status_mix(r["status_counts"])}</td>'
                f'</tr>'
            )
        sections.append(_subst(block_tpl, {
            "{PRODUCT_NAME}": _esc(product),
            "{ROWS}": ''.join(body),
        }))
    return _read(VIEWS / "grid_section.html").replace(
        "{PRODUCT_BLOCKS}", ''.join(sections)
    )


def _render_recommendations(recs: list[dict]) -> str:
    if not recs:
        return ""
    card_tpl = _read(VIEWS / "rec_card.html")
    cards = []
    for r in recs:
        # r["body"] is pre-escaped at construction in
        # production_recommendations.py; _subst stamps it without re-scanning.
        cards.append(_subst(card_tpl, {
            "{KIND}":     str(r["kind"]),
            "{PRIORITY}": str(r["priority"]),
            "{HEADLINE}": _esc(r["headline"]),
            "{BODY}":     r["body"],
        }))
    return _read(VIEWS / "recommendations_section.html").replace(
        "{CARDS}", ''.join(cards)
    )


def _render_questions(qs: list[dict]) -> str:
    if not qs:
        return ""
    card_tpl = _read(VIEWS / "question_card.html")
    cards = []
    for i, q in enumerate(qs):
        plain = re.sub(r"<[^>]+>", "", q["q"])
        plain = (plain.replace("&nbsp;", " ").replace("&amp;", "&")
                 .replace("&lt;", "<").replace("&gt;", ">")
                 .replace("&quot;", '"').strip())
        cards.append(_subst(card_tpl, {
            "{Q_NUM}":   f"Q{i+1}",
            "{Q_TEXT}":  _esc(q["q"]),
            "{Q_WHY}":   _esc(q["why"]),
            "{Q_PLAIN}": _attr(plain),
        }))
    return _read(VIEWS / "questions_section.html").replace(
        "{CARDS}", ''.join(cards)
    )


def _render_anomalies(anomalies: list[dict]) -> str:
    # detect_anomalies returns store-level daily-stat z-scores, each with
    # {date, metric, value, baseline_mean, baseline_std, z_score, direction}.
    # direction is "above" / "below" (not "spike" / "drop"); there is no
    # entity_name or severity field — severity is the numeric z_score.
    if not anomalies:
        return ""
    items = []
    for an in anomalies[:5]:
        raw = str(an.get("metric") or "").replace("_", " ").strip()
        metric = _esc(raw[:1].upper() + raw[1:] if raw else "")
        direction = (an.get("direction") or "").lower()
        arrow = "↑" if direction in ("above", "spike") else (
                "↓" if direction in ("below", "drop") else "")
        z = an.get("z_score")
        try:
            severity = f"{abs(float(z)):.1f}σ {direction}".strip() if z is not None else direction
        except (TypeError, ValueError):
            severity = direction
        date = _esc(str(an.get("date") or ""))
        detail = " · ".join(p for p in (_esc(severity), date) if p)
        items.append(
            f'<li><strong>{arrow} {metric}</strong>'
            + (f' — {detail}' if detail else '')
            + '</li>'
        )
    return (
        _read(VIEWS / "anomaly_banner.html")
        .replace("{COUNT}",  str(len(anomalies)))
        .replace("{PLURAL}", "ies" if len(anomalies) != 1 else "y")
        .replace("{ITEMS}",  ''.join(items))
    )


def _render_unavailable(title: str, reason: str) -> str:
    return (
        f'<div class="data-unavailable">'
        f'  <div class="data-unavailable-title">{_esc(title)}</div>'
        f'  <div>{_esc(reason)}</div>'
        f'</div>'
    )


# ── Format date pill ────────────────────────────────────────────────
def _format_date_pill(start_str: str, end_str: str) -> str:
    s = dt.date.fromisoformat(start_str)
    e = dt.date.fromisoformat(end_str)
    n = (e - s).days + 1
    if s.year == e.year and s.month == e.month:
        r = f"{s.strftime('%b %d').replace(' 0', ' ')}–{e.strftime('%d').lstrip('0')}"
    elif s.year == e.year:
        r = f"{s.strftime('%b %d').replace(' 0', ' ')} – {e.strftime('%b %d').replace(' 0', ' ')}"
    else:
        r = f"{s.strftime('%b %d, %Y').replace(' 0', ' ')} – {e.strftime('%b %d, %Y').replace(' 0', ' ')}"
    return f"{n} days · {r}"


# ── Per-store assembly ──────────────────────────────────────────────
def _resolve_fx(account_currency: str, store_currency: str,
                  store_cfg: dict, global_fx: dict, explicit_key: str,
                  safe_float) -> float:
    """Return the multiplier that converts spend/revenue FROM
    ``account_currency`` (the ad platform's reporting currency) TO the
    store's display currency.

    Priority:
      1. ``store_cfg[explicit_key]`` — per-store override
         (``meta_fx_to_store`` / ``google_fx_to_store``).
      2. ``global_fx[account_currency]`` — the dict passed at top-level
         under ``config.fx_to_store``.
      3. ``1.0`` — when no rate is supplied and the account currency
         already matches the store currency, this is correct;
         otherwise the monetary numbers will be off but the report
         still renders. A warning sits on the orchestrator caller.
    """
    # A non-positive rate (e.g. a config typo like ``"USD": 0``) would
    # silently multiply every spend/revenue figure by 0 — zeroing ROAS and
    # scoring every ad KILL. ``safe_float`` coerces both 0 and None to 0.0,
    # so guard explicitly with ``> 0`` and fall back to the identity
    # multiplier rather than emit a zeroed report.
    explicit = store_cfg.get(explicit_key)
    if explicit is not None:
        rate = safe_float(explicit, 1.0)
        return rate if rate > 0 else 1.0
    if account_currency and store_currency and account_currency == store_currency:
        return 1.0
    if account_currency and account_currency in global_fx:
        rate = safe_float(global_fx[account_currency], 1.0)
        return rate if rate > 0 else 1.0
    return 1.0


def _build_store(store_cfg: dict, inputs_dir: Path, window_end,
                  scope: dict, helpers, modules) -> dict:
    """Take one store_cfg block plus the global scope and produce its
    fully populated store dict (KPIs + ad list + sections)."""
    sid = store_cfg["id"]
    store_currency = (store_cfg.get("currency")
                       or modules.get("store_currency")
                       or "")
    sym = store_cfg.get("currency_symbol") or helpers.currency_symbol_for(store_currency)

    global_fx = modules["fx_default"] or {}
    meta_acct = (store_cfg.get("meta_account_currency")
                  or store_currency)
    goog_acct = (store_cfg.get("google_account_currency")
                  or store_currency)
    m_fx = _resolve_fx(meta_acct, store_currency, store_cfg, global_fx,
                       "meta_fx_to_store", helpers.safe_float)
    g_fx = _resolve_fx(goog_acct, store_currency, store_cfg, global_fx,
                       "google_fx_to_store", helpers.safe_float)
    name = store_cfg["name"]

    meta_raw = _load_raw(inputs_dir, f"{sid}_meta.json")
    goog_raw = _load_raw(inputs_dir, f"{sid}_google.json")
    anom_raw = _load_raw(inputs_dir, f"{sid}_anomalies.json")

    meta_campaigns = meta_raw.get("campaigns") or []
    goog_campaigns = goog_raw.get("campaigns") or []

    meta_full = _load_ads_by_camp(inputs_dir, sid, "meta_ads")
    goog_full = _load_ads_by_camp(inputs_dir, sid, "google_ads")

    exclude = set(str(x) for x in (scope.get("exclude_campaign_ids") or []))
    platforms = set(scope.get("platforms") or ["meta", "google"])
    focus = (scope.get("product_focus") or "").strip() or None

    ads: list[dict] = []
    ap = modules["ad_processing"]

    # Resolve user-chosen exclusions to names from the campaign-level files
    # (always fetched in Phase 1). NOT from the ad files: those are only
    # fetched for kept campaigns, so an excluded campaign has no ad file to
    # read — deriving the note here keeps the banner correct either way.
    excluded_campaigns: list = []
    for c in (*meta_campaigns, *goog_campaigns):
        if str(c.get("campaign_id") or "") in exclude:
            excluded_campaigns.append(
                {"name": c.get("campaign_name") or str(c.get("campaign_id"))})

    # Both platforms iterate the ad files (authoritative for ad inclusion)
    # and apply the campaign spend-gate identically: skip a campaign only
    # when it is present in the campaigns file with spend <= 0. Campaigns
    # missing from that file (SKILL.md fetches only the top spenders) keep
    # their ads rather than dropping them silently.
    if "meta" in platforms:
        camp_by_id = {str(c.get("campaign_id") or ""): c for c in meta_campaigns}
        for cid, lst in meta_full.items():
            if cid in exclude:
                continue  # excluded; the note is built from campaign files above
            c = camp_by_id.get(cid, {"campaign_id": cid, "campaign_name": ""})
            if cid in camp_by_id and helpers.safe_float(c.get("spend")) <= 0:
                continue
            for a in lst:
                processed = ap.process_meta_ad(a, m_fx, sym, window_end, focus)
                processed["campaign_name"] = a.get("campaign_name") or c.get("campaign_name") or ""
                processed["campaign_id"] = cid
                ads.append(processed)

    if "google" in platforms:
        camp_by_id = {str(c.get("campaign_id") or ""): c for c in goog_campaigns}
        for cid, lst in goog_full.items():
            if cid in exclude:
                continue  # excluded; the note is built from campaign files above
            campaign = camp_by_id.get(cid,
                                       {"campaign_id": cid, "campaign_name": "",
                                        "campaign_type": ""})
            if cid in camp_by_id and helpers.safe_float(campaign.get("spend")) <= 0:
                continue
            for a in lst:
                processed = ap.process_google_ad(a, campaign, g_fx, sym, window_end, focus)
                ads.append(processed)

    return {
        "id":         sid,
        "name":       name,
        "sym":        sym,
        "ads":        ads,
        "excluded":   excluded_campaigns,
        "anomalies":  anom_raw.get("anomalies") or [],
    }


# ── Public entry ────────────────────────────────────────────────────
def build(inputs_dir: Path, config: dict) -> str:
    # Resolve component modules once
    helpers = _load_module(CHROME / "format_helpers.py")
    ad_processing = _load_module(TRANSFORMS / "ad_processing.py")
    store_rollups = _load_module(TRANSFORMS / "store_rollups.py")
    product_format_grid = _load_module(TRANSFORMS / "product_format_grid.py")
    production_recs = _load_module(INSIGHTS / "production_recommendations.py")
    next_questions = _load_module(INSIGHTS / "next_questions.py")
    logos = _load_module(CHROME / "logos.py")

    modules = {
        "ad_processing": ad_processing,
        "fx_default":    config.get("fx_to_store") or {},
        "store_currency": config.get("store_currency", ""),
    }

    window = config["window"]
    w_start = dt.date.fromisoformat(window["start"])
    w_end   = dt.date.fromisoformat(window["end"])
    n_days = (w_end - w_start).days + 1

    # Stores config: prefer explicit `stores` list; fall back to a
    # synthesised single-store entry from store_name / store_currency.
    stores_cfg = config.get("stores") or [{
        "id":   1,
        "name": config["store_name"],
        "currency": config["store_currency"],
        "currency_symbol": helpers.currency_symbol_for(config["store_currency"]),
    }]
    scope = config.get("scope") or {}

    rendered_stores: list[dict] = []
    all_excluded: list = []
    for sc in stores_cfg:
        store = _build_store(sc, inputs_dir, w_end, scope, helpers, modules)
        all_excluded.extend(store.get("excluded") or [])
        ads = sorted(store["ads"], key=lambda a: -a["spend"])

        rollup = store_rollups.rollups(store)
        grid = product_format_grid.grid(ads)
        recs = production_recs.recommendations(store, n_days)
        qs = next_questions.questions(store)

        # KPI tiles
        tiles_html = _render_kpi_bar(rollup, n_days, helpers)
        # Anomalies banner
        anomalies_html = _render_anomalies(store["anomalies"])

        # Status chips
        sc_counts = rollup["status_counts"]
        chips = ['<div class="status-chips">']
        chips.append(f'<button class="chip active" data-action="filter-status" '
                     f'data-status="all" data-sid="{store["id"]}">'
                     f'All ({helpers.fmt_int(rollup["n_ads"])})</button>')
        for s in STATUS_ORDER:
            n = sc_counts.get(s, 0)
            chips.append(f'<button class="chip chip-{STATUS_COLOR[s]}" '
                          f'data-action="filter-status" '
                          f'data-status="{s}" data-sid="{store["id"]}">'
                          f'{s} ({helpers.fmt_int(n)})</button>')
        chips.append('</div>')
        chips_html = "".join(chips)

        # Ad table
        if ads:
            thead = "<tr>" + "".join(_th(h, sk, tip)
                                      for h, sk, tip in AD_HEADERS) + "</tr>"
            rows = "\n".join(_render_ad_row(a, store["id"], helpers)
                              for a in ads)
            unique_formats = sorted({a["format"] for a in ads})
            fmt_opts = "".join(f'<option value="{_attr(f)}">{_esc(f)}</option>'
                                for f in unique_formats)
            sid = store["id"]
            table_html = _subst(_read(VIEWS / "table.html"), {
                "{FMT_OPTS}": fmt_opts,
                "{THEAD}":    thead,
                "{ROWS}":     rows,
                "{SID}":      str(sid),
            })
        else:
            table_html = _render_unavailable(
                "No ad-level data for this store",
                "The audit could not load any ads for this store and "
                "window — check that the store is connected and that "
                "at least one ad account has tracked spend.",
            )

        # Grid / recs / questions (no lifetime section in 7-day snapshot mode)
        grid_html = _render_grid(grid, helpers, store["sym"])
        rec_html = _render_recommendations(recs)
        questions_html = _render_questions(qs)

        rendered_stores.append({
            "id":        store["id"],
            "name":      store["name"],
            "tiles":     tiles_html,
            "chips":     chips_html,
            "anomalies": anomalies_html,
            "table":     table_html,
            "grid":      grid_html,
            "recs":      rec_html,
            "questions": questions_html,
        })

    # Exclusion note — a visible, plain-language summary of any campaigns
    # the user chose to drop, so the report never silently hides ads.
    if all_excluded:
        n_camp = len(all_excluded)
        names = ", ".join(_esc(e["name"]) for e in all_excluded)
        exclusion_note = (f'<div class="exclusion-note">Excluded at your request: '
                          f'{n_camp} campaign(s) — {names}. '
                          f'These campaigns are not scored.</div>')
    else:
        exclusion_note = ""

    # Header / footer chrome
    date_label = window.get("label",
                              f"{window['start']} → {window['end']}")
    generated_date = dt.datetime.now().strftime("%b %d, %Y %H:%M")
    date_pill = _format_date_pill(window["start"], window["end"])

    nav_tabs = "".join(
        f'<button class="store-tab" data-action="switch-store" '
        f'data-sid="{rs["id"]}">'
        f'{_esc(rs["name"])}</button>'
        for rs in rendered_stores
    )

    section_tpl = _read(VIEWS / "store_section.html")
    sections_html = ""
    for rs in rendered_stores:
        sections_html += _subst(section_tpl, {
            "{STORE_ID}":  str(rs["id"]),
            "{KPI_BAR}":   rs["tiles"],
            "{ANOMALIES}": rs["anomalies"],
            "{CHIPS}":     rs["chips"],
            "{TABLE}":     rs["table"],
            "{GRID}":      rs["grid"],
            "{RECS}":      rs["recs"],
            "{QUESTIONS}": rs["questions"],
        })

    # Stamp into the shell
    shell = _read(CHROME / "shell.html")
    theme = _read(CHROME / "theme.css")
    format_helpers_js = _read(CHROME / "render_formatters.js")
    table_filters_js = _read(CHROME / "table_filters.js")

    html = _subst(shell, {
        "{STORE_NAME}": _esc(config["store_name"]),
        "{INLINE_THEME_CSS}": theme,
        "{INLINE_FORMAT_HELPERS_JS}": format_helpers_js,
        "{INLINE_TABLE_FILTERS_JS}": table_filters_js,
        "{LOGO_HTML}": logos.header_logo_html(),
        "{DATE_PILL}": _esc(date_pill),
        "{DATE_LABEL}": _esc(date_label),
        "{GENERATED_DATE}": _esc(generated_date),
        "{EXCLUSION_NOTE}": exclusion_note,
        "{NAV_TABS}": nav_tabs,
        "{STORE_SECTIONS}": sections_html,
    })
    return html
