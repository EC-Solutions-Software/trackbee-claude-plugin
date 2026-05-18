"""Regression tests for the channel touch-points heatmap and cooccurrence
insights.

Both modules read the ``cooccurrence`` bucket of
``tool__get_platform_interactions``. The MCP payload uses ``a``/``b``
keys for the (symmetric) cooccurrence rows and ``leading``/``related``
keys for the (directional) transitions rows. A previous bug read
``leading``/``related`` on cooccurrence rows, which silently produced
0.0 for every off-diagonal cell in the heatmap and degraded the
cooccurrence insights.

These tests assert the heatmap HTML renders the real percentages and
that the insights function produces at least one observation for a
non-empty cooccurrence payload.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parent.parent
HEATMAP_PATH = (
    SKILL_ROOT / "resources" / "dashboards" / "attribution"
    / "transforms" / "journey_heatmap.py"
)
COOCCUR_PATH = (
    SKILL_ROOT / "resources" / "dashboards" / "attribution"
    / "insights" / "cooccurrence.py"
)


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def heatmap_mod():
    return _load("journey_heatmap", HEATMAP_PATH)


@pytest.fixture()
def cooccur_mod():
    return _load("cooccurrence_insights", COOCCUR_PATH)


@pytest.fixture()
def touchpoints():
    return {
        "cooccurrence": [
            {"a": "google", "b": "meta", "share_of_orders": 0.1068},
            {"a": "meta", "b": "klaviyo", "share_of_orders": 0.0752},
        ],
        "transitions": [
            {
                "leading": "meta",
                "related": "google",
                "share_of_leading": 0.16,
                "share_of_orders": 0.08,
            },
        ],
        "single_touch_share": 0.24,
        "multi_touch_share": 0.42,
        "organic_share": 0.33,
    }


def test_heatmap_renders_cooccurrence_shares(heatmap_mod, touchpoints):
    """Real MCP cooccurrence rows use a/b — heatmap must read them."""
    out = heatmap_mod.transform(inputs={"touchpoints": touchpoints}, config={})

    html = out["html"]
    # The two pairs in the fixture, rounded to one decimal as the cell
    # formatter renders them.
    assert "10.7%" in html, "Google×Meta cell missing — heatmap likely all-zeros"
    assert "7.5%" in html, "Meta×Klaviyo cell missing — heatmap likely all-zeros"

    # Sanity: every channel from cooccurrence is on the axes.
    assert "google" in out["platforms"]
    assert "meta" in out["platforms"]
    assert "klaviyo" in out["platforms"]


def test_heatmap_off_diagonal_not_all_zero(heatmap_mod, touchpoints):
    """Guard against the original regression: every off-diagonal == 0.0%."""
    out = heatmap_mod.transform(inputs={"touchpoints": touchpoints}, config={})

    html = out["html"]
    # 3 platforms → 6 off-diagonal cells. The original bug rendered "0.0%"
    # in every one of them. Confirm we get at least one non-zero share.
    non_zero_renders = [s for s in ("10.7%", "7.5%") if s in html]
    assert non_zero_renders, "All off-diagonal cells are 0.0% — cooccurrence not read"


def test_heatmap_falls_back_to_leading_related(heatmap_mod):
    """Defensive: if a payload variant ever puts directional keys on
    cooccurrence rows, the fallback path should still pick them up."""
    tp = {
        "cooccurrence": [
            {"leading": "meta", "related": "google", "share_of_orders": 0.12},
        ],
        "transitions": [],
    }
    out = heatmap_mod.transform(inputs={"touchpoints": tp}, config={})
    assert "12.0%" in out["html"]


def test_heatmap_diagonal_uses_self_loop_transitions(heatmap_mod):
    """Diagonal cells must read from ``<X> -> <X>`` rows in transitions[],
    not hardcode to 0.0. Regression: diagonal was always 0.0%."""
    tp = {
        "cooccurrence": [
            {"a": "google", "b": "meta", "share_of_orders": 0.1068},
        ],
        "transitions": [
            {"leading": "meta",   "related": "meta",
             "share_of_leading": 0.59, "share_of_orders": 0.30},
            {"leading": "google", "related": "google",
             "share_of_leading": 0.33, "share_of_orders": 0.07},
            {"leading": "meta",   "related": "order",
             "share_of_leading": 0.76, "share_of_orders": 0.38},
        ],
        "single_touch_share": 0.24,
        "multi_touch_share":  0.42,
        "organic_share":      0.33,
    }

    out = heatmap_mod.transform(inputs={"touchpoints": tp}, config={})
    html = out["html"]

    # The Meta diagonal (30.0%) and Google diagonal (7.0%) must render.
    assert "30.0%" in html, "Meta self-loop missing from diagonal"
    assert "7.0%" in html, "Google self-loop missing from diagonal"

    # Catch the original "diagonal always zero" regression directly. Every
    # channel in the fixture has a self-loop row, and the matrix is
    # 2x2 (Meta + Google), so no `diag` cell should render 0.0%.
    assert "'hcell diag'>0.0%</td>" not in html, (
        "Diagonal cell still rendering 0.0% despite self-loop data"
    )


def test_cooccurrence_insights_produces_observations(cooccur_mod, touchpoints):
    """Insights function must surface at least one a/b-keyed pair."""
    out = cooccur_mod.insights(touchpoints, orders_per_platform=None)

    assert isinstance(out, list) and out, "Insights list is empty"
    joined = " ".join(item.get("obs", "") for item in out)
    # The strongest pair in the fixture is Google × Meta at 10.7%.
    assert "Google" in joined and "Meta" in joined, (
        f"Expected the top cooccurrence pair (Google × Meta) to appear "
        f"in observations, got: {joined!r}"
    )
    assert "10.7%" in joined
