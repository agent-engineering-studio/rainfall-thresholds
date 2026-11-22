from __future__ import annotations

import math

import pytest

from rainfall_thresholds import auc, cutoff_at_budget, skill, skill_at_budget


def test_skill_counts_both_sides_at_the_cutoff() -> None:
    s = skill([0.5, 0.2, -0.1, 0.0], [-1.0, -0.5, 0.0, 0.3, -0.2], cutoff=0.0)
    assert (s.caught, s.landslides, s.alerts, s.ordinary) == (3, 4, 2, 5)
    assert s.hit_rate == 0.75
    assert s.alert_share == 0.4
    assert s.discrimination == pytest.approx(1.875)
    assert s.alerts_per_caught == pytest.approx(2 / 3)


def test_not_measured_is_left_out_and_counted() -> None:
    s = skill([0.5, None, math.nan], [None, -1.0], cutoff=0.0)
    assert (s.caught, s.landslides, s.ordinary, s.unmeasured) == (1, 1, 1, 3)


def test_unknown_ratios_are_none_not_zero() -> None:
    empty = skill([], [], cutoff=0.0)
    assert empty.hit_rate is None and empty.alert_share is None
    assert empty.discrimination is None and empty.alerts_per_caught is None
    nothing_on_alert = skill([1.0], [-1.0], cutoff=0.0)
    assert nothing_on_alert.alert_share == 0.0
    assert nothing_on_alert.discrimination is None


def test_cutoff_at_budget_is_the_kth_highest() -> None:
    ordinary = [float(x) for x in range(1, 101)]  # 1..100
    assert cutoff_at_budget(ordinary, 0.05) == 96.0
    assert cutoff_at_budget(ordinary, 0.001) == 100.0  # at least one unit
    assert cutoff_at_budget(ordinary, 1.0) == 1.0


def test_ties_can_put_more_than_the_budget_on_alert() -> None:
    s = skill_at_budget([], [5.0, 5.0, 5.0, 1.0], budget=0.25)
    assert s.cutoff == 5.0
    assert s.alert_share == 0.75


def test_a_floor_never_alerts() -> None:
    mostly_zero = [0.0] * 98 + [0.4, 0.9]
    assert cutoff_at_budget(mostly_zero, 0.05) == 0.0
    assert cutoff_at_budget(mostly_zero, 0.05, floor=0.0) == 0.4
    assert cutoff_at_budget([0.0, 0.0], 0.5, floor=0.0) == math.inf


def test_cutoff_without_scores_is_infinite_and_budget_is_checked() -> None:
    assert cutoff_at_budget([None], 0.1) == math.inf
    with pytest.raises(ValueError, match="budget"):
        cutoff_at_budget([1.0], 0.0)
    with pytest.raises(ValueError, match="budget"):
        cutoff_at_budget([1.0], 1.5)


def test_same_budget_compares_two_scores_fairly() -> None:
    # Score B alerts on everything above 0, A only on the top: at a fixed
    # cutoff B "catches more"; at the same budget they catch the same.
    ordinary = [i / 100 for i in range(100)]
    landslides = [0.97, 0.99, 0.5]
    a = skill_at_budget(landslides, ordinary, budget=0.05)
    assert a.caught == 2 and a.alert_share == 0.05
    b = skill(landslides, ordinary, cutoff=0.01)
    assert b.caught == 3 and b.alert_share == 0.99


def test_auc_ties_count_half() -> None:
    assert auc([1.0, 2.0], [0.0, 0.5]) == 1.0
    assert auc([0.0], [1.0]) == 0.0
    assert auc([1.0], [1.0]) == 0.5
    assert auc([0.0, 0.0, 1.0], [0.0, 0.0]) == pytest.approx((0.5 * 4 + 2) / 6)
    assert auc([], [1.0]) is None
    assert auc([1.0], [None]) is None
