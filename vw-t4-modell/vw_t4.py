#!/usr/bin/env python3
"""
Parametrisches Modell eines VW-T4-artigen Transporters (Multivan/Caravelle,
kurze Front, kurzer Radstand) als druckbare STL-Datei.

Alle Masse im Skript sind ORIGINAL-Millimeter (1:1). Am Ende wird auf den
gewuenschten Massstab skaliert (Standard 1:30 -> ca. 157 x 64 x 65 mm).

Koordinaten: x = Laengsachse (0 = Heck, L = Front), y = Breite (+y = rechte
Fahrzeugseite mit Schiebetuer), z = Hoehe (0 = Fahrbahn).

Benoetigt: pip install manifold3d numpy
Aufruf:    python3 vw_t4.py [--scale 30] [--out vw_t4_1-30.stl]
"""
import argparse
import numpy as np
import manifold3d as mf

Manifold, CrossSection, JoinType = mf.Manifold, mf.CrossSection, mf.JoinType

# ---------------------------------------------------------------------------
# Grunddaten (Original-mm)
# ---------------------------------------------------------------------------
L = 4707.0          # Laenge
HALF_W = 920.0      # halbe Breite (1840)
ROOF = 1940.0       # Dachhoehe
BELT = 1150.0       # Guertellinie (Fensterunterkante)
WHEEL_R = 317.0     # Rad 205/65 R15
X_FRONT_AXLE = 3802.0
X_REAR_AXLE = 882.0
TRACK_Y = 798.0     # Mitte Reifen (y)
TIRE_HALF = 97.0
ARCH_R = 375.0

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def smooth_profile(points, xs, sigma=15.0):
    px, pz = np.array(points, dtype=float).T
    grid = np.arange(-200, L + 200 + 1e-9, 2.0)
    vals = np.interp(grid, px, pz)
    k = np.arange(-4 * sigma, 4 * sigma + 1e-9, 2.0)
    ker = np.exp(-0.5 * (k / sigma) ** 2)
    ker /= ker.sum()
    pad = len(k) // 2
    padded = np.concatenate([np.full(pad, vals[0]), vals, np.full(pad, vals[-1])])
    sm = np.convolve(padded, ker, mode="valid")
    return np.interp(xs, grid, sm)


ZT_PTS = [(0, 1700), (25, 1850), (70, 1915), (140, 1940), (3420, 1940),
          (3500, 1925), (3560, 1890), (4080, 1170), (4130, 1135),
          (4400, 1080), (4580, 1030), (4650, 1000), (4690, 970), (L, 940)]
ZB_PTS = [(0, 420), (30, 330), (80, 290), (4600, 290), (4680, 320), (L, 380)]


def z_top(x):
    return smooth_profile(ZT_PTS, np.clip(x, 0, L))


def z_bot(x):
    return smooth_profile(ZB_PTS, np.clip(x, 0, L))


def plan_half_width(x, x0, x1, hw, r_front, r_rear):
    """Halbe Breite einer im Grundriss abgerundeten Form zwischen x0 und x1."""
    x = np.clip(x, x0, x1)
    w = np.full_like(np.asarray(x, dtype=float), hw)
    df = x - (x1 - r_front)
    m = df > 0
    w[m] = hw - r_front + np.sqrt(np.maximum(r_front ** 2 - df[m] ** 2, 0))
    dr = (x0 + r_rear) - x
    m = dr > 0
    w[m] = hw - r_rear + np.sqrt(np.maximum(r_rear ** 2 - dr[m] ** 2, 0))
    return w


def fillet_polygon(pts, radii, k):
    """Rundet jede Ecke eines konvexen Polygons mit festem Punktezaehler ab."""
    pts = np.asarray(pts, float)
    n = len(pts)
    out = []
    for i in range(n):
        P, A, B = pts[i], pts[i - 1], pts[(i + 1) % n]
        ua, ub = A - P, B - P
        la, lb = np.linalg.norm(ua), np.linalg.norm(ub)
        ua, ub = ua / la, ub / lb
        cosang = np.clip(np.dot(ua, ub), -1, 1)
        half = np.arccos(cosang) / 2
        r = max(radii[i], 1e-3)
        t = r / np.tan(half)
        tmax = 0.45 * min(la, lb)
        if t > tmax:
            t = tmax
            r = t * np.tan(half)
        bis = ua + ub
        bis /= np.linalg.norm(bis)
        C = P + bis * (r / np.sin(half))
        S, E = P + ua * t, P + ub * t
        a0 = np.arctan2(*(S - C)[::-1])
        a1 = np.arctan2(*(E - C)[::-1])
        da = (a1 - a0 + np.pi) % (2 * np.pi) - np.pi
        for s in np.linspace(0, 1, k[i]):
            a = a0 + da * s
            out.append(C + r * np.array([np.cos(a), np.sin(a)]))
    return np.array(out)


