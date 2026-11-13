"""Deterministic SVG views for the Amargosa M03 measured-data lesson."""
from __future__ import annotations

import html


FLIGHT_COLORS = ("#2b6f9c", "#178a89", "#a36b20", "#79539a", "#427b53", "#b45742",
                 "#4f657d", "#9b7937", "#317c78", "#8e5661", "#5a749b", "#647d3d")


def render_figures(result: dict, rows: list[dict], selection: dict) -> tuple[str, str]:
    """Return source-track geometry and masked interpolation as self-contained SVGs."""
    xmin, xmax, ymin, ymax = selection["bounds_projected_m_half_open"]
    if not xmin < xmax or not ymin < ymax:
        raise ValueError("cannot render a non-positive Amargosa window")

    def sx(x: float, left: float, width: float) -> float:
        return left + (x - xmin) / (xmax - xmin) * width

    def sy(y: float, top: float, height: float) -> float:
        return top + height - (y - ymin) / (ymax - ymin) * height

    def esc(text: object) -> str:
        return html.escape(str(text), quote=True)

    def head(title: str, subtitle: str) -> list[str]:
        return ['<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="690" viewBox="0 0 1180 690">',
                '<rect width="100%" height="100%" fill="#f5f7f8"/>',
                f'<text x="42" y="43" font-family="Arial,sans-serif" font-size="25" font-weight="700" fill="#102a43">{esc(title)}</text>',
                f'<text x="42" y="69" font-family="Arial,sans-serif" font-size="14" fill="#486581">{esc(subtitle)}</text>']

    def axes(left: float, top: float, width: float, height: float) -> list[str]:
        out = [f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="#ffffff" stroke="#9fb3c8"/>']
        for i in range(6):
            px = left + i * width / 5
            py = top + i * height / 5
            xv = xmin + i * (xmax - xmin) / 5
            yv = ymax - i * (ymax - ymin) / 5
            out.extend([
                f'<path d="M {px:.1f} {top} V {top + height}" stroke="#d9e2ec"/>',
                f'<path d="M {left} {py:.1f} H {left + width}" stroke="#d9e2ec"/>',
                f'<text x="{px:.1f}" y="{top + height + 22}" text-anchor="middle" font-family="Arial" font-size="11" fill="#486581">{xv / 1000:.2f}</text>',
                f'<text x="{left - 12}" y="{py + 4:.1f}" text-anchor="end" font-family="Arial" font-size="11" fill="#486581">{yv / 1000:.2f}</text>',
            ])
        out.extend([
            f'<text x="{left + width / 2}" y="{top + height + 51}" text-anchor="middle" font-family="Arial" font-size="12" fill="#334e68">Easting (km, NAD27 / UTM 11N)</text>',
            f'<text x="24" y="{top + height / 2}" transform="rotate(-90 24 {top + height / 2})" text-anchor="middle" font-family="Arial" font-size="12" fill="#334e68">Northing (km)</text>',
        ])
        return out

    by_track: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        by_track.setdefault((row["role"], row["track_id"]), []).append(row)
    heldout = set(result["split"]["holdout_line_ids"])

    first = head("Amargosa · sampled survey geometry",
                 "USGS levelled anomaly · representative segments · orange rings mark held-out flight lines")
    left, top, width, height = 92, 102, 790, 475
    first += axes(left, top, width, height)
    for (role, track_id), track in sorted(by_track.items()):
        track.sort(key=lambda row: row["sample_order"])
        color = FLIGHT_COLORS[int(track_id[1:]) - 1] if role == "flight" else "#c17a18"
        points = " ".join(f"{sx(r['E'], left, width):.1f},{sy(r['N'], top, height):.1f}" for r in track)
        dash = ' stroke-dasharray="7 5"' if role == "tie" else ""
        stroke = "#d76a35" if track_id in heldout else color
        line_width = 4 if track_id in heldout else (3 if role == "tie" else 2.2)
        first.append(f'<polyline points="{points}" fill="none" stroke="{stroke}" stroke-width="{line_width}"{dash} opacity="0.9"/>')
        for row in track:
            cx, cy = sx(row["E"], left, width), sy(row["N"], top, height)
            if track_id in heldout:
                first.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#fff" stroke="#d76a35" stroke-width="1.5"/>')
            else:
                first.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.1" fill="{color}" opacity="0.75"/>')
    first.extend([
        '<rect x="910" y="115" width="230" height="190" rx="12" fill="#fff" stroke="#d9e2ec"/>',
        '<text x="930" y="145" font-family="Arial" font-size="15" font-weight="700" fill="#102a43">Survey layout</text>',
        f'<text x="930" y="177" font-family="Arial" font-size="13" fill="#334e68">Flights · {selection["track_count"]["flight"]}</text>',
        f'<text x="930" y="201" font-family="Arial" font-size="13" fill="#334e68">Tie lines · {selection["track_count"]["tie"]}</text>',
        f'<text x="930" y="225" font-family="Arial" font-size="13" fill="#334e68">Retained samples · {selection["selected_row_count"]}</text>',
        '<text x="930" y="249" font-family="Arial" font-size="13" fill="#334e68">Window · 5 km × 5 km</text>',
        '<line x1="930" y1="275" x2="966" y2="275" stroke="#178a89" stroke-width="3"/><text x="976" y="280" font-family="Arial" font-size="12" fill="#334e68">flight fit</text>',
        '<line x1="930" y1="294" x2="966" y2="294" stroke="#d76a35" stroke-width="4"/><text x="976" y="299" font-family="Arial" font-size="12" fill="#334e68">withheld flight</text>',
        '<line x1="930" y1="322" x2="966" y2="322" stroke="#c17a18" stroke-width="3" stroke-dasharray="7 5"/><text x="976" y="327" font-family="Arial" font-size="12" fill="#334e68">tie · QC only</text>',
        '<text x="910" y="385" font-family="Arial" font-size="12" fill="#486581">Grouped source segments are listed</text>',
        '<text x="910" y="403" font-family="Arial" font-size="12" fill="#486581">in the result manifest with the</text>',
        '<text x="910" y="421" font-family="Arial" font-size="12" fill="#486581">selected and omitted IDs.</text>',
        '</svg>',
    ])

    grid = result["grid"]
    gx, gy = grid["x_easting_m"], grid["y_northing_m"]
    values, mask = grid["values"], grid["support_mask"]
    supported_values = [values[j][i] for j in range(len(gy)) for i in range(len(gx)) if mask[j][i]]
    if not supported_values:
        raise ValueError("interpolation has no supported grid cells")
    vmax = max(abs(min(supported_values)), abs(max(supported_values))) or 1.0

    def diverging(value: float) -> str:
        t = max(-1.0, min(1.0, value / vmax))
        a, b, q = ((32, 83, 130), (244, 247, 249), t + 1) if t < 0 else ((244, 247, 249), (181, 78, 47), t)
        rgb = tuple(round(a[k] + q * (b[k] - a[k])) for k in range(3))
        return "#%02x%02x%02x" % rgb

    second = head("Amargosa · levelled-anomaly interpolation",
                  "Flight lines fit the surface · withheld lines score it · unsupported cells remain masked")
    second += axes(left, top, width, height)
    cellw, cellh = width / (len(gx) - 1), height / (len(gy) - 1)
    for j in range(len(gy) - 1):
        for i in range(len(gx) - 1):
            cx, cy = sx(gx[i], left, width), sy(gy[j + 1], top, height)
            supported = mask[j][i] and mask[j][i + 1] and mask[j + 1][i] and mask[j + 1][i + 1]
            if supported:
                value = sum((values[j][i], values[j][i + 1], values[j + 1][i], values[j + 1][i + 1])) / 4
                fill = diverging(value)
            else:
                fill = "#edf1f4"
            second.append(f'<rect x="{cx:.2f}" y="{cy:.2f}" width="{cellw + 0.4:.2f}" height="{cellh + 0.4:.2f}" fill="{fill}"/>')
    for (_, track_id), track in sorted(by_track.items()):
        for row in track[::3]:
            cx, cy = sx(row["E"], left, width), sy(row["N"], top, height)
            if track_id in heldout:
                second.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.4" fill="#fff" stroke="#d76a35" stroke-width="1.7"/>')
            else:
                second.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.0" fill="#102a43" opacity="0.75"/>')
    h = result["heldout_interpolation"]
    second.extend([
        '<rect x="910" y="115" width="230" height="225" rx="12" fill="#fff" stroke="#d9e2ec"/>',
        '<text x="930" y="145" font-family="Arial" font-size="15" font-weight="700" fill="#102a43">Held-line check</text>',
        f'<text x="930" y="178" font-family="Arial" font-size="13" fill="#334e68">RMSE · {h["rmse"]:.2f} nT</text>',
        f'<text x="930" y="202" font-family="Arial" font-size="13" fill="#334e68">MAE · {h["mae"]:.2f} nT</text>',
        f'<text x="930" y="226" font-family="Arial" font-size="13" fill="#334e68">Support · {100 * h["coverage_fraction"]:.1f}%</text>',
        f'<text x="930" y="250" font-family="Arial" font-size="13" fill="#334e68">Held-out rows · {h["heldout_row_count"]}</text>',
        '<text x="930" y="282" font-family="Arial" font-size="12" fill="#486581">Blue-white-red · nT</text>',
        '<circle cx="939" cy="309" r="4" fill="#fff" stroke="#d76a35" stroke-width="2"/><text x="952" y="314" font-family="Arial" font-size="12" fill="#334e68">held-out observation</text>',
        '<text x="910" y="390" font-family="Arial" font-size="12" fill="#486581">Grey cells lack a supported training</text>',
        '<text x="910" y="408" font-family="Arial" font-size="12" fill="#486581">hull. They are not zero-field</text>',
        '<text x="910" y="426" font-family="Arial" font-size="12" fill="#486581">measurements or extrapolations.</text>',
        '</svg>',
    ])
    return "\n".join(first), "\n".join(second)
