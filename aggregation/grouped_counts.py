"""Gruppering og optælling af hændelser pr. bruger, IP, vært og port."""

from collections import Counter, defaultdict
from collections.abc import Callable


def highestTabel(AllData=None, records=()):
    counts_by_user = defaultdict(Counter)
    counts_by_ip = defaultdict(Counter)
    counts_by_host = defaultdict(Counter)
    counts_by_port = defaultdict(Counter)
    service_by_port = {}

    for record in records:
        service_by_port.setdefault(record.dest_port, record.service)
        counters = (
            counts_by_user[record.user],
            counts_by_ip[record.src_ip],
            counts_by_host[record.dest_host],
            counts_by_port[record.dest_port],
        )
        for counts in counters:
            counts["Events"] += 1
            counts["Level"] += 1
            counts["Status"] += 1
            counts[record.event] += 1
            counts[record.level] += 1
            counts[record.status] += 1

    compiled_data = _group_rows(counts_by_user, "User")
    compiled_data.extend(_group_rows(counts_by_ip, "src_ip"))
    compiled_data.extend(_group_rows(counts_by_host, "dest_host"))
    compiled_data.extend(
        _group_rows(
            counts_by_port,
            "dest",
            lambda port: f"{port} ({service_by_port[port]})",
        )
    )
    return compiled_data


def _group_rows(
    counts_by_value,
    key: str,
    format_value: Callable[[object], str] = str,
):
    return [
        {key: format_value(value), **counts_by_value[value]}
        for value in sorted(counts_by_value)
    ]
