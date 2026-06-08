"""Creatives Report — ad processing.

Take raw ``tool__get_meta_ad_insights`` / ``tool__get_google_ad_insights`` rows for
the last 7 days and produce the unified per-ad records the rest of the
pipeline consumes. No prior-period slice — the audit is by design a
pure 7-day snapshot, so fatigue scoring uses absolute thresholds
only.

Inputs are mutated only in the sense that we read out the fields we
care about — we don't write back. The unified record shape is
documented at the bottom of this module."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path


_HERE = Path(__file__).resolve().parent
_CHROME = _HERE.parent / "chrome"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_H = _load("format_helpers", _CHROME / "format_helpers.py")
_F = _load("fatigue_scoring", _HERE / "fatigue_scoring.py")

safe_float = _H.safe_float
parse_date = _H.parse_date


# ── Format detection ────────────────────────────────────────────────
def meta_format(ad: dict) -> str:
    """Classify a Meta ad's creative format.

    The MCP attaches the creative as a nested ``ad["creative"]`` object and
    exposes the format there as SINGLE_IMAGE / DYNAMIC_CREATIVE / VIDEO /
    CAROUSEL — there is no flat ``creative_format`` field. Dynamic-creative
    ads mix assets, so classify them by whether a video is present. When the
    creative wasn't merged (older payloads, lookup miss), fall back to the
    presence of a video id or image url."""
    creative = ad.get("creative") or {}
    fmt = (creative.get("format") or "").upper()
    if fmt == "VIDEO":
        return "Video"
    if fmt == "CAROUSEL":
        return "Carousel"
    if fmt == "SINGLE_IMAGE":
        return "Static"
    if fmt == "DYNAMIC_CREATIVE":
        return "Video" if creative.get("video_id") else "Static"
    if creative.get("video_id"):
        return "Video"
    if creative.get("image_url") or creative.get("thumbnail_url"):
        return "Static"
    return "Other"


def google_format(campaign_type: str | None) -> str:
    if campaign_type == "PERFORMANCE_MAX":
        return "PMAX"
    if campaign_type == "SHOPPING":
        return "Shopping Feed"
    if campaign_type == "SEARCH":
        return "Search Text"
    if campaign_type == "DEMAND_GEN":
        return "Demand Gen"
    # Title-case any other type and turn underscores into spaces so a raw
    # enum like DISPLAY_VIDEO never renders as "Display_Video".
    return (campaign_type or "Other").replace("_", " ").title()


# ── Product inference ──────────────────────────────────────────────
_BRACKET_RE = re.compile(r"\[([^\]]+)\]")
# Short uppercase code (2-4 chars) + product, e.g. PRO-Tee / BR-Hoodie.
# Deliberately NOT {2,}: that matched full words like "BEFORE-AFTER" and
# returned "AFTER" as a product.
_PREFIX_RE  = re.compile(r"^([A-Z]{2,4}-[A-Za-z]+)")
_PIPE_RE    = re.compile(r"\s*\|\s*")
_DATE_RE    = re.compile(r"^[<>]?\s*\d{1,2}\s*[/.\-]\s*\d{1,2}")
# Ad-ops structural tokens that are never a product. Matched per word
# (case-insensitive), so "Hooks re-test" is rejected via "test".
_STRUCTURAL_WORDS = {
    "test", "testing", "broad", "prospecting", "retargeting", "remarketing",
    "mix", "advertorial", "manual", "sales", "performance", "assets",
    "asc", "abo", "cbo", "dpa", "lla", "tof", "mof", "bof", "bau", "scaling",
}


def _looks_like_product(token: str) -> bool:
    """True when a free-form name segment plausibly names a product, not a
    date (``<1/6``), a campaign code (``04.01``), an acronym (``ABO``), or an
    ad-ops structural word (``Sales``, ``Assets``, ``Broad``)."""
    t = (token or "").strip()
    if len(t) < 3:
        return False                       # too short / acronyms like "ON"
    if t[0] in "<>" or _DATE_RE.match(t):
        return False                       # "<1/6", "25/5", "01-06"
    if re.match(r"^\d", t):
        return False                       # campaign codes "04.01"
    if not re.search(r"[A-Za-z]", t):
        return False                       # pure number / punctuation
    if t.isupper() and len(t) <= 5:
        return False                       # acronyms ABO / CBO / PMAX
    words = {w for w in re.split(r"[^A-Za-z0-9]+", t.lower()) if w}
    if words & _STRUCTURAL_WORDS:
        return False                       # contains a structural token
    return True


def infer_product(ad_name: str | None, adset_name: str | None,
                   campaign_name: str | None, focus: str | None = None) -> str:
    """Return a product label inferred from ad / ad-set / campaign names.

    Priority:
      1. ``focus`` override — explicit user-supplied product label.
      2. Bracketed tokens like ``[Hoodie]`` (explicit — trusted as-is).
      3. ``PREFIX-Product`` pattern like ``PRO-Tee`` (short code prefix).
      4. Middle segment of a 3+ part pipe name (``BR | Hoodie | Cold``).
    Inferred candidates from (3) and (4) must pass ``_looks_like_product``
    so operational names (dates, codes, ad-ops jargon) don't masquerade as
    products. Anything that matches none of these → ``"Uncategorised"``
    (per dashboard-spec §3)."""
    # Coerce to str at the boundary: a name field can arrive non-string
    # (e.g. a numeric id echoed as a name), which would crash the regex below.
    sources = [str(adset_name or ""), str(campaign_name or ""), str(ad_name or "")]

    if focus:
        flow = focus.lower()
        for s in sources:
            if flow in (s or "").lower():
                return focus

    for s in sources:
        m = _BRACKET_RE.search(s or "")
        if m:
            return m.group(1).strip()

    for s in sources:
        m = _PREFIX_RE.match(s or "")
        if m:
            cand = m.group(1).split("-", 1)[1].strip()
            if _looks_like_product(cand):
                return cand

    # Pipe convention is `<structure> | <Product> | <targeting>` — the
    # product sits in the MIDDLE of a 3+ part name. A 2-part name almost
    # never puts the product last (it's usually `<name> | <date/code>`), so
    # don't guess from it.
    for s in sources:
        parts = [p.strip() for p in _PIPE_RE.split(s or "") if p.strip()]
        if len(parts) >= 3 and _looks_like_product(parts[1]):
            return parts[1]

    return "Uncategorised"


# ── Per-platform processing ────────────────────────────────────────
def process_meta_ad(ad: dict, m_fx: float, sym: str, window_end,
                     focus: str | None = None) -> dict:
    spend     = safe_float(ad.get("spend")) * m_fx
    reach     = safe_float(ad.get("reach"))
    impr      = safe_float(ad.get("impressions"))
    # Missing frequency stays None (renders "—", excluded from the median);
    # a present 0.0 is a real value and renders 0.0×.
    freq_raw  = ad.get("frequency")
    freq      = safe_float(freq_raw) if freq_raw is not None else None
    cpm       = safe_float(ad.get("cpm")) * m_fx
    ctr       = safe_float(ad.get("ctr"))
    cpc       = safe_float(ad.get("cpc")) * m_fx
    clicks    = safe_float(ad.get("clicks"))
    atc       = safe_float(ad.get("add_to_carts"))
    purchases = safe_float(ad.get("purchases"))
    revenue   = safe_float(ad.get("revenue_1d_click")) * m_fx
    # Align with the Google path: a zero-spend ad has no defined ROAS, so leave
    # it absent (None → "—") rather than rendering 0.00.
    roas      = safe_float(ad.get("purchase_roas")) if spend > 0 else None
    nnr_raw   = ad.get("net_new_reach")
    nnr       = safe_float(nnr_raw)
    p1d       = safe_float(ad.get("purchases_1d_click"))
    p28d      = safe_float(ad.get("purchases_28d_click"))
    # Like net_new_reach below: missing new-customer data must stay None
    # (renders "—", never tags "retargeting only"); only a present value —
    # including a genuine 0 — feeds the acquisition-fade tag.
    nc_raw    = ad.get("new_customer_purchases")
    nc        = safe_float(nc_raw) if nc_raw is not None else None
    nc_rev    = safe_float(ad.get("new_customer_revenue")) * m_fx
    cpa       = (spend / purchases) if purchases > 0 else None
    # A missing net_new_reach must stay None (renders "—", never scores
    # REFRESH); only a present value — including a genuine 0, the
    # audience-exhausted REFRESH trigger — yields a share.
    nnr_share = (nnr / reach) if (nnr_raw is not None and reach > 0) else None

    first_active = (parse_date(ad.get("first_active_date"))
                    or parse_date(ad.get("created_time")))
    age_days = None
    if first_active and window_end:
        age_days = max(0, (window_end - first_active).days)

    fmt = meta_format(ad)
    creative = ad.get("creative") or {}
    metrics = {
        "spend": spend, "roas": roas, "frequency": freq, "ctr": ctr,
        "purchases": purchases, "nnr_share": nnr_share, "reach": reach,
        "p_1d_click": p1d, "p_28d_click": p28d, "new_customers": nc,
    }
    scored = _F.score_ad(metrics, "meta")

    product = infer_product(
        ad.get("ad_name"),
        ad.get("adset_name"),
        ad.get("campaign_name"),
        focus,
    )

    return {
        "platform":     "meta",
        "ad_id":        str(ad.get("ad_id") or ad.get("id") or ""),
        "ad_name":      ad.get("ad_name") or "(unnamed)",
        "adset_name":   ad.get("adset_name") or "",
        "campaign_id":  str(ad.get("campaign_id") or ""),
        "campaign_name": ad.get("campaign_name") or "",
        "status":       ad.get("effective_status") or "",
        "format":       fmt,
        "thumbnail":    creative.get("thumbnail_url") or creative.get("image_url") or "",
        "body":         creative.get("primary_text") or "",
        "title":        creative.get("headline") or "",
        "spend":        spend,
        "reach":        reach,
        "impressions":  impr,
        "frequency":    freq,
        "cpm":          cpm,
        "ctr":          ctr,
        "cpc":          cpc,
        "clicks":       clicks,
        "atc":          atc,
        "purchases":    purchases,
        "revenue":      revenue,
        "roas":         roas,
        "cpa":          cpa,
        "nnr":          nnr,
        "nnr_share":    nnr_share,
        "p_1d_click":   p1d,
        "p_28d_click":  p28d,
        "nc":           nc,
        "nc_revenue":   nc_rev,
        "first_active": first_active.isoformat() if first_active else None,
        "age_days":     age_days,
        "status_tag":   scored["status"],
        "reason":       scored["reason"],
        "tags":         scored["tags"],
        "product":      product,
        "sym":          sym,
    }


def process_google_ad(ad: dict, campaign: dict, g_fx: float, sym: str,
                       window_end, focus: str | None = None) -> dict:
    # Detect PMAX from the ad payload itself — an asset group with no
    # per-asset spend. The campaign may be missing from the campaigns
    # file (SKILL.md fetches only the top spending campaigns), so its
    # ``campaign_type`` can't be relied on here.
    is_pmax = "asset_group_name" in ad and "spend" not in ad
    spend     = safe_float(ad.get("spend")) * g_fx
    impr      = safe_float(ad.get("impressions"))
    clicks    = safe_float(ad.get("clicks"))
    # Compute CTR from clicks / impressions rather than trusting the
    # API's `ctr` field — Google returns it as a fraction in some
    # responses and a percentage in others, so derive it ourselves.
    ctr       = (clicks / impr * 100) if impr > 0 else 0.0
    cpc       = safe_float(ad.get("average_cpc")) * g_fx
    cpm       = safe_float(ad.get("average_cpm")) * g_fx
    conv      = safe_float(ad.get("conversions"))
    # Google reports fractional conversions. Round once here so the displayed
    # per-ad purchases and the KPI rollup (store_rollups sums this same field)
    # reconcile — summing raw fractionals then truncating each row would make
    # the rows fail to add up to the total. Keep `conv` raw for CPA / scoring.
    purchases_rounded = round(conv)
    conv_val  = safe_float(ad.get("conversions_value")) * g_fx
    # Zero-spend ads have no defined ROAS — leave it absent (None → "—") rather
    # than 0.00, which would misrepresent an ad with positive attributed revenue
    # but no spend as a total loss.
    roas      = (conv_val / spend) if spend > 0 else None
    # Keep missing new-customer data as None — see the Meta path above.
    nc_raw    = ad.get("new_customer_conversions")
    nc        = safe_float(nc_raw) if nc_raw is not None else None
    nc_rev    = safe_float(ad.get("new_customer_conversions_value")) * g_fx
    cpa       = (spend / conv) if conv > 0 else None

    first_active = (parse_date(ad.get("start_date"))
                    or parse_date(ad.get("created_time")))
    age_days = None
    if first_active and window_end:
        age_days = max(0, (window_end - first_active).days)

    fmt = "PMAX" if is_pmax else google_format(campaign.get("campaign_type"))

    if is_pmax:
        ad_name = ad.get("asset_group_name") or "Asset Group"
        body    = " · ".join((ad.get("headlines") or [])[:2]) or ""
        title   = ", ".join((ad.get("descriptions") or [])[:1])
        # Exclude PMAX asset groups from fatigue scoring — no per-asset spend
        scored = {"status": "HOLD",
                  "reason": "PMAX asset group — no per-asset spend.",
                  "tags": ["pmax"]}
    else:
        ad_name = ad.get("ad_name") or str(ad.get("ad_id") or "Ad")
        body    = " · ".join((ad.get("headlines") or [])[:2])
        title   = ", ".join((ad.get("descriptions") or [])[:1])
        # WARNING — Google has no Meta-only signals (frequency, net-new-reach,
        # 1d/28d click splits), so we stuff zero sentinels to satisfy score_ad.
        # This is a load-bearing coupling: nnr_share=0 PASSES the NNR-collapse
        # REFRESH gate's `0 <= nnr_share < 0.10`; the ONLY thing stopping a
        # false REFRESH on every Google ad is reach=0 failing the `reach > 1000`
        # check in the same branch. Do NOT replace the reach sentinel with a
        # real value (e.g. impressions) and do NOT reuse this zero-stuffing
        # pattern for another platform — switch to None sentinels + explicit
        # absence handling in score_ad first (deferred follow-up).
        metrics = {
            "spend": spend, "roas": roas, "frequency": 0, "ctr": ctr,
            "purchases": conv, "nnr_share": 0, "reach": 0,
            "p_1d_click": 0, "p_28d_click": 0, "new_customers": nc,
        }
        scored = _F.score_ad(metrics, "google")

    product = infer_product(
        ad.get("ad_name") or ad.get("asset_group_name"),
        ad.get("ad_group_name"),
        campaign.get("campaign_name"),
        focus,
    )

    return {
        "platform":     "google",
        "ad_id":        str(ad.get("ad_id") or ad.get("asset_group_id") or ""),
        "ad_name":      ad_name,
        "adset_name":   ad.get("ad_group_name") or "",
        "campaign_id":  str(campaign.get("campaign_id") or ""),
        "campaign_name": campaign.get("campaign_name") or "",
        "campaign_type": campaign.get("campaign_type") or "",
        # Google ad rows expose `ad_status` (not `effective_status`, which is
        # Meta's field). Fall back to the campaign status / effective_status
        # for safety across payload shapes.
        "status":       (ad.get("ad_status") or ad.get("effective_status")
                          or campaign.get("campaign_status") or ""),
        "format":       fmt,
        "thumbnail":    "",
        "body":         body,
        "title":        title,
        "spend":        spend,
        "reach":        None,
        "impressions":  impr,
        "frequency":    None,
        "cpm":          cpm,
        "ctr":          ctr,
        "cpc":          cpc,
        "clicks":       clicks,
        "atc":          None,
        "purchases":    purchases_rounded,
        "revenue":      conv_val,
        "roas":         roas,
        "cpa":          cpa,
        "nnr":          None,
        "nnr_share":    None,
        "p_1d_click":   None,
        "p_28d_click":  None,
        "nc":           nc,
        "nc_revenue":   nc_rev,
        "first_active": first_active.isoformat() if first_active else None,
        "age_days":     age_days,
        "status_tag":   scored["status"],
        "reason":       scored["reason"],
        "tags":         scored["tags"],
        "product":      product,
        "is_pmax":      is_pmax,
        "sym":          sym,
    }


# ── Unified ad record shape (output of process_*_ad) ───────────────
# {
#   platform:        "meta" | "google",
#   ad_id:           str,
#   ad_name, adset_name, campaign_id, campaign_name:  str,
#   status:          str (effective_status from the platform),
#   format:          "Video" | "Static" | "Carousel" | "Collection" |
#                    "Search Text" | "Shopping Feed" | "PMAX" | "Other",
#   spend, reach, impressions, frequency, cpm, ctr, cpc,
#   clicks, atc, purchases, revenue, roas, cpa:        float | None,
#   nnr, nnr_share, p_1d_click, p_28d_click, nc, nc_revenue: float | None,
#   first_active:    ISO date str | None,
#   age_days:        int | None  (how long the ad has been live, not
#                    used in 7-day scoring but kept for context),
#   status_tag:      "SCALE" | "HOLD" | "REFRESH" | "KILL",
#   reason:          str (plain-language explanation),
#   tags:            list[str] (secondary chips),
#   product:         str (inferred product label),
#   sym:             str (currency symbol for display),
# }