def body_section(zb, zt, w, *, crown=25.0, rb=60.0, rbelt=250.0, rt=150.0,
                 tumble_max=75.0):
    belt = min(BELT, zb + 0.55 * (zt - zb))
    tumble = max(0.0, tumble_max * (zt - belt) / (ROOF - BELT))
    wt = w - tumble
    pts = [(w, zb), (w, belt), (wt, zt - crown), (0, zt),
           (-wt, zt - crown), (-w, belt), (-w, zb)]
    radii = [rb, rbelt, rt, 3000, rt, rbelt, rb]
    k = [6, 4, 10, 5, 10, 4, 6]
    return fillet_polygon(pts, radii, k)


def loft(xs, section_fn):
    """Verbindet Querschnitte (y,z) an den Stationen xs zu einem Volumenkoerper."""
    rings = [section_fn(x) for x in xs]
    N = len(rings[0])
    verts = []
    for x, r in zip(xs, rings):
        assert len(r) == N
        verts.append(np.column_stack([np.full(N, x), r]))
    verts = np.vstack(verts)
    tris = []
    M = len(xs)
    j = np.arange(N)
    jn = (j + 1) % N
    for i in range(M - 1):
        a, b = i * N + j, i * N + jn
        c, d = (i + 1) * N + j, (i + 1) * N + jn
        tris.append(np.column_stack([a, b, d]))
        tris.append(np.column_stack([a, d, c]))
    c0 = len(verts)
    c1 = c0 + 1
    verts = np.vstack([verts, [[xs[0], *rings[0].mean(0)]], [[xs[-1], *rings[-1].mean(0)]]])
    tris.append(np.column_stack([np.full(N, c0), jn, j]))
    base = (M - 1) * N
    tris.append(np.column_stack([np.full(N, c1), base + j, base + jn]))
    tris = np.vstack(tris).astype(np.uint32)
    mesh = mf.Mesh(vert_properties=verts.astype(np.float32), tri_verts=tris)
    m = Manifold(mesh)
    assert m.status() == mf.Error.NoError, m.status()
    assert m.volume() > 0
    return m


def stations(x0, x1, fine=4.0, coarse=12.0, zone=320.0):
    a = np.arange(x0, x0 + zone, fine)
    b = np.arange(x0 + zone, x1 - zone, coarse)
    c = np.arange(x1 - zone, x1 + 1e-9, fine)
    xs = np.unique(np.concatenate([a, b, c, [x1]]))
    return xs[(xs >= x0) & (xs <= x1)]


def body_offset(d):
    """Karosserie, um d nach aussen (d>0) bzw. innen (d<0) versetzt."""
    x0, x1 = -d, L + d
    xs = stations(x0, x1)

    def sec(x):
        zt = float(z_top(x)) + d
        zb = float(z_bot(x)) - d
        w = float(plan_half_width(np.array([x]), x0, x1, HALF_W + d,
                                  max(260 + d, 20), max(90 + d, 20))[0])
        return body_section(zb, zt, w, rb=max(60 + d, 15), rt=max(150 + d, 30),
                            rbelt=250)
    return loft(xs, sec)


def rounded_poly(pts, r):
    cs = CrossSection([np.asarray(pts, float)])
    if r > 0:
        cs = cs.offset(-r, JoinType.Round, circular_segments=24).offset(
            r, JoinType.Round, circular_segments=24)
    return cs


def rrect(a0, a1, b0, b1, r=0.0):
    return rounded_poly([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], r)


def prism_xz(cs, y0, y1):
    """2D-Form in (x,z) entlang y extrudiert."""
    m = Manifold.extrude(cs, y1 - y0)
    # (a,b,c) -> (a, y1 - c, b)
    T = np.array([[1, 0, 0, 0], [0, 0, -1, y1], [0, 1, 0, 0]], dtype=float)
    return m.transform(T)


def prism_yz(cs, x0, x1):
    """2D-Form in (y,z) entlang x extrudiert."""
    m = Manifold.extrude(cs, x1 - x0)
    T = np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], dtype=float)
    return m.transform(T)


