"""Scatter-plots til sammenhængsanalysen af logdata."""

import plotly.graph_objects as go

import analysis
from model import service_name

SCOPE_COLORS = {
    "intern": "#2e7d32",
    "ekstern": "#c62828",
    "invalid": "#616161",
}
CATEGORY_LABELS = {"succes": "Succes", "neutral": "Neutral", "fejl": "Fejl"}
CATEGORY_ORDER = ("succes", "neutral", "fejl")
NO_DATA_MESSAGE = "Ingen data at vise"

BASE_LAYOUT = {
    "template": "plotly_white",
    "font": {"family": "sans-serif", "size": 13},
    "margin": {"l": 70, "r": 30, "t": 60, "b": 90},
    "height": 500,
}


def _layout(figure, title, x_axis, y_axis, **overrides):
    figure.update_layout(
        title=title,
        xaxis=x_axis,
        yaxis=y_axis,
        **BASE_LAYOUT,
        **overrides,
    )
    return figure


def _empty_figure(title, x_title, y_title):
    figure = go.Figure()
    figure.add_annotation(
        text=NO_DATA_MESSAGE, showarrow=False, font={"size": 16}
    )
    return _layout(figure, title, {"title": x_title}, {"title": y_title})


def hour_event_scatter(records):
    title = "Hændelser pr. time på dagen"
    if not records:
        return _empty_figure(title, "Time på dagen", "Antal hændelser")

    series = analysis.hourly_event_counts(records)
    figure = go.Figure(
        go.Scatter(
            x=[hour for hour, _ in series],
            y=[count for _, count in series],
            mode="markers",
            marker={"size": 10, "color": "#1565c0"},
            hovertemplate="Kl. %{x}: %{y} hændelser<extra></extra>",
            name="Hændelser",
        )
    )
    return _layout(
        figure,
        title,
        {
            "title": "Time på dagen",
            "tick0": 0,
            "dtick": 1,
            "range": [-0.5, 23.5],
        },
        {"title": "Antal hændelser", "rangemode": "tozero"},
        showlegend=False,
    )


def user_failure_scatter(records):
    title = "Andel fejl pr. bruger"
    if not records:
        return _empty_figure(title, "Bruger", "Andel fejl (%)")

    series = analysis.user_failure_rates(records)
    total_failures = sum(entry["failures"] for entry in series)
    total_events = sum(entry["total"] for entry in series)
    overall_rate = total_failures / total_events * 100 if total_events else 0

    figure = go.Figure(
        go.Scatter(
            x=[entry["user"] for entry in series],
            y=[entry["rate"] * 100 for entry in series],
            mode="markers",
            marker={"size": 12, "color": "#6a1b9a"},
            customdata=[
                [entry["failures"], entry["total"]] for entry in series
            ],
            hovertemplate=(
                "%{x}: %{y:.1f} % fejl "
                "(%{customdata[0]} af %{customdata[1]} hændelser)"
                "<extra></extra>"
            ),
            name="Brugere",
        )
    )
    figure.add_hline(
        y=overall_rate,
        line={"dash": "dash", "color": "#616161"},
        annotation_text=f"Samlet fejlrate: {overall_rate:.1f} %",
        annotation_position="top left",
    )
    return _layout(
        figure,
        title,
        {"title": "Bruger", "type": "category"},
        {"title": "Andel fejl (%)", "rangemode": "tozero"},
        showlegend=False,
    )


def port_event_scatter(records):
    title = "Destinationsport vs. hændelsestype og IP-klasse"
    if not records:
        return _empty_figure(title, "Destinationsport", "Hændelsestype")

    series = analysis.port_event_series(records)
    ports = sorted({entry["port"] for entry in series})
    labels = [f"{port} ({service_name(port)})" for port in ports]
    label_by_port = dict(zip(ports, labels))
    max_count = max(entry["count"] for entry in series)

    figure = go.Figure()
    for scope in sorted({entry["ip_scope"] for entry in series}):
        entries = [entry for entry in series if entry["ip_scope"] == scope]
        figure.add_trace(
            go.Scatter(
                x=[label_by_port[entry["port"]] for entry in entries],
                y=[
                    CATEGORY_LABELS[entry["event_category"]]
                    for entry in entries
                ],
                mode="markers",
                marker={
                    "size": [entry["count"] for entry in entries],
                    "sizemode": "area",
                    "sizeref": 2 * max_count / 40**2,
                    "sizemin": 4,
                    "color": SCOPE_COLORS.get(scope, "#616161"),
                    "opacity": 0.75,
                },
                customdata=[
                    [entry["count"], entry["ip_scope"]] for entry in entries
                ],
                hovertemplate=(
                    "%{x} – %{y}<br>%{customdata[0]} hændelser "
                    "(%{customdata[1]} IP)<extra></extra>"
                ),
                name=scope,
            )
        )

    return _layout(
        figure,
        title,
        {
            "title": "Destinationsport",
            "type": "category",
            "categoryorder": "array",
            "categoryarray": labels,
        },
        {
            "title": "Hændelsestype",
            "type": "category",
            "categoryorder": "array",
            "categoryarray": [
                CATEGORY_LABELS[category] for category in CATEGORY_ORDER
            ],
        },
        legend={"title": {"text": "IP-klasse"}},
    )


def build_figures(records) -> dict[str, go.Figure]:
    records = list(records)
    return {
        "events_by_hour": hour_event_scatter(records),
        "user_failure_rate": user_failure_scatter(records),
        "port_event": port_event_scatter(records),
    }
