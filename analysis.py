"""Statistik, aggregering og sammenhængsanalyse af logdata."""

from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from typing import TypedDict

from aggregation import grouped_counts
from model import LogRecord

TOP_N = 10


class UserFailure(TypedDict):
    user: str
    failures: int
    total: int
    rate: float


class HourlySummary(TypedDict):
    average: float
    busiest_hour: int | None
    busiest_count: int
    quietest_hour: int | None
    quietest_count: int


class PortEvent(TypedDict):
    port: int
    event_category: str
    ip_scope: str
    count: int


class PortFailure(TypedDict):
    port: int
    total: int
    failures: int
    failure_rate: float
    external: int
    external_failure_rate: float


class PairSeries(TypedDict):
    time_of_day: list[tuple[int, int]]
    user_failure: list[UserFailure]
    port_event: list[PortEvent]


def top_n_lists(
    records: Iterable[LogRecord], n: int = TOP_N
) -> dict[str, list[tuple[str, int]]]:
    rows = grouped_counts.highestTabel(records=list(records))
    return {
        "users": _rank_rows(rows, "User", n),
        "src_ips": _rank_rows(rows, "src_ip", n),
        "dest_hosts": _rank_rows(rows, "dest_host", n),
    }


def _rank_rows(rows, key, n):
    entries = [(row[key], row["Events"]) for row in rows if key in row]
    return sorted(entries, key=lambda item: (-item[1], item[0]))[:n]


def is_failure(record: LogRecord) -> bool:
    return record.event_category == "fejl" or record.status_category == "fejl"


def time_range(
    records: Iterable[LogRecord],
) -> tuple[datetime | None, datetime | None]:
    timestamps = [record.timestamp for record in records]
    if not timestamps:
        return None, None
    return min(timestamps), max(timestamps)


def failure_counts(records: Iterable[LogRecord]) -> tuple[int, int]:
    records = list(records)
    failures = sum(1 for record in records if is_failure(record))
    return failures, len(records)


def hourly_event_counts(records: Iterable[LogRecord]) -> list[tuple[int, int]]:
    counts = Counter(record.hour for record in records)
    return [(hour, counts[hour]) for hour in range(24)]


def user_failure_rates(records: Iterable[LogRecord]) -> list[UserFailure]:
    totals = Counter()
    failures = Counter()
    for record in records:
        totals[record.user] += 1
        if is_failure(record):
            failures[record.user] += 1

    rates: list[UserFailure] = [
        {
            "user": user,
            "failures": failures[user],
            "total": total,
            "rate": failures[user] / total,
        }
        for user, total in totals.items()
    ]
    return sorted(rates, key=lambda entry: (-entry["rate"], entry["user"]))


def port_event_series(records: Iterable[LogRecord]) -> list[PortEvent]:
    counts = Counter(
        (record.dest_port, record.event_category, record.ip_scope)
        for record in records
    )
    series: list[PortEvent] = [
        {
            "port": port,
            "event_category": category,
            "ip_scope": scope,
            "count": count,
        }
        for (port, category, scope), count in counts.items()
    ]
    return sorted(
        series,
        key=lambda entry: (
            entry["port"],
            entry["event_category"],
            entry["ip_scope"],
        ),
    )


def hourly_summary(records: Iterable[LogRecord]) -> HourlySummary:
    hourly = hourly_event_counts(records)
    if not any(count for _, count in hourly):
        return {
            "average": 0.0,
            "busiest_hour": None,
            "busiest_count": 0,
            "quietest_hour": None,
            "quietest_count": 0,
        }

    busiest_hour, busiest_count = max(hourly, key=lambda item: item[1])
    quietest_hour, quietest_count = min(hourly, key=lambda item: item[1])
    total = sum(count for _, count in hourly)
    return {
        "average": total / len(hourly),
        "busiest_hour": busiest_hour,
        "busiest_count": busiest_count,
        "quietest_hour": quietest_hour,
        "quietest_count": quietest_count,
    }


def port_failure_rows(records: Iterable[LogRecord]) -> list[PortFailure]:
    totals = Counter()
    external = Counter()
    failures = Counter()
    external_failures = Counter()
    for record in records:
        port = record.dest_port
        totals[port] += 1
        failures[port] += is_failure(record)
        if record.ip_scope == "ekstern":
            external[port] += 1
            external_failures[port] += is_failure(record)

    return [
        {
            "port": port,
            "total": totals[port],
            "failures": failures[port],
            "failure_rate": failures[port] / totals[port],
            "external": external[port],
            "external_failure_rate": (
                external_failures[port] / external[port]
                if external[port]
                else 0.0
            ),
        }
        for port in sorted(totals)
    ]