def prism_xy(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def both_sides(m):
    return m + m.mirror([0, 1, 0])


def segment_poly(p0, p1, width):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    d /= np.linalg.norm(d)
    n = np.array([-d[1], d[0]]) * width / 2
    e = d * width / 2
    return CrossSection([np.array([p0 - n - e, p1 - n + e, p1 + n + e, p0 + n - e])])


def polyline_groove_xz(points, width, y0, y1):
    parts = [prism_xz(segment_poly(points[i], points[i + 1], width), y0, y1)
             for i in range(len(points) - 1)]
    return Manifold.batch_boolean(parts, mf.OpType.Add)


def cyl_y(xc, zc, r, y0, y1, seg=96):
    c = Manifold.cylinder(y1 - y0, r, r, seg)  # entlang z
    T = np.array([[1, 0, 0, xc], [0, 0, 1, y0], [0, 1, 0, zc]], dtype=float)
    # (a,b,c) -> (xc + a, y0 + c, zc + b)
    return c.transform(T)


# ---------------------------------------------------------------------------
# Rad
# ---------------------------------------------------------------------------

def wheel():
    """Rad mit Achse = z, Aussenseite bei +z, Mittelpunkt im Ursprung."""
    seg = 120
    tire = Manifold.revolve(rrect(212, WHEEL_R, -TIRE_HALF, TIRE_HALF, 34), seg)
    # Laufflaechen-Rillen
    for h in (-52, 0, 52):
        tire -= Manifold.revolve(rrect(WHEEL_R - 9, WHEEL_R + 20, h - 7, h + 7), seg)
    # Seitenwand-Wulst (Felgenhorn-Schutz)
    tire -= Manifold.revolve(rrect(212, 228, TIRE_HALF - 12, TIRE_HALF + 5), seg)
    rim_prof = [(0, -90), (214, -90), (214, 62), (198, 68), (178, 52),
                (138, 52), (128, 60), (112, 72), (72, 80), (0, 83)]
    rim = Manifold.revolve(CrossSection([np.array(rim_prof, float)]), seg)
    # Lueftungsloecher der Stahlfelge
    for i in range(8):
        a = 2 * np.pi * i / 8 + np.pi / 8
        rim -= Manifold.cylinder(60, 17, 17, 32).translate(
            [158 * np.cos(a), 158 * np.sin(a), 22])
    # Radkappe mit Radbolzen-Andeutung
    for i in range(5):
        a = 2 * np.pi * i / 5
        rim += Manifold.cylinder(20, 13, 11, 24).translate(
            [92 * np.cos(a), 92 * np.sin(a), 64])
    rim -= Manifold.revolve(rrect(0, 40, 79, 100), 48)  # Mitte leicht vertieft
    return tire + rim


def place_wheel(w, x, side):
    # Achse z -> +y (rechts) bzw. -y (links)
    if side > 0:
        R = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
    else:
        R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)
    T = np.column_stack([R, [x, side * TRACK_Y, WHEEL_R]])
    return w.transform(T)


# ---------------------------------------------------------------------------
# Modell
# ---------------------------------------------------------------------------

