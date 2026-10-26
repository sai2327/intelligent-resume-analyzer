"""
Server-rendered SVG chart builders. No JavaScript: every chart is a plain
SVG string the templates can inline, which keeps rendering deterministic,
testable, and dependency-free. All builders return dict payloads with the
geometry the templates need (never raw HTML), so presentation stays in the
templates.
"""

import math


def trend_chart(points: list, width: int = 640, height: int = 220,
                padding: int = 34) -> dict | None:
    """Line chart of ATS scores over time (chronological).

    points: [{"label": str, "score": float}] in chronological order.
    Returns axis geometry, the polyline, dot coordinates, and y-axis grid
    lines (0/25/50/75/100). None when there are fewer than 2 points."""
    usable = [p for p in points if p.get("score") is not None]
    if len(usable) < 2:
        return None

    inner_w = width - padding * 2
    inner_h = height - padding * 2
    step = inner_w / (len(usable) - 1)

    def xy(index: int, score: float) -> tuple:
        x = padding + step * index
        y = padding + inner_h * (1 - score / 100.0)
        return round(x, 1), round(y, 1)

    coords = [xy(i, p["score"]) for i, p in enumerate(usable)]
    polyline = " ".join(f"{x},{y}" for x, y in coords)

    grid = []
    for level in (0, 25, 50, 75, 100):
        _, y = xy(0, level)
        grid.append({"y": y, "level": level})

    dots = []
    for i, (p, (x, y)) in enumerate(zip(usable, coords)):
        dots.append({
            "x": x, "y": y,
            "score": round(p["score"], 1),
            "label": p.get("label", ""),
        })

    return {
        "width": width,
        "height": height,
        "padding": padding,
        "polyline": polyline,
        "dots": dots,
        "grid": grid,
        "x_axis_y": padding + inner_h,
        "x_axis_end": padding + inner_w,
    }


def grouped_bars(factors: list, candidates: list, colors: list,
                 width: int = 640, row_height: int = 30) -> dict | None:
    """Horizontal grouped bars for a resume comparison: one row per factor,
    one slim bar per candidate, width proportional to the factor score.

    factors: [{"key", "label"}] in display order.
    candidates: [{"filename", "factors": {key: score|None}}] in ranking order.
    colors: hex color per candidate (same order)."""
    usable_factors = []
    for factor in factors:
        scores = [c["factors"].get(factor["key"]) for c in candidates]
        if any(score is not None for score in scores):
            usable_factors.append(factor)
    if not usable_factors or not candidates:
        return None

    label_w = 150
    bar_w = width - label_w - 8

    rows = []
    for factor in usable_factors:
        bars = []
        for ci, candidate in enumerate(candidates):
            score = candidate["factors"].get(factor["key"])
            w = round(bar_w * (score / 100.0), 1) if score is not None else 0
            bars.append({
                "width": w,
                "color": colors[ci % len(colors)],
                "score": score,
                "title": f"{candidate['filename']}: "
                         f"{score if score is not None else 'N/A'}",
            })
        rows.append({"label": factor["label"], "bars": bars})

    return {
        "width": width,
        "row_height": row_height,
        "label_w": label_w,
        "bar_w": bar_w,
        "rows": rows,
        "height": row_height * len(rows) + 10,
        "legend": [
            {"color": colors[ci % len(colors)], "filename": c["filename"]}
            for ci, c in enumerate(candidates)
        ],
    }


def donut(slices: list, size: int = 150, thickness: int = 22) -> dict | None:
    """Donut chart via stroke-dasharray arcs.

    slices: [{"label", "value", "color"}]; values need not sum to any
    particular total - they are normalized. Only non-zero slices are drawn."""
    total = sum(s["value"] for s in slices)
    if total <= 0:
        return None

    radius = (size - thickness) / 2
    center = size / 2
    circumference = 2 * math.pi * radius

    arcs = []
    offset = 0.0
    for s in slices:
        value = s["value"]
        if value <= 0:
            continue
        fraction = value / total
        dash = round(fraction * circumference, 2)
        gap = round(circumference - dash, 2)
        # Rotate each arc to its start position; -90deg starts at 12 o'clock.
        rotation = round(-90 + offset / total * 360, 2)
        arcs.append({
            "label": s["label"],
            "value": value,
            "color": s["color"],
            "dash": dash,
            "gap": gap,
            "rotation": rotation,
        })
        offset += value

    percentage = 0
    if slices and slices[0]["value"]:
        percentage = round(slices[0]["value"] / total * 100)

    return {
        "size": size,
        "thickness": thickness,
        "radius": round(radius, 1),
        "center": center,
        "circumference": round(circumference, 2),
        "arcs": arcs,
        "center_label": f"{percentage}%",
    }


def score_bars(items: list, width: int = 640, row_height: int = 34,
               color: str = "#4f46e5") -> dict | None:
    """Horizontal bars for a simple ranked score list (e.g. the multi-JD
    ranking page): one bar per item, labeled, colored by rank position.

    items: [{"label", "score"}] already sorted best first. Scores may be None
    (rendered as an empty 'N/A' row)."""
    usable = list(items)
    if not usable:
        return None
    label_w = 220
    bar_w = width - label_w - 60

    rows = []
    for i, item in enumerate(usable):
        score = item.get("score")
        w = round(bar_w * (score / 100.0), 1) if score is not None else 0
        rows.append({
            "label": item["label"],
            "width": w,
            "score": score,
            "color": color if i == 0 else "#c7cbe8",
        })

    return {
        "width": width,
        "row_height": row_height,
        "label_w": label_w,
        "bar_w": bar_w,
        "rows": rows,
        "height": row_height * len(rows) + 8,
    }





def stacked_bar(segments: list, width: int = 640, height: int = 40,
                palette: list | None = None) -> dict | None:
    """Single horizontal stacked bar showing how a total decomposes into parts
    (e.g. overall ATS score = per-factor contributions in points).

    segments: [{"label", "points"}] - points are absolute contribution values;
    they are normalized to the bar width. Palette cycles automatically."""
    colors = palette or ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444",
                         "#8b5cf6", "#ec4899", "#14b8a6"]
    usable = [s for s in segments if s.get("points") is not None and s["points"] > 0]
    if not usable:
        return None
    total = sum(s["points"] for s in usable)
    if total <= 0:
        return None

    parts = []
    offset = 0.0
    for i, s in enumerate(usable):
        w = round(width * (s["points"] / total), 1)
        parts.append({
            "label": s["label"],
            "points": round(s["points"], 1),
            "share": round(s["points"] / total * 100, 1),
            "width": w,
            "x": round(offset, 1),
            "color": colors[i % len(colors)],
        })
        offset += w

    return {"width": width, "height": height, "parts": parts, "total": round(total, 1)}


class charts:  # namespace for `from services.charts import charts`
    trend_chart = staticmethod(trend_chart)
    grouped_bars = staticmethod(grouped_bars)
    donut = staticmethod(donut)
    score_bars = staticmethod(score_bars)
    stacked_bar = staticmethod(stacked_bar)
