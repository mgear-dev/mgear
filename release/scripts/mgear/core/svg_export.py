"""Qt-free writer from vector layers to SVG text.

The counterpart of ``mgear.core.svg_import``: takes layers of normalized
subpaths (``M`` / ``L`` / ``C`` / ``Z`` segments) and writes a standalone SVG
document. Each visible layer becomes a ``<g>`` carrying its fill or stroke
presentation attributes around one ``<path>``; the root ``viewBox`` fits the
geometry. ``flip_y`` negates y for callers whose coordinates are y-up (e.g.
the anim picker), so the file reads upright in SVG's y-down space.

A layer is a dict with ``subpaths`` and optional ``name``, ``mode``
(``"fill"`` / ``"stroke"``), ``stroke_width`` and ``visible`` keys, matching
the anim picker's vector layer model.

Pure string / math only (no Qt, no Maya), so it is unit-testable standalone.
"""

from xml.sax.saxutils import quoteattr

from mgear.core import vector_path
from mgear.core.svg_import import MODE_STROKE


def _number(value, precision):
    """Format a coordinate compactly (no trailing zeros, no "-0")."""
    text = "{:.{p}f}".format(value, p=precision).rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def path_data(subpaths, precision=4):
    """Return the SVG ``d`` attribute for a list of subpaths.

    Args:
        subpaths (list): Normalized subpaths.
        precision (int, optional): Decimal places written per coordinate.

    Returns:
        str: Path data such as ``"M 0 0 L 10 0 Z"``.
    """
    parts = []
    for subpath in subpaths:
        for segment in subpath:
            numbers = " ".join(_number(v, precision) for v in segment[1:])
            parts.append(segment[0] + (" " + numbers if numbers else ""))
    return " ".join(parts)


def to_svg(layers, flip_y=False, color="#000000", padding=1.0, precision=4):
    """Write layers of subpaths as an SVG document.

    Args:
        layers (list): Layer dicts, back to front (hidden layers skipped).
        flip_y (bool, optional): Negate y (input is y-up).
        color (str, optional): Fill / stroke color for layers without
            their own ``color``.
        padding (float, optional): Margin added around the geometry in the
            ``viewBox`` (stroke half-widths are added on top).
        precision (int, optional): Decimal places written per coordinate.

    Returns:
        str: The SVG document text.
    """
    visible = [layer for layer in layers if layer.get("visible", True)]
    if flip_y:
        visible = [
            dict(
                layer,
                subpaths=vector_path.scale(layer.get("subpaths", []), 1.0, -1.0),
            )
            for layer in visible
        ]

    all_subpaths = []
    max_stroke = 0.0
    for layer in visible:
        all_subpaths.extend(layer.get("subpaths", []))
        if layer.get("mode") == MODE_STROKE:
            max_stroke = max(max_stroke, float(layer.get("stroke_width", 1.0)))
    box = vector_path.bounds(all_subpaths) or (0.0, 0.0, 0.0, 0.0)
    margin = padding + max_stroke / 2.0
    min_x = box[0] - margin
    min_y = box[1] - margin
    width = (box[2] - box[0]) + 2.0 * margin
    height = (box[3] - box[1]) + 2.0 * margin

    view_box = " ".join(_number(v, precision) for v in (min_x, min_y, width, height))
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="{}" width="{}" '
        'height="{}">'.format(
            view_box, _number(width, precision), _number(height, precision)
        )
    ]
    for layer in visible:
        subpaths = layer.get("subpaths", [])
        if not subpaths:
            continue
        attributes = []
        layer_color = layer.get("color") or color
        if layer.get("name"):
            attributes.append("id={}".format(quoteattr(layer["name"])))
        if layer.get("mode") == MODE_STROKE:
            attributes.extend(
                (
                    'fill="none"',
                    "stroke={}".format(quoteattr(layer_color)),
                    'stroke-width="{}"'.format(
                        _number(float(layer.get("stroke_width", 1.0)), precision)
                    ),
                    'stroke-linecap="round"',
                    'stroke-linejoin="round"',
                )
            )
        else:
            attributes.extend(
                (
                    "fill={}".format(quoteattr(layer_color)),
                    'fill-rule="evenodd"',
                    'stroke="none"',
                )
            )
        lines.append("  <g {}>".format(" ".join(attributes)))
        lines.append('    <path d="{}"/>'.format(path_data(subpaths, precision)))
        lines.append("  </g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"
