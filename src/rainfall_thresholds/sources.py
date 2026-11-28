"""The shape of a rain source, so that any archive can feed this package.

This package reads no rain: it takes hourly series. :class:`RainSource` is
the shape of what gives them for a list of points, written down so that code
joining a rain library with this one can be typed without either importing
the other. dpc-radar's ``MergingArchive`` and ``SriHistory`` have this shape;
so can a table of rain gauges.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class RainSource(Protocol):
    """Hourly rain at lon/lat points."""

    def hourly(
        self, points: list[tuple[float, float]], start: datetime, end: datetime
    ) -> dict[datetime, list[float | None]]:
        """The rain of every hour in ``(start, end]``, in mm, one value per point.

        The key is the end of the hour; the list follows ``points``. ``None``
        is an hour not measured at that point, never zero.
        """
        ...


def point_series(
    rain: Mapping[datetime, Sequence[float | None]], index: int
) -> dict[datetime, float | None]:
    """The series of one point, out of what :meth:`RainSource.hourly` returns.

    Ready for :func:`~rainfall_thresholds.assess.event_against_threshold`,
    :func:`~rainfall_thresholds.assess.cumulate` and, as ``.items()``,
    :func:`~rainfall_thresholds.events.reconstruct_events`.
    """
    return {when: values[index] for when, values in rain.items()}
