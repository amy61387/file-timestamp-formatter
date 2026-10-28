# file-timestamp-formatter

Converts `os.stat_result` timestamps into ISO 8601 strings with a fixed UTC offset. Standard library only, no dependencies.

```python
import tempfile, os
from file_timestamp_formatter import FileTimestampFormatter, format_stat_time

f = FileTimestampFormatter(offset_minutes=540)  # +09:00
f.format(0.0)                                   # '1970-01-01T09:00:00+09:00'

with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "some_file.txt")
    open(path, "w").close()
    f.format_stat(os.stat(path))  # {'atime': '...', 'mtime': '...', 'ctime': '...'}

# one-off, stateless
format_stat_time(0.0, offset_minutes=-480)      # '1969-12-31T16:00:00-08:00'
```

## Why this exists

Recording when a file was touched is only useful if the recorded string says *which* offset it was recorded in. A bare `"2024-01-01T12:00:00"` is ambiguous; `"2024-01-01T12:00:00+09:00"` is not. This library exists to produce that unambiguous string from the float epoch seconds that `os.stat` returns, without dragging in a timezone database.

The trade-off: the offset is fixed and caller-supplied. We do not try to resolve the zone the host *would* have applied at that instant — that requires tzdata and historical rules, and is a different library. If you need that, pair this with `zoneinfo` and pass the resolved offset in.

## Edge cases

- **Fractional seconds are truncated** when `timespec="seconds"` (the default). Pass `timespec="microseconds"` to keep sub-second precision; do not try to recover it after the fact.
- **Pre-epoch timestamps** (before 1970-01-01T00:00:00Z) are supported and produce correctly negative dates.
- **Offset range** is clamped to ±1440 minutes (±24h). POSIX permits up to 24:00 inclusive; anything beyond that is treated as a programming error.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

