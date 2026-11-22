"""How good a threshold is: landslides caught, and the alerts it costs.

A threshold is only half an answer. T5 catches 95 % of past landslides by
construction; what it does not say is how often it is exceeded when nothing
happens. These functions measure both sides on the same scale, for any
score that grows with danger: the exceedance of a threshold in decades, a
24-hour total in mm, a probability.

You bring two lists of scores:

* ``landslides``: one score per landslide, the **highest** in the hours
  before it (the lead window is your choice: 24, 48, 72 hours);
* ``ordinary``: one score per unit of time and place you could alert on
  (cell-hours, municipality-days...), with or without landslides, as your
  alert budget is counted.

``None`` is a score that was not measured. It is left out and counted,
never read as zero.

Definitions, as in Limen's backtests (limen#243, limen#352):

* a landslide is **caught** when its score reaches the cutoff (``>=``);
* the **alert share** is the share of ordinary units at or above the cutoff;
* **discrimination** is hit rate over alert share: 1 is chance;
* the **cutoff at a budget** is the score that puts that share of ordinary
  units on alert. Ties can make the share a little higher than asked.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Skill:
    """What a cutoff catches, and what it costs."""

    cutoff: float
    caught: int
    landslides: int
    alerts: int
    ordinary: int
    #: Scores left out because they were not measured (``None`` or NaN).
    unmeasured: int = 0

    @property
    def hit_rate(self) -> float | None:
        """Share of the landslides caught; ``None`` without landslides."""
        return self.caught / self.landslides if self.landslides else None

    @property
    def alert_share(self) -> float | None:
        """Share of the ordinary units on alert; ``None`` without units."""
        return self.alerts / self.ordinary if self.ordinary else None

    @property
    def discrimination(self) -> float | None:
        """Hit rate over alert share: 1 is chance. ``None`` when either is unknown or zero."""
        hit, share = self.hit_rate, self.alert_share
        if hit is None or not share:
            return None
        return hit / share

    @property
    def alerts_per_caught(self) -> float | None:
        """Alerts paid for every landslide caught; ``None`` when none is caught."""
        return self.alerts / self.caught if self.caught else None


def _measured(scores: Iterable[float | None]) -> tuple[list[float], int]:
    kept: list[float] = []
    dropped = 0
    for s in scores:
        if s is None or math.isnan(s):
            dropped += 1
        else:
            kept.append(float(s))
    return kept, dropped


def skill(
    landslides: Iterable[float | None],
    ordinary: Iterable[float | None],
    cutoff: float,
) -> Skill:
    """Landslides caught and ordinary units on alert at ``cutoff``."""
    pos, pos_missing = _measured(landslides)
    neg, neg_missing = _measured(ordinary)
    return Skill(
        cutoff=cutoff,
        caught=sum(s >= cutoff for s in pos),
        landslides=len(pos),
        alerts=sum(s >= cutoff for s in neg),
        ordinary=len(neg),
        unmeasured=pos_missing + neg_missing,
    )


def cutoff_at_budget(
    ordinary: Iterable[float | None], budget: float, *, floor: float | None = None
) -> float:
    """The cutoff that puts ``budget`` (0-1) of the ordinary units on alert.

    It is the k-th highest score, ``k = max(1, round(budget * n))``. With
    ``floor``, a score at or below it never alerts (for a score that is 0 when
    nothing happens, ``floor=0``): the cutoff is then at least the lowest score
    above it, or ``inf`` when there is none. Without measured scores, ``inf``.
    """
    if not 0.0 < budget <= 1.0:
        raise ValueError(f"budget must be in (0, 1], got {budget}")
    values, _ = _measured(ordinary)
    if not values:
        return math.inf
    ranked = sorted(values, reverse=True)
    k = max(1, round(budget * len(ranked)))
    cutoff = ranked[k - 1]
    if floor is not None and cutoff <= floor:
        cutoff = min((x for x in ranked if x > floor), default=math.inf)
    return cutoff


def skill_at_budget(
    landslides: Iterable[float | None],
    ordinary: Iterable[float | None],
    budget: float,
    *,
    floor: float | None = None,
) -> Skill:
    """:func:`skill` at the cutoff of :func:`cutoff_at_budget`.

    The fair way to compare two scores: at the same share of units on alert,
    which catches more landslides? Counting at a fixed level instead rewards
    the score that alerts more.
    """
    neg = list(ordinary)
    return skill(landslides, neg, cutoff_at_budget(neg, budget, floor=floor))


def auc(landslides: Iterable[float | None], ordinary: Iterable[float | None]) -> float | None:
    """The chance that a landslide scores higher than an ordinary unit (Mann-Whitney).

    Ties count half. ``None`` without one of the two lists. Read it with
    care when many scores are tied, for example at zero: it then measures the
    order of the few that are not, and says nothing about the level.
    """
    pos, _ = _measured(landslides)
    neg, _ = _measured(ordinary)
    if not pos or not neg:
        return None
    values = sorted([(s, True) for s in pos] + [(s, False) for s in neg], key=lambda v: v[0])
    rank_sum = 0.0
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[j + 1][0] == values[i][0]:
            j += 1
        mean_rank = (i + j) / 2.0 + 1.0
        rank_sum += mean_rank * sum(is_pos for _, is_pos in values[i : j + 1])
        i = j + 1
    n_pos, n_neg = len(pos), len(neg)
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
