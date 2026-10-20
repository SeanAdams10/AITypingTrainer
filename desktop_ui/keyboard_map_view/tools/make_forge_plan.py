"""Write web/js/forge_plan.js: the Master Forge seen from straight above.

Input is the 3D model from spike 5 (Spikes/keyboard_highlight/5_forge_3d_cad.js),
which is CharaChorder's own CAD (github.com/CharaChorder/CAD-CAM, licence
CharaChorder BY-SA-CR: non-commercial, credit CharaChorder, share alike).

Intuition: a top-down view is an orthographic projection, so a 3D point
(x, y, z) lands at plan point (x, z) and its height y only decides what covers
what. Every part (each folded shell panel, the black frame, rails, the bookend)
is projected triangle by triangle and merged into one outline, and the parts
are then painted lowest first, so higher panels cover lower ones the way they
do when you look down on the real thing. Each panel gets one flat grey from
how much it faces the light, which is what makes the folds readable in 2D.

This runs once, offline; the map view only reads the result, so drawing it
costs no more than the old traced outline.

    python desktop_ui/keyboard_map_view/tools/make_forge_plan.py

Needs shapely (pip install shapely); the app itself does not.
"""
import json
import math
import re
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SRC = REPO / "Spikes" / "keyboard_highlight" / "5_forge_3d_cad.js"
OUT = HERE.parent / "web" / "js" / "forge_plan.js"

MM = 18.0        # one plan unit = one switch pitch = 18 mm, the same scale as the 3D view
MID_Z = 37.0     # the half turns about this point, front to back (mm), as in the 3D view
SIMPLIFY = 0.12  # mm; drops points nobody can see
MIN_HOLE = 400   # mm^2; smaller holes are filled in
LIGHT = (-6.0, 15.0, 8.0)   # the 3D view's sun: above, left and in front
BOOT_H, CAP_H = 3.5, 5.66   # joystick boot and cap height (mm), as in the 3D view


def load():
    text = SRC.read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.FORGE_CAD\s*=\s*(\{.*\})\s*;?\s*$", text, re.S).group(1))


def plan(x, z):
    return ((x) / MM, (z - MID_Z) / MM)


def triangles(v, idx, k=100.0, matrix=None):
    """Triangles of an integer CAD mesh as [(x, y, z) * 3], optionally moved by a 4x4 matrix."""
    pts = [(v[i] / k, v[i + 1] / k, v[i + 2] / k) for i in range(0, len(v), 3)]
    if matrix:
        m = matrix
        pts = [(m[0] * x + m[1] * y + m[2] * z + m[3], m[4] * x + m[5] * y + m[6] * z + m[7],
                m[8] * x + m[9] * y + m[10] * z + m[11]) for x, y, z in pts]
    return [(pts[idx[t]], pts[idx[t + 1]], pts[idx[t + 2]]) for t in range(0, len(idx), 3)]


def outline(tris):
    """Top-down outline of some triangles: their projections merged."""
    polys = []
    for a, b, c in tris:
        p = Polygon([(a[0], a[2]), (b[0], b[2]), (c[0], c[2])])
        if p.area > 1e-4:
            polys.append(p.buffer(0.02, join_style=2))
    return unary_union(polys).buffer(-0.02, join_style=2).simplify(SIMPLIFY).buffer(0)


def rings(geom):
    """Shapely (multi)polygon -> list of rings in plan units; holes are just more rings (drawn even-odd)."""
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty or g.area < 0.5:
            continue
        # Small holes (switch, screw and LED cut-outs) are left out: a cap or a
        # window fills them on the real board, and the guide draws its own switches.
        for k, r in enumerate([g.exterior, *g.interiors]):
            if Polygon(r).area < (0.5 if k == 0 else MIN_HOLE):
                continue
            out.append([[round(c, 3) for c in plan(x, z)] for x, z in list(r.coords)[:-1]])
    return out


def unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def grey(normal, base, ambient=0.42):
    """Flat shading: how much a facet faces the light, as a grey of the given base brightness."""
    n, l = unit(normal), unit(LIGHT)
    if n[1] < 0:
        n = [-c for c in n]
    lam = max(0.0, sum(a * b for a, b in zip(n, l)))
    v = round(base * (ambient + (1 - ambient) * lam))
    return "#%02x%02x%02x" % (v, v, min(255, v + 6))


