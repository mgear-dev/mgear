"""Qt/Maya-free SVG geometry import.

Parses a defined *subset* of SVG geometry into a normalized subpath list any
tool can turn into a ``QPainterPath`` (or other renderer), and reports which
unsupported elements were discarded -- a graceful partial import: an SVG that
mixes supported and unsupported content still imports its supported shapes, and
a malformed element never raises. Lives in ``mgear.core`` so tools beyond the
anim picker can reuse it.

Supported geometry (converted): ``path`` (full ``d`` command set), ``rect``
(with ``rx`` / ``ry``), ``circle``, ``ellipse``, ``polygon``, ``polyline``,
``line`` -- nested in ``svg`` / ``g`` containers whose ``transform`` (and the
root ``viewBox``) are applied. Everything else (``text``, ``image``, ``use``,
gradients, ``filter``, ``clipPath``, ``mask``, ``pattern``, ``style``,
``script``, animation) is discarded and its tag collected into the report.

Output segment vocabulary (coordinates absolute, in the fitted space)::

    ("M", x, y)                        start a subpath
    ("L", x, y)                        line
    ("C", x1, y1, x2, y2, x, y)        cubic Bezier
    ("Z",)                             close the subpath

Higher-level commands are normalized to these: ``H`` / ``V`` -> ``L``; smooth
``S`` / ``T`` reflected; quadratic ``Q`` / ``T`` -> cubic; elliptical arc ``A``
-> a sequence of cubics; ``rect`` / ``circle`` / ``ellipse`` / ``polygon`` /
``polyline`` / ``line`` -> the equivalent segments.

``parse_svg`` also returns a suggested render *mode* (``fill`` or ``stroke``)
from the source's fill / stroke presentation attributes, so line-art icons
(``fill:none; stroke:...``) can be drawn as strokes rather than filled to
nothing. ``flip_y`` negates y for callers whose view is y-up (e.g. the anim
picker); the default keeps SVG's native y-down.

Pure string / math only (no Qt, no Maya), so the tokenizer, arc conversion,
transform composition, and fit are unit-testable standalone.
"""

import math
import re
import xml.etree.ElementTree as ElementTree


# Default fitted extent: the imported shape's larger side is scaled to this.
DEFAULT_SIZE = 40.0

# Suggested render modes returned alongside the geometry.
MODE_FILL = "fill"
MODE_STROKE = "stroke"

# Geometry element tags this module converts (local names, namespace-stripped).
SUPPORTED_TAGS = (
    "path",
    "rect",
    "circle",
    "ellipse",
    "polygon",
    "polyline",
    "line",
)

# Container tags recursed into (their geometry children are converted).
_CONTAINER_TAGS = ("svg", "g")

# A cubic quarter-circle control-point constant (kappa) for arc / ellipse fits.
_KAPPA = 0.5522847498307936


def _local(tag):
    """Return an element tag without its ``{namespace}`` prefix."""
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


# =============================================================================
# Number / token parsing
# =============================================================================
_NUMBER_RE = re.compile(
    r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
)


def _numbers(text):
    """Return every number in ``text`` as a list of floats."""
    return [float(match) for match in _NUMBER_RE.findall(text or "")]


# Path command letters and how many numbers each takes per repetition.
_PATH_ARGS = {
    "M": 2,
    "L": 2,
    "H": 1,
    "V": 1,
    "C": 6,
    "S": 4,
    "Q": 4,
    "T": 2,
    "A": 7,
    "Z": 0,
}

_PATH_TOKEN_RE = re.compile(
    r"([MmLlHhVvCcSsQqTtAaZz])|([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)"
)


def _tokenize_path(data):
    """Split a path ``d`` string into (command, number) tokens.

    Returns a flat list of items, each either a one-character command string
    or a float. Malformed characters are ignored.
    """
    tokens = []
    for command, number in _PATH_TOKEN_RE.findall(data or ""):
        if command:
            tokens.append(command)
        elif number:
            tokens.append(float(number))
    return tokens


