# timeutils.py
#
# Centralizes how the scheduling subsystem converts between wall-clock time and the
# naive-UTC datetimes stored in scheduled_at/executed_at. SQLite has no native
# timezone-aware datetime type, so everything there is stored as naive UTC.
#
# A timestamp that arrives WITHOUT a timezone (e.g. a raw local time typed by a lab
# user) is assumed to already be in LOCAL_TZ (the lab is in Stuttgart, Germany), not
# UTC — treating a naive value as "already UTC" would silently be off by 1-2 hours.

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Berlin")


class NonExistentLocalTimeError(ValueError):
    """A naive datetime falls in a DST spring-forward gap and never occurred in LOCAL_TZ."""


class AmbiguousLocalTimeError(ValueError):
    """A naive datetime falls in a DST fall-back overlap and occurred twice in LOCAL_TZ."""


def _is_nonexistent(dt_local: datetime) -> bool:
    # Attach the zone, round-trip through UTC and back; a gap time gets pulled onto
    # a real instant on the way through, so the wall-clock reading won't match.
    aware = dt_local.replace(tzinfo=LOCAL_TZ)
    round_tripped = aware.astimezone(timezone.utc).astimezone(LOCAL_TZ).replace(tzinfo=None)
    return round_tripped != dt_local


def _is_ambiguous(dt_local: datetime) -> bool:
    # The two PEP 495 "fold" interpretations resolve to different UTC offsets only
    # when the wall-clock reading occurs twice (fall-back overlap).
    offset_first = dt_local.replace(tzinfo=LOCAL_TZ, fold=0).utcoffset()
    offset_second = dt_local.replace(tzinfo=LOCAL_TZ, fold=1).utcoffset()
    return offset_first != offset_second


def validate_naive_local(dt: datetime) -> None:
    """Raise if a naive datetime is not a real, unambiguous Europe/Berlin local time.
    (A gap time also looks "ambiguous" under the fold check, so non-existence is
    checked first and takes precedence.) No-op for an already timezone-aware dt."""
    if dt.tzinfo is not None:
        return
    if _is_nonexistent(dt):
        raise NonExistentLocalTimeError(
            f"{dt.isoformat()} does not exist in Europe/Berlin local time — clocks skip "
            "from 02:00 to 03:00 during the spring DST transition. Pick a time outside "
            "that gap, or send the time with an explicit UTC offset."
        )
    if _is_ambiguous(dt):
        raise AmbiguousLocalTimeError(
            f"{dt.isoformat()} is ambiguous in Europe/Berlin local time — it occurs twice "
            "during the autumn DST transition (clocks fall back from 03:00 to 02:00). "
            "Send the time with an explicit UTC offset to disambiguate."
        )


def to_utc_naive(dt: datetime) -> datetime:
    """Convert a datetime to naive UTC for storage. A naive input is assumed to
    already be in LOCAL_TZ (Europe/Berlin) rather than UTC."""
    if dt.tzinfo is None:
        validate_naive_local(dt)
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def utc_now_naive() -> datetime:
    """The current time as naive UTC, matching how scheduled_at/executed_at are stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