def mean_height(tris):
    return sum(p[1] for t in tris for p in t) / (3 * len(tris))


def main():
    cad = load()
    layers = []   # (height, class, geometry, fill)

    endo = triangles(cad["endo"]["v"], cad["endo"]["i"])
    layers.append((-1e9, "frame", outline(endo), None))
    for s in cad["skirts"]:
        tris = [(s[0], s[1], s[2]), (s[0], s[2], s[3])]
        layers.append((mean_height(tris) - 50, "frame", outline(tris), None))
    for led in cad["leds"]:
        p = led["pts"]
        layers.append((sum(q[1] for q in p) / len(p) - 50, "led", outline([(p[0], p[i], p[i + 1]) for i in range(1, len(p) - 1)]), None))
    for m in cad["rail"]["m"]:
        tris = triangles(cad["rail"]["v"], cad["rail"]["i"], matrix=m)
        layers.append((mean_height(tris), "rail", outline(tris), None))
    be = triangles(cad["bookend"]["v"], cad["bookend"]["i"], matrix=cad["bookend"]["m"])
    layers.append((mean_height(be) + 30, "rail", outline(be), None))
    for name, panel in cad["shell"].items():
        tris = triangles(panel["v"], panel["i"])
        layers.append((mean_height(tris), "metal", outline(tris), grey(panel["n"], 220)))
    layers.sort(key=lambda layer: layer[0])

    shapes = [[cls, rings(g), fill] for _, cls, g, fill in layers]
    shapes = [s for s in shapes if s[1]]

    # Switches: where the top of each cap is seen from above, and which way its
    # "north" points once projected (on the steep thumb facet north is up the
    # slope, which from above points out and slightly back).
    switches = {}
    for sid, s in cad["switches"].items():
        p, n = s["p"], unit(s["n"])
        top = [p[i] + n[i] * (BOOT_H + CAP_H / 2) for i in range(3)]
        ref = (0.0, 0.0, -1.0) if abs(n[1]) > 0.8 else (0.0, 1.0, 0.0)
        d = sum(a * b for a, b in zip(ref, n))
        north = unit([ref[i] - d * n[i] for i in range(3)])
        rot = math.degrees(math.atan2(north[2], north[0])) + 90   # 0 = north points straight up the screen
        rot = (rot + 180) % 360 - 180
        x, y = plan(top[0], top[2])
        switches[sid] = {"x": round(x, 3), "y": round(y, 3), "rot": round(rot, 1),
                         "tilt": round(math.degrees(math.acos(min(1.0, abs(n[1])))), 1)}

    lg = cad["logo"]
    lx, ly = plan(lg["p"][0], lg["p"][2])

    # The USB-C cable leaves from the inner back corner of the half.
    hull = unary_union([g.convex_hull for _, _, g, _ in layers]).convex_hull
    cx, cz = max(hull.exterior.coords, key=lambda q: q[0] - 0.6 * q[1])

    data = {
        "source": "CharaChorder Master Forge CAD (github.com/CharaChorder/CAD-CAM, BY-SA-CR), via spike 5",
        "pivot": {"x": 0, "y": 0},
        "switches": switches,
        "shapes": shapes,
        "logo": {"x": round(lx, 3), "y": round(ly, 3), "size": round(lg["size"] / MM, 3)},
        "cable": {"x": round(plan(cx, cz)[0] - 0.15, 3), "y": round(plan(cx, cz)[1] + 0.25, 3)},
        "forgeMask": cad["forgeMask"],
    }
    OUT.write_text(
        "// Generated by tools/make_forge_plan.py from spike 5's 3D model, which is CharaChorder's\n"
        "// Master Forge CAD (github.com/CharaChorder/CAD-CAM, licence CharaChorder BY-SA-CR).\n"
        "// Left half seen from straight above, in switch pitches (18 mm); x right, y toward you.\n"
        "// Do not edit by hand: rerun the script.\n"
        "window.FORGE_PLAN = " + json.dumps(data, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print("wrote", OUT, OUT.stat().st_size, "bytes,", len(shapes), "shapes")
    for sid, s in switches.items():
        print(" ", sid, s)


if __name__ == "__main__":
    main()