# =============================================================================
# Transforms (2x3 affine as (a, b, c, d, e, f))
# =============================================================================
_IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _mat_mul(m1, m2):
    """Return the product of two 2x3 affine matrices (``m1`` then ``m2``)."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply(mat, x, y):
    """Apply a 2x3 affine matrix to a point, returning ``(x, y)``."""
    a, b, c, d, e, f = mat
    return (a * x + c * y + e, b * x + d * y + f)


def _parse_transform(text):
    """Parse an SVG ``transform`` attribute into a single 2x3 matrix."""
    mat = _IDENTITY
    if not text:
        return mat
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", text):
        values = _numbers(args)
        mat = _mat_mul(mat, _transform_matrix(name, values))
    return mat


def _transform_matrix(name, values):
    """Return the 2x3 matrix for a single transform function."""
    if name == "translate":
        tx = values[0] if values else 0.0
        ty = values[1] if len(values) > 1 else 0.0
        return (1.0, 0.0, 0.0, 1.0, tx, ty)
    if name == "scale":
        sx = values[0] if values else 1.0
        sy = values[1] if len(values) > 1 else sx
        return (sx, 0.0, 0.0, sy, 0.0, 0.0)
    if name == "rotate" and values:
        angle = math.radians(values[0])
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        rot = (cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
        if len(values) >= 3:
            cx, cy = values[1], values[2]
            rot = _mat_mul((1.0, 0.0, 0.0, 1.0, cx, cy), rot)
            rot = _mat_mul(rot, (1.0, 0.0, 0.0, 1.0, -cx, -cy))
        return rot
    if name == "matrix" and len(values) >= 6:
        return tuple(values[:6])
    if name == "skewX" and values:
        return (1.0, 0.0, math.tan(math.radians(values[0])), 1.0, 0.0, 0.0)
    if name == "skewY" and values:
        return (1.0, math.tan(math.radians(values[0])), 0.0, 1.0, 0.0, 0.0)
    return _IDENTITY


# =============================================================================
# Arc -> cubic
# =============================================================================
def _arc_to_cubics(x0, y0, rx, ry, phi_deg, large_arc, sweep, x, y):
    """Convert an SVG elliptical arc to a list of cubic segments.

    Returns a list of ``(x1, y1, x2, y2, ex, ey)`` cubic control/end tuples
    starting from the current point ``(x0, y0)``; an empty list when the arc is
    degenerate (caller should fall back to a line).
    """
    if rx == 0 or ry == 0:
        return []
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(phi_deg % 360.0)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)

    dx = (x0 - x) / 2.0
    dy = (y0 - y) / 2.0
    x1p = cos_phi * dx + sin_phi * dy
    y1p = -sin_phi * dx + cos_phi * dy

    # Correct out-of-range radii.
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1.0:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale

    denom = (rx * rx * y1p * y1p) + (ry * ry * x1p * x1p)
    num = (rx * rx * ry * ry) - (rx * rx * y1p * y1p) - (ry * ry * x1p * x1p)
    factor = math.sqrt(max(0.0, num / denom)) if denom else 0.0
    if large_arc == sweep:
        factor = -factor
    cxp = factor * rx * y1p / ry
    cyp = -factor * ry * x1p / rx

    cx = cos_phi * cxp - sin_phi * cyp + (x0 + x) / 2.0
    cy = sin_phi * cxp + cos_phi * cyp + (y0 + y) / 2.0

    def angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        length = math.hypot(ux, uy) * math.hypot(vx, vy)
        value = 0.0 if length == 0 else max(-1.0, min(1.0, dot / length))
        result = math.acos(value)
        if ux * vy - uy * vx < 0:
            result = -result
        return result

    theta1 = angle(1.0, 0.0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    delta = angle(
        (x1p - cxp) / rx,
        (y1p - cyp) / ry,
        (-x1p - cxp) / rx,
        (-y1p - cyp) / ry,
    )
    if not sweep and delta > 0:
        delta -= 2.0 * math.pi
    elif sweep and delta < 0:
        delta += 2.0 * math.pi

    segments = max(1, int(math.ceil(abs(delta) / (math.pi / 2.0))))
    result = []
    step = delta / segments
    t = (4.0 / 3.0) * math.tan(step / 4.0)
    for index in range(segments):
        a1 = theta1 + index * step
        a2 = a1 + step
        cos1, sin1 = math.cos(a1), math.sin(a1)
        cos2, sin2 = math.cos(a2), math.sin(a2)

        def point(cos_a, sin_a):
            px = cos_phi * rx * cos_a - sin_phi * ry * sin_a + cx
            py = sin_phi * rx * cos_a + cos_phi * ry * sin_a + cy
            return px, py

        p1x, p1y = point(cos1, sin1)
        p2x, p2y = point(cos2, sin2)
        c1x = p1x + t * (cos_phi * -rx * sin1 - sin_phi * ry * cos1)
        c1y = p1y + t * (sin_phi * -rx * sin1 + cos_phi * ry * cos1)
        c2x = p2x - t * (cos_phi * -rx * sin2 - sin_phi * ry * cos2)
        c2y = p2y - t * (sin_phi * -rx * sin2 + cos_phi * ry * cos2)
        result.append((c1x, c1y, c2x, c2y, p2x, p2y))
    return result


# =============================================================================
# Path "d" -> normalized subpaths
# =============================================================================
def _parse_path_d(data):
    """Convert a path ``d`` string to subpaths of M/L/C/Z segments."""
    tokens = _tokenize_path(data)
    subpaths = []
    current = []
    index = 0
    length = len(tokens)

    cx = cy = 0.0  # current point
    sx = sy = 0.0  # subpath start
    prev_cmd = ""
    prev_c2 = None  # previous cubic 2nd control (for S)
    prev_q = None  # previous quadratic control (for T)

    def flush():
        if current:
            subpaths.append(list(current))

    while index < length:
        token = tokens[index]
        if isinstance(token, str):
            command = token
            index += 1
        else:
            # Implicit repeat: reuse the previous command; a repeated moveto
            # becomes a lineto (SVG spec), preserving relative/absolute case.
            command = prev_cmd
            if command in ("M", "m"):
                command = "l" if command.islower() else "L"
        upper = command.upper()
        relative = command.islower()
        need = _PATH_ARGS.get(upper, 0)
        args = tokens[index : index + need]
        if len(args) < need or any(isinstance(a, str) for a in args):
            break
        index += need

        if upper == "M":
            x, y = args
            if relative:
                x, y = cx + x, cy + y
            flush()
            current = [("M", x, y)]
            cx, cy = sx, sy = x, y
        elif upper == "L":
            x, y = args
            if relative:
                x, y = cx + x, cy + y
            current.append(("L", x, y))
            cx, cy = x, y
        elif upper == "H":
            x = args[0] + (cx if relative else 0.0)
            current.append(("L", x, cy))
            cx = x
        elif upper == "V":
            y = args[0] + (cy if relative else 0.0)
            current.append(("L", cx, y))
            cy = y
        elif upper == "C":
            pts = _rel_points(args, cx, cy, relative)
            current.append(("C",) + pts)
            prev_c2 = (pts[2], pts[3])
            cx, cy = pts[4], pts[5]
        elif upper == "S":
            c1 = _reflect(prev_c2, cx, cy, prev_cmd.upper() in ("C", "S"))
            pts = _rel_points(args, cx, cy, relative)
            current.append(("C", c1[0], c1[1], pts[0], pts[1], pts[2], pts[3]))
            prev_c2 = (pts[0], pts[1])
            cx, cy = pts[2], pts[3]
        elif upper == "Q":
            pts = _rel_points(args, cx, cy, relative)
            seg = _quad_to_cubic(cx, cy, pts[0], pts[1], pts[2], pts[3])
            current.append(seg)
            prev_q = (pts[0], pts[1])
            cx, cy = pts[2], pts[3]
        elif upper == "T":
            qc = _reflect(prev_q, cx, cy, prev_cmd.upper() in ("Q", "T"))
            x, y = args
            if relative:
                x, y = cx + x, cy + y
            seg = _quad_to_cubic(cx, cy, qc[0], qc[1], x, y)
            current.append(seg)
            prev_q = qc
            cx, cy = x, y
        elif upper == "A":
            rx, ry, rot, large, sweep, x, y = args
            if relative:
                x, y = cx + x, cy + y
            cubics = _arc_to_cubics(
                cx, cy, rx, ry, rot, int(large), int(sweep), x, y
            )
            if cubics:
                for c in cubics:
                    current.append(("C",) + c)
            else:
                current.append(("L", x, y))
            cx, cy = x, y
        elif upper == "Z":
            current.append(("Z",))
            cx, cy = sx, sy

        if upper not in ("C", "S"):
            prev_c2 = None
        if upper not in ("Q", "T"):
            prev_q = None
        prev_cmd = command

    flush()
    return subpaths


def _rel_points(args, cx, cy, relative):
    """Return ``args`` as absolute coordinates (offset by current point)."""
    if not relative:
        return tuple(args)
    out = []
    for i, value in enumerate(args):
        out.append(value + (cx if i % 2 == 0 else cy))
    return tuple(out)


def _reflect(prev_ctrl, cx, cy, had_prev):
    """Return the reflected control point for a smooth ``S`` / ``T``."""
    if had_prev and prev_ctrl is not None:
        return (2.0 * cx - prev_ctrl[0], 2.0 * cy - prev_ctrl[1])
    return (cx, cy)


def _quad_to_cubic(x0, y0, qx, qy, x, y):
    """Return a cubic ``C`` segment equivalent to a quadratic Bezier."""
    c1x = x0 + 2.0 / 3.0 * (qx - x0)
    c1y = y0 + 2.0 / 3.0 * (qy - y0)
    c2x = x + 2.0 / 3.0 * (qx - x)
    c2y = y + 2.0 / 3.0 * (qy - y)
    return ("C", c1x, c1y, c2x, c2y, x, y)


# =============================================================================
# Basic shapes -> normalized subpaths
# =============================================================================
def _attr_float(element, name, default=0.0):
    """Return a float attribute, or ``default`` when absent / unparseable."""
    try:
        return float(element.get(name, default))
    except (TypeError, ValueError):
        return default


def _paint_prop(element, name, inherited):
    """Return a paint property (``fill`` / ``stroke``) with SVG inheritance.

    Reads the ``style="fill:...;stroke:..."`` declaration first, then the
    presentation attribute, else the value inherited from the parent.
    """
    style = element.get("style", "")
    if style:
        for declaration in style.split(";"):
            key, _, value = declaration.partition(":")
            if key.strip() == name and value.strip():
                return value.strip().lower()
    value = element.get(name)
    if value:
        return value.strip().lower()
    return inherited


def _rect_subpaths(element):
    x = _attr_float(element, "x")
    y = _attr_float(element, "y")
    width = _attr_float(element, "width")
    height = _attr_float(element, "height")
    if width <= 0 or height <= 0:
        return []
    rx = element.get("rx")
    ry = element.get("ry")
    rx = _attr_float(element, "rx") if rx is not None else 0.0
    ry = _attr_float(element, "ry") if ry is not None else rx
    if rx <= 0 and ry <= 0:
        return [
            [
                ("M", x, y),
                ("L", x + width, y),
                ("L", x + width, y + height),
                ("L", x, y + height),
                ("Z",),
            ]
        ]
    rx = min(rx or ry, width / 2.0)
    ry = min(ry or rx, height / 2.0)
    ox, oy = rx * _KAPPA, ry * _KAPPA
    right, bottom = x + width, y + height
    top, left = y, x
    segs = [("M", x + rx, top)]
    segs.append(("L", right - rx, top))
    segs.append(
        ("C", right - rx + ox, top, right, top + ry - oy, right, y + ry)
    )
    segs.append(("L", right, bottom - ry))
    segs.append(
        ("C", right, bottom - ry + oy, right - rx + ox, bottom,
         right - rx, bottom)
    )
    segs.append(("L", x + rx, bottom))
    segs.append(
        ("C", x + rx - ox, bottom, left, bottom - ry + oy, left, bottom - ry)
    )
    segs.append(("L", left, y + ry))
    segs.append(("C", left, y + ry - oy, x + rx - ox, top, x + rx, top))
    segs.append(("Z",))
    return [segs]


def _ellipse_subpaths(cx, cy, rx, ry):
    if rx <= 0 or ry <= 0:
        return []
    ox, oy = rx * _KAPPA, ry * _KAPPA
    return [
        [
            ("M", cx + rx, cy),
            ("C", cx + rx, cy + oy, cx + ox, cy + ry, cx, cy + ry),
            ("C", cx - ox, cy + ry, cx - rx, cy + oy, cx - rx, cy),
            ("C", cx - rx, cy - oy, cx - ox, cy - ry, cx, cy - ry),
            ("C", cx + ox, cy - ry, cx + rx, cy - oy, cx + rx, cy),
            ("Z",),
        ]
    ]


def _poly_subpaths(element, close):
    numbers = _numbers(element.get("points"))
    if len(numbers) < 4:
        return []
    segs = [("M", numbers[0], numbers[1])]
    for i in range(2, len(numbers) - 1, 2):
        segs.append(("L", numbers[i], numbers[i + 1]))
    if close:
        segs.append(("Z",))
    return [segs]


def _element_subpaths(element):
    """Return the normalized subpaths for a supported geometry element."""
    tag = _local(element.tag)
    if tag == "path":
        return _parse_path_d(element.get("d"))
    if tag == "rect":
        return _rect_subpaths(element)
    if tag == "circle":
        r = _attr_float(element, "r")
        return _ellipse_subpaths(
            _attr_float(element, "cx"), _attr_float(element, "cy"), r, r
        )
    if tag == "ellipse":
        return _ellipse_subpaths(
            _attr_float(element, "cx"),
            _attr_float(element, "cy"),
            _attr_float(element, "rx"),
            _attr_float(element, "ry"),
        )
    if tag == "polygon":
        return _poly_subpaths(element, close=True)
    if tag == "polyline":
        return _poly_subpaths(element, close=False)
    if tag == "line":
        return [
            [
                ("M", _attr_float(element, "x1"), _attr_float(element, "y1")),
                ("L", _attr_float(element, "x2"), _attr_float(element, "y2")),
            ]
        ]
    return []


# =============================================================================
# Tree walk + transform application
# =============================================================================
def _map_segment(segment, fn):
    """Return ``segment`` with ``fn(x, y)`` applied to each coord pair.

    A ``Z`` (close) segment carries no coordinates and passes through.
    """
    if segment[0] == "Z":
        return segment
    coords = segment[1:]
    out = [segment[0]]
    for i in range(0, len(coords), 2):
        nx, ny = fn(coords[i], coords[i + 1])
        out.append(nx)
        out.append(ny)
    return tuple(out)


def _transform_segment(segment, mat):
    """Return ``segment`` with every coordinate pair passed through ``mat``."""
    return _map_segment(segment, lambda x, y: _apply(mat, x, y))


def _walk(element, matrix, paint, subpaths, dropped, votes):
    """Recurse ``element``, converting supported geometry under ``matrix``.

    ``paint`` is the inherited ``(fill, stroke)`` pair; ``votes`` is a mutable
    ``[fill_count, stroke_count]`` accumulated per geometry element to hint a
    render mode.
    """
    tag = _local(element.tag)
    local_matrix = _mat_mul(matrix, _parse_transform(element.get("transform")))
    fill = _paint_prop(element, "fill", paint[0])
    stroke = _paint_prop(element, "stroke", paint[1])

    if tag in _CONTAINER_TAGS:
        for child in list(element):
            _walk(
                child, local_matrix, (fill, stroke), subpaths, dropped, votes
            )
        return
    if tag in SUPPORTED_TAGS:
        try:
            element_subpaths = _element_subpaths(element)
        except Exception:
            dropped.add(tag)
            return
        for sub in element_subpaths:
            subpaths.append(
                [_transform_segment(seg, local_matrix) for seg in sub]
            )
        # Vote fill vs stroke. SVG's default fill is solid (None -> filled), so
        # an element counts as stroke-only when fill is explicitly "none" and a
        # stroke is set.
        if fill == "none" and stroke and stroke != "none":
            votes[1] += 1
        else:
            votes[0] += 1
        return
    # Anything else (text/image/gradient/filter/use/style/script/...) is
    # discarded, but its tag is reported.
    dropped.add(tag)


# =============================================================================
# Fit
# =============================================================================
def _iter_coords(subpaths):
    """Yield every ``(x, y)`` coordinate pair across ``subpaths``."""
    for sub in subpaths:
        for segment in sub:
            coords = segment[1:]
            for i in range(0, len(coords), 2):
                yield coords[i], coords[i + 1]


def _bounds(subpaths):
    """Return ``(minx, miny, maxx, maxy)`` over every coordinate, or None."""
    xs = []
    ys = []
    for x, y in _iter_coords(subpaths):
        xs.append(x)
        ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _map_subpaths(subpaths, fn):
    """Return ``subpaths`` with ``fn(x, y)`` applied to every coord pair."""
    return [[_map_segment(seg, fn) for seg in sub] for sub in subpaths]


def _fit(subpaths, size, flip_y):
    """Center on the origin and scale the larger side to ``size``.

    When ``flip_y`` is True the geometry is negated in y (SVG is y-down; a y-up
    view -- e.g. the anim picker -- needs it flipped to import upright).
    """
    box = _bounds(subpaths)
    if box is None:
        return subpaths
    minx, miny, maxx, maxy = box
    extent = max(maxx - minx, maxy - miny)
    scale = (size / extent) if extent else 1.0
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0
    sy = -scale if flip_y else scale
    return _map_subpaths(
        subpaths, lambda x, y: ((x - cx) * scale, (y - cy) * sy)
    )


# =============================================================================
# Subpath transforms (scale / mirror -- bake into the geometry)
# =============================================================================
def scale_subpaths(subpaths, sx, sy):
    """Return ``subpaths`` with every coordinate scaled by ``(sx, sy)``.

    Baked into the geometry (the vector analog of moving polygon handles), so a
    scale or mirror persists. A vertical-axis mirror is ``scale_subpaths(subs,
    -1.0, 1.0)``. Scaling the Bezier control points is an exact affine scale.

    Args:
        subpaths (list): normalized subpaths.
        sx (float): x scale factor.
        sy (float): y scale factor.

    Returns:
        list: the scaled subpaths.
    """
    return _map_subpaths(subpaths, lambda x, y: (x * sx, y * sy))


# =============================================================================
# Public entry point
# =============================================================================
def parse_svg(text, size=DEFAULT_SIZE, flip_y=False):
    """Parse SVG ``text`` into ``(subpaths, dropped, mode)``.

    Args:
        text (str): the SVG document.
        size (float): the fitted extent of the imported shape's larger side.
        flip_y (bool): negate y (for a y-up view, e.g. the anim picker).

    Returns:
        tuple: ``(subpaths, dropped, mode)`` where ``subpaths`` is a list of
        subpaths (each a list of ``M`` / ``L`` / ``C`` / ``Z`` segment tuples,
        fitted into the target space), ``dropped`` is a sorted list of the
        unsupported element tags discarded, and ``mode`` is the suggested
        render mode (``MODE_STROKE`` for line-art whose geometry is mostly
        stroked, else ``MODE_FILL``). ``subpaths`` is empty when the SVG has no
        supported geometry (or is unparseable).
    """
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return ([], ["<malformed>"], MODE_FILL)

    subpaths = []
    dropped = set()
    votes = [0, 0]  # [fill, stroke]

    # Apply the root viewBox as an initial translate so geometry sits near the
    # origin before fitting (the actual scale is handled by _fit).
    matrix = _IDENTITY
    view_box = _numbers(root.get("viewBox"))
    if len(view_box) == 4:
        matrix = (1.0, 0.0, 0.0, 1.0, -view_box[0], -view_box[1])

    _walk(root, matrix, (None, None), subpaths, dropped, votes)
    mode = MODE_STROKE if votes[1] > votes[0] else MODE_FILL
    if not subpaths:
        return ([], sorted(dropped), mode)
    return (_fit(subpaths, size, flip_y), sorted(dropped), mode)