def build(sockel=True):
    body = body_offset(0)
    inner12 = body_offset(-12)
    inner18 = body_offset(-18)
    inner25 = body_offset(-25)
    outer10 = body_offset(10)
    outer14 = body_offset(14)

    # ---- erhabene Details auf der Karosserie -----------------------------
    # Seitliche Schutzleiste zwischen den Radlaeufen
    strip = both_sides(box(X_REAR_AXLE + ARCH_R + 40, X_FRONT_AXLE - ARCH_R - 30,
                           860, 1100, 560, 625))
    body += strip ^ outer10
    # Radlauf-Verbreiterungen (Ring um den Ausschnitt)
    flare = Manifold()
    for xa in (X_FRONT_AXLE, X_REAR_AXLE):
        ring = cyl_y(xa, WHEEL_R, ARCH_R + 55, 840, 1100) - cyl_y(
            xa, WHEEL_R, ARCH_R - 5, 830, 1110)
        flare += both_sides(ring)
    body += flare ^ outer10 ^ box(-100, L + 100, -1200, 1200, 300, 2000)
    # Hohe Heckleuchten an den Ecken (umlaufend)
    lamp = both_sides(box(-40, 150, 690, 1000, 640, 1150)) ^ outer14
    for zg in (805, 975):
        lamp -= box(-60, 200, -1100, 1100, zg, zg + 16) - body
    body += lamp

    # ---- Vertiefungen ----------------------------------------------------
    cuts = []
    # Radlaeufe
    for xa in (X_FRONT_AXLE, X_REAR_AXLE):
        cuts.append(both_sides(cyl_y(xa, WHEEL_R, ARCH_R, 660, 1200)))

    win_z0, win_z1 = 1190, 1785
    side_windows = [
        rrect(130, 1170, win_z0, win_z1, 55),     # hinteres Seitenfenster
        rrect(1250, 2200, win_z0, win_z1, 55),    # Fondfenster
        rrect(2330, 3230, win_z0, win_z1, 55),    # Schiebetuer-/Mittelfenster
        rounded_poly([(3370, win_z0), (3985, win_z0), (3545, win_z1),
                      (3370, win_z1)], 45),       # Fahrer-/Beifahrertuer
    ]
    win = Manifold.batch_boolean([prism_xz(c, 600, 1150) for c in side_windows],
                                 mf.OpType.Add)
    cuts.append(both_sides(win) - inner18)
    # Windschutzscheibe
    cuts.append(prism_yz(rrect(-800, 800, 1195, 1862, 70), 3350, 4400) - inner18)
    # Heckscheibe
    cuts.append(prism_yz(rrect(-640, 640, 1185, 1650, 60), -60, 90) - inner18)

    # Fugen (Tueren, Heckklappe, Haube)
    G = 18
    grooves = []
    # Vordertueren (beide Seiten)
    front_door = [
        polyline_groove_xz([(3300, 330), (3300, 1820)], G, 700, 1150),
        polyline_groove_xz([(3290, 1820), (3600, 1820)], G, 700, 1150),
        polyline_groove_xz([(4195, 700), (4195, 1110), (4060, 1200), (3570, 1835)],
                           G, 760, 1150),
    ]
    grooves.append(both_sides(Manifold.batch_boolean(front_door, mf.OpType.Add)))
    # Schiebetuer rechts inkl. Fuehrungsschiene
    grooves.append(polyline_groove_xz([(2260, 330), (2260, 1822), (3300, 1822)],
                                      G, 700, 1150))
    grooves.append(polyline_groove_xz([(1180, 1158), (2260, 1158)], 26, 700, 1150))
    # Heckklappe
    hatch = rrect(-670, 670, 612, 1712, 60)
    hatch_in = rrect(-670 + G, 670 - G, 612 + G, 1712 - G, 60 - G)
    grooves.append(prism_yz(hatch - hatch_in, -60, 120))
    # Motorhaube quer
    grooves.append(box(4160, 4178, -770, 770, 950, 1300))
    cuts.append(Manifold.batch_boolean(grooves, mf.OpType.Add) - inner12)

    # Tuergriffe, Tankdeckel, Heckklappengriff
    small = [
        both_sides(box(3360, 3470, 700, 1150, 1075, 1118)),
        box(2290, 2400, 700, 1150, 1075, 1118),
        prism_xz(rrect(1080, 1200, 880, 1000, 15), -1150, -700),
        box(-60, 60, -130, 130, 765, 805),
    ]
    cuts.append(Manifold.batch_boolean(small, mf.OpType.Add) - inner12)

    # Scheinwerfer, Blinker, Kuehlergrill
    head = both_sides(box(L - 300, L + 60, 330, 640, 705, 870))
    cuts.append(head - body_offset(-45))
    cuts.append(both_sides(box(L - 260, L + 60, 650, 820, 705, 870)) - inner12)
    grille = box(L - 300, L + 60, -305, 305, 705, 870)
    cuts.append(grille - body_offset(-30))

    body -= Manifold.batch_boolean(cuts, mf.OpType.Add)

    # ---- Anbauteile ------------------------------------------------------
    # Scheinwerfer-Glaeser (zweigeteilt) und Grillstaebe
    lens = Manifold()
    for y0, y1 in ((345, 470), (488, 628)):
        lens += box(L - 60, L - 24, y0, y1, 720, 855)
    body += both_sides(lens)
    for zs in (722, 765, 808, 851):
        body += box(L - 45, L - 7, -300, 300, zs - 11, zs + 11)

    # Stossfaenger vorne
    def bumper(x0, x1, hw, r_front, r_rear, zb, zt):
        xs = stations(x0, x1, fine=4, coarse=12, zone=min(330, (x1 - x0) / 2 - 1))

        def sec(x):
            w = float(plan_half_width(np.array([x]), x0, x1, hw, r_front, r_rear)[0])
            pts = [(w, zb), (w, zt), (-w, zt), (-w, zb)]
            return fillet_polygon(pts, [45, 40, 40, 45], [6, 6, 6, 6])
        return loft(xs, sec)

    fb = bumper(4215, L + 70, 945, 330, 25, 300, 615)
    fb -= box(L + 45, L + 120, -430, 430, 335, 410)        # Lufteinlass
    fb -= box(4100, L + 120, -1100, 1100, 470, 484) - bumper(4230, L + 56, 932, 316, 20, 310, 605)
    body += fb
    body += box(L + 62, L + 82, -262, 262, 420, 532)        # Kennzeichen vorne

    rb = bumper(-75, 480, 935, 25, 150, 300, 600)
    rb -= box(-200, 600, -1100, 1100, 450, 464) - bumper(-62, 467, 922, 20, 137, 310, 590)
    body += rb
    body += box(-16, 8, -262, 262, 630, 742)               # Kennzeichen hinten

    # Aussenspiegel (Unterseite 45 Grad -> stuetzenfrei druckbar)
    mirror_pts = np.array([
        [3960, 870, 1170], [4070, 870, 1170], [3960, 870, 1440], [4070, 870, 1440],
        [3945, 1065, 1365], [4085, 1065, 1365], [3945, 1070, 1485], [4085, 1070, 1485],
        [3955, 1000, 1505], [4075, 1000, 1505]], float)
    mir = Manifold.hull_points(mirror_pts)
    mir -= box(3900, 3958, 900, 1060, 1390, 1470)   # Spiegelglas (nach hinten)
    body += both_sides(mir)

    # Scheibenwischer (flache Leisten auf der Scheibe)
    for yc in (-330, 330):
        wiper = prism_yz(rrect(yc - 240, yc + 240, 1221, 1247, 6), 3900, 4200) ^ outer10
        body += wiper - inner18

    # ---- Unterboden-Stuetzblock (macht das Modell stuetzenfrei druckbar) --
    xs = np.linspace(-20, L + 20, 400)
    pw = plan_half_width(xs, -20, L + 20, 860, 330, 150)
    outline = np.vstack([np.column_stack([xs, -pw]), np.column_stack([xs[::-1], pw[::-1]])])
    plan = CrossSection([outline])
    block = prism_xy(plan, -100, 330)
    trap = CrossSection([np.array([[-600, -100], [600, -100], [870, 330], [-870, 330]], float)])
    block ^= prism_yz(trap, -100, L + 100)
    for xa in (X_FRONT_AXLE, X_REAR_AXLE):
        block -= both_sides(cyl_y(xa, WHEEL_R, WHEEL_R + 42, 655, 1200))
    if sockel:
        body += block

    # ---- Raeder ----------------------------------------------------------
    w = wheel()
    for xa in (X_FRONT_AXLE, X_REAR_AXLE):
        body += place_wheel(w, xa, +1) + place_wheel(w, xa, -1)
        body += both_sides(cyl_y(xa, WHEEL_R, 70, 560, 730, 48))  # Achsstummel

    # Reifen unten leicht abflachen -> stabile Aufstandsflaechen, Boden bei z=0
    cut = 10.0
    body = body.trim_by_plane([0, 0, 1], cut).translate([0, 0, -cut])
    return body


