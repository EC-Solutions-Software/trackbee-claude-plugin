"""Per-store JSON discovery + envelope unpacking.

Reads `<store_id>_overview.json`, `<store_id>_meta.json`, `<store_id>_google.json`
plus the per-campaign ad files from the inputs directory and returns one
flat dict per store with everything the orchestrator needs.

Currency conversion: spend / revenue values arrive in the ad-account's
native currency. The orchestrator's downstream transforms multiply by
`m_fx` / `g_fx` to express every monetary value in the store's currency.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "format_helpers",
    _HERE.parent / "chrome" / "format_helpers.py",
)
assert _spec is not None and _spec.loader is not None
_fh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fh)

_spec_cfg = importlib.util.spec_from_file_location("ap_config", _HERE / "config.py")
assert _spec_cfg is not None and _spec_cfg.loader is not None
_cfg = importlib.util.module_from_spec(_spec_cfg)
_spec_cfg.loader.exec_module(_cfg)


def _load_ad_files(inputs_dir: Path, sid: int | str, platform: str) -> dict:
    """Return a dict keyed by campaign_id → list of ad / asset-group dicts."""
    prefix = f"{sid}_{platform}_ads_"
    out: dict = {}
    for f in sorted(inputs_dir.glob(f"{prefix}*.json")):
        cid = f.stem.split(prefix, 1)[1]
        try:
            data = json.loads(f.read_text(encoding="utf-8")).get("result") or {}
        except (json.JSONDecodeError, OSError):
            data = {}
        # PMAX returns asset_groups; Search / Shopping return ads.
        out[cid] = data.get("ads") or data.get("asset_groups") or []
    return out


def load_all_stores(inputs_dir: Path, stores_cfg: list[dict]) -> list[dict]:
    """Load every store's data into one list of dicts."""
    out: list[dict] = []
    for sc in stores_cfg:
        sid = sc["id"]
        sym = sc["currency_symbol"]
        g_fx = _fh.safe_float(sc.get("google_fx_to_store", 1.0), 1.0)
        m_fx = _fh.safe_float(sc.get("meta_fx_to_store", 1.0), 1.0)

        overview = _cfg.load_json(inputs_dir, f"{sid}_overview.json")
        meta_raw = _cfg.load_json(inputs_dir, f"{sid}_meta.json")
        goog_raw = _cfg.load_json(inputs_dir, f"{sid}_google.json")

        meta_campaigns = meta_raw.get("campaigns", []) or []
        goog_campaigns = goog_raw.get("campaigns", []) or []

        meta_ads = _load_ad_files(inputs_dir, sid, "meta")
        goog_ads = _load_ad_files(inputs_dir, sid, "google")

        # Overview KPIs arrive in cents of the store currency. We only
        # use `total_revenue` and `marketing_efficiency_ratio` downstream
        # (in store_kpis.compute) — keep the dict tight so reviewers can
        # tell at a glance which fields actually feed the dashboard.
        ov = overview.get("overview") if isinstance(overview, dict) else {}
        ov = ov or {}
        ov_total_rev = _fh.safe_float(ov.get("total_revenue", 0)) / 100
        ov_mer = _fh.safe_float(ov.get("marketing_efficiency_ratio", 0))

        out.append({
            "id":             sid,
            "name":           sc["name"],
            "currency":       sc["currency"],
            "symbol":         sym,
            "g_fx":           g_fx,
            "m_fx":           m_fx,
            "meta_campaigns": meta_campaigns,
            "goog_campaigns": goog_campaigns,
            "meta_ads":       meta_ads,
            "goog_ads":       goog_ads,
            "ov_total_rev":   ov_total_rev,
            "ov_mer":         ov_mer,
        })

    return out
