from __future__ import annotations

import datetime as _dt
import os
from typing import Optional

__all__ = ["FileTimestampFormatter", "format_stat_time"]


def _validate_offset_minutes(offset_minutes: int) -> None:
    """Guard against offsets that cannot represent a real timezone.

    The library accepts offsets as integer minutes rather than full
    tzinfo objects to keep the surface area small and dependency-free.
    We clamp the range to +/- 24h because POSIX allows offsets up to
    24:00:00 (inclusive) for historical zones, and anything beyond
    that is a programming error rather than a timestamp to format.
    """
    if not isinstance(offset_minutes, int):
        raise TypeError(
            "offset_minutes must be int, got " + type(offset_minutes).__name__
        )
    if offset_minutes < -24 * 60 or offset_minutes > 24 * 60:
        raise ValueError(
            "offset_minutes must be in [-1440, 1440], got " + str(offset_minutes)
        )


class _ClampedTimezone(_dt.tzinfo):
    """Timezone whose offset may be exactly ±24h.

    ``datetime.timezone`` rejects offsets that are exactly ±24h because
    they are on the boundary of what POSIX permits. We accept them per
    the documented contract, so this thin subclass returns the stored
    offset directly without that boundary check.
    """

    def __init__(self, offset: _dt.timedelta) -> None:
        self._offset = offset

    def utcoffset(self, dt):
        return self._offset

    def tzname(self, dt):
        return None

    def dst(self, dt):
        return _dt.timedelta(0)


class FileTimestampFormatter:
    """Format file stat timestamps as ISO 8601 strings with a fixed offset.

    The offset is fixed rather than derived from the host clock so that
    formatting is purely a function of its inputs. A test running in a
    container in UTC can produce +09:00 timestamps without touching the
    system timezone, and a batch job can record which offset it *believed*
    applied at the time even if the host tzdata disagrees.

    The ``format`` method takes an explicit float epoch seconds value
    rather than reading ``time.time()`` internally, so tests never need
    to monkey-patch the clock or sleep.
    """

    def __init__(self, offset_minutes: int = 0) -> None:
        _validate_offset_minutes(offset_minutes)
        # Store as a custom tzinfo subclass so offsets of exactly ±1440
        # minutes are accepted. ``datetime.timezone`` rejects those
        # boundary values, but our contract permits them per POSIX.
        self._tz = _ClampedTimezone(_dt.timedelta(minutes=offset_minutes))
        self._offset_minutes = offset_minutes

    @property
    def offset_minutes(self) -> int:
        return self._offset_minutes

    def format(self, epoch_seconds: float, *, timespec: str = "seconds") -> str:
        """Format an epoch-seconds value as an ISO 8601 string.

        ``timespec`` is forwarded to ``datetime.isoformat`` so callers can
        request microsecond precision when the underlying stat value
        actually carries it. We do not try to *guess* precision from the
        float because ``os.stat_result.st_mtime`` on Linux truncates
        nanoseconds to whatever the filesystem reported, which is not
        recoverable from the float alone.
        """
        dt = _dt.datetime.fromtimestamp(epoch_seconds, tz=self._tz)
        return dt.isoformat(timespec=timespec)

    def format_stat(self, st: os.stat_result, *, timespec: str = "seconds") -> dict:
        """Return a dict of the three portable stat timestamps, formatted.

        We use ``getattr`` rather than indexing because ``os.stat_result``
        is a sequence *and* a mapping, and the attribute path avoids any
        ambiguity on platforms where the index order differs.
        """
        return {
            "atime": self.format(getattr(st, "st_atime"), timespec=timespec),
            "mtime": self.format(getattr(st, "st_mtime"), timespec=timespec),
            "ctime": self.format(getattr(st, "st_ctime"), timespec=timespec),
        }


def format_stat_time(
    epoch_seconds: float,
    offset_minutes: int = 0,
    *,
    timespec: str = "seconds",
) -> str:
    """Stateless convenience wrapper around :class:`FileTimestampFormatter`.

    Useful for one-off formatting where constructing an instance would be
    ceremony. Repeated formatting should reuse an instance to avoid
    re-validating the offset each call.
    """
    return FileTimestampFormatter(offset_minutes).format(
        epoch_seconds, timespec=timespec
    )