def save_stl(m, path, name="VW T4"):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float32)
    t = np.asarray(mesh.tri_verts).astype(np.int64)
    p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    n = np.cross(p1 - p0, p2 - p0)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    data = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    data["n"] = n
    data["v"] = np.stack([p0, p1, p2], axis=1)
    with open(path, "wb") as f:
        hdr = name.encode()[:80].ljust(80, b" ")
        f.write(hdr)
        f.write(np.uint32(len(t)).tobytes())
        f.write(data.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=30.0, help="Massstab 1:N")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ohne-sockel", action="store_true",
                    help="ohne Unterboden-Stuetzblock (realistischer, braucht Baum-Stuetzen)")
    a = ap.parse_args()
    model = build(sockel=not a.ohne_sockel)
    s = 1.0 / a.scale
    model = model.scale([s, s, s])
    # Mikro-Kanten entfernen, damit beim float32-Export keine Punkte verschmelzen
    model = model.simplify(0.002)
    # Mittig ausrichten (x,y), Boden bei z=0
    bb = model.bounding_box()
    model = model.translate([-(bb[0] + bb[3]) / 2, -(bb[1] + bb[4]) / 2, -bb[2]])
    bb = model.bounding_box()
    out = a.out or f"vw_t4_1-{int(a.scale)}{'_ohne-sockel' if a.ohne_sockel else ''}.stl"
    save_stl(model, out, f"VW T4 Modell 1:{a.scale:g}")
    print(f"{out}: {model.num_tri()} Dreiecke, "
          f"{bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm, "
          f"Volumen {model.volume()/1000:.1f} cm3, genus {model.genus()}, "
          f"status {model.status()}")
