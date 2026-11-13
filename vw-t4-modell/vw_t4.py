#!/usr/bin/env python3
"""
VW T4 (Typ 70, Kurzschnauze, Baujahr 1990-1995, kurzer Radstand,
Caravelle/Kombi) als druckbares 3D-Modell.

Die Proportionen sind an einer Seiten-, Front- und Heckansicht des T4
Kurzschnauze (1990) abgeglichen. Alle Masse im Skript sind Originalmasse in mm.
Am Ende wird auf den gewaehlten Massstab skaliert.

Koordinaten: x = vom Heck (0) nach vorn (4707), y = nach links
(rechte Fahrzeugseite mit Schiebetuer liegt bei -y), z = Hoehe ueber Fahrbahn.

Ausgabe:
  vw_t4_1-<N>.stl                 einfarbig, ein Koerper
  mehrfarbig_1-<N>/*.stl          Teile je Farbe (in Bambu Studio alle
                                  gleichzeitig importieren -> "als ein Objekt
                                  mit mehreren Teilen laden" -> Farben zuweisen)

Benoetigt: pip install manifold3d numpy
"""
import argparse
import os
import numpy as np
import manifold3d as mf

Manifold, CrossSection, JoinType, OpType = (mf.Manifold, mf.CrossSection,
                                            mf.JoinType, mf.OpType)

# ---------------------------------------------------------------------------
# Hauptmasse (mm)
# ---------------------------------------------------------------------------
LENGTH = 4707.0
Z_FLOOR = 300.0          # Unterkante Karosserie / Schweller
Z_ROOF = 1950.0
X_RA, X_FA = 910.0, 3830.0   # Hinter-/Vorderachse (Radstand 2920)
WHEEL_R = 322.0
TIRE_HALF = 97.0
TRACK_Y = 793.0
ARCH_R = 410.0
Z_CREASE = 870.0         # seitliche Sicke
Z_FACE_TOP = 995.0       # Oberkante Frontmaske
X_FACE = 4688.0          # Frontmaske


def _smooth(points, zq, sigma=8.0):
    pz, pv = np.array(points, float).T
    grid = np.arange(pz[0] - 100, pz[-1] + 100.01, 1.0)
    vals = np.interp(grid, pz, pv)
    if sigma > 0:
        k = np.arange(-4 * sigma, 4 * sigma + 0.01, 1.0)
        ker = np.exp(-0.5 * (k / sigma) ** 2)
        ker /= ker.sum()
        pad = len(k) // 2
        vals = np.convolve(np.concatenate([np.full(pad, vals[0]), vals,
                                           np.full(pad, vals[-1])]), ker, "valid")
    return np.interp(zq, grid, vals)


# Profile als Funktion der Hoehe z ----------------------------------------
# Vorderkante (Frontmaske -> Haube 37 Grad -> Windlauf -> Frontscheibe -> Dach)
XF_PTS = [(300, 4660), (690, 4676), (980, 4688), (1000, 4683), (1040, 4650),
          (1333, 4268), (1342, 4215), (1352, 4152), (1910, 3441), (1932, 3395),
          (1950, 3310)]
# Hinterkante (schraege Heckklappe)
XR_PTS = [(300, 40), (380, 30), (700, 33), (1800, 190), (1880, 226), (1925, 270),
          (1950, 345)]


def _w_pts():
    pts = [(300, 862), (315, 892), (340, 910), (380, 918), (420, 920), (1120, 920),
           (1790, 783)]
    for z in np.linspace(1795, 1950, 32):
        pts.append((z, 620 + np.sqrt(max(163 ** 2 - (z - 1790) ** 2, 0))))
    return pts


W_PTS = _w_pts()
RF_PTS = [(300, 175), (990, 175), (1060, 240), (1340, 430), (1420, 470), (1800, 335),
          (1950, 260)]
RR_PTS = [(300, 130), (1800, 130), (1950, 150)]


def prof_xf(z): return _smooth(XF_PTS, z, 6)
def prof_xr(z): return _smooth(XR_PTS, z, 8)
def prof_w(z): return _smooth(W_PTS, z, 3)
def prof_rf(z): return _smooth(RF_PTS, z, 20)
def prof_rr(z): return _smooth(RR_PTS, z, 20)


def pillar_x(z):
    """Lage der A-Saeule (Ende der umlaufenden Frontscheibe) in Seitenansicht."""
    return prof_xf(z) - prof_rf(z) + 45


# ---------------------------------------------------------------------------
# Geometrie-Helfer
# ---------------------------------------------------------------------------
NS, NF, NR, K = 70, 18, 14, 14


def plan_ring(xr, xf, w, rr, rf):
    """Abgerundetes Rechteck im Grundriss, gegen den Uhrzeigersinn (von oben)."""
    rf = min(rf, w - 1, (xf - xr) / 2 - 1)
    rr = min(rr, w - 1, (xf - xr) / 2 - 1)
    pts = []
    a0 = np.linspace(0, 1, NS + 2)[1:-1]
    for t in a0:                                    # rechte Seite y=-w
        pts.append((xr + rr + t * (xf - rf - xr - rr), -w))
    for a in np.linspace(-np.pi / 2, 0, K):         # vorn rechts
        pts.append((xf - rf + rf * np.cos(a), -w + rf + rf * np.sin(a)))
    for t in np.linspace(0, 1, NF + 2)[1:-1]:       # Front
        pts.append((xf, -w + rf + t * 2 * (w - rf)))
    for a in np.linspace(0, np.pi / 2, K):          # vorn links
        pts.append((xf - rf + rf * np.cos(a), w - rf + rf * np.sin(a)))
    for t in a0:                                    # linke Seite
        pts.append((xf - rf - t * (xf - rf - xr - rr), w))
    for a in np.linspace(np.pi / 2, np.pi, K):      # hinten links
        pts.append((xr + rr + rr * np.cos(a), w - rr + rr * np.sin(a)))
    for t in np.linspace(0, 1, NR + 2)[1:-1]:       # Heck
        pts.append((xr, w - rr - t * 2 * (w - rr)))
    for a in np.linspace(np.pi, 1.5 * np.pi, K):    # hinten rechts
        pts.append((xr + rr + rr * np.cos(a), -w + rr + rr * np.sin(a)))
    return np.array(pts)


def loft_z(zs, ring_fn):
    rings = [ring_fn(z) for z in zs]
    N = len(rings[0])
    verts = np.vstack([np.column_stack([r, np.full(N, z)]) for z, r in zip(zs, rings)])
    j = np.arange(N)
    jn = (j + 1) % N
    tris = []
    for i in range(len(zs) - 1):
        a, b, c, d = i * N + j, i * N + jn, (i + 1) * N + j, (i + 1) * N + jn
        tris += [np.column_stack([a, b, d]), np.column_stack([a, d, c])]
    c0, c1 = len(verts), len(verts) + 1
    verts = np.vstack([verts, [[*rings[0].mean(0), zs[0]]], [[*rings[-1].mean(0), zs[-1]]]])
    tris.append(np.column_stack([np.full(N, c0), jn, j]))
    base = (len(zs) - 1) * N
    tris.append(np.column_stack([np.full(N, c1), base + j, base + jn]))
    mesh = mf.Mesh(vert_properties=verts.astype(np.float32),
                   tri_verts=np.vstack(tris).astype(np.uint32))
    m = Manifold(mesh)
    assert m.status() == mf.Error.NoError, m.status()
    assert m.volume() > 0
    return m


def z_stations(z0, z1, edges=((0, 110, 2.0),), top=160, dz=8.0):
    zs = list(np.arange(z0, z0 + 110, 2.5))
    zs += list(np.arange(z0 + 110, z1 - top, dz))
    zs += list(np.arange(z1 - top, z1, 2.0)) + [z1]
    return np.unique(np.array(zs))


def body_offset(d):
    """Karosserie um d nach aussen (d>0) / innen (d<0) versetzt (Naeherung)."""
    z0, z1 = Z_FLOOR - d, Z_ROOF + d
    zs = z_stations(z0, z1)

    def ring(z):
        zc = float(np.clip(z, Z_FLOOR, Z_ROOF))
        # oben/unten Rundung beibehalten: Profile an der verschobenen Hoehe lesen
        if z > Z_ROOF - 170:
            zc = Z_ROOF - (Z_ROOF + d - z) * (170 / (170 + d)) if d > -150 else zc
        if z < Z_FLOOR + 120:
            zc = Z_FLOOR + (z - (Z_FLOOR - d)) * (120 / (120 + d)) if d > -100 else zc
        zc = float(np.clip(zc, Z_FLOOR, Z_ROOF))
        return plan_ring(float(prof_xr(zc)) - d, float(prof_xf(zc)) + d,
                         float(prof_w(zc)) + d, max(float(prof_rr(zc)) + d, 20),
                         max(float(prof_rf(zc)) + d, 20))
    return loft_z(zs, ring)


def rounded(pts, r, seg=24):
    pts = np.asarray(pts, float)
    x, y = pts[:, 0], pts[:, 1]
    if np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) < 0:   # im Uhrzeigersinn?
        pts = pts[::-1]
    cs = CrossSection([pts])
    if r > 0:
        cs = cs.offset(-r, JoinType.Round, circular_segments=seg).offset(
            r, JoinType.Round, circular_segments=seg)
    return cs


def rrect(a0, a1, b0, b1, r=0.0):
    return rounded([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], r)


def prism_xz(cs, y0, y1):
    """2D (x,z) entlang y extrudieren."""
    return Manifold.extrude(cs, y1 - y0).transform(
        np.array([[1, 0, 0, 0], [0, 0, -1, y1], [0, 1, 0, 0]], float))


def prism_yz(cs, x0, x1):
    """2D (y,z) entlang x extrudieren."""
    return Manifold.extrude(cs, x1 - x0).transform(
        np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], float))


def prism_xy(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def mirror_y(m):
    return m + m.mirror([0, 1, 0])


def cyl_y(xc, zc, r, y0, y1, seg=120):
    return Manifold.cylinder(y1 - y0, r, r, seg).transform(
        np.array([[1, 0, 0, xc], [0, 0, 1, y0], [0, 1, 0, zc]], float))


def seg_poly(p0, p1, width):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    n = np.array([-d[1], d[0]]) * width / 2
    e = d * width / 2
    return CrossSection([np.array([p0 - n - e, p1 - n + e, p1 + n + e, p0 + n - e])])


def groove_xz(points, width, y0, y1):
    return union([prism_xz(seg_poly(points[i], points[i + 1], width), y0, y1)
                  for i in range(len(points) - 1)])


def union(parts):
    parts = [p for p in parts if p is not None and not p.is_empty()]
    if not parts:
        return Manifold()
    return Manifold.batch_boolean(parts, OpType.Add)


def hull(pts):
    return Manifold.hull_points(np.asarray(pts, float))


# ---------------------------------------------------------------------------
# Anbauteile
# ---------------------------------------------------------------------------

def bumper_loft(x0, x1, hw, r_front, r_rear, z0, z1, r_edge=45):
    """Stossfaenger aus horizontalen Schnitten mit gerundeten Kanten."""
    zs = np.unique(np.concatenate([np.linspace(z0, z0 + r_edge, 10),
                                   np.linspace(z0 + r_edge, z1 - r_edge, 6),
                                   np.linspace(z1 - r_edge, z1, 10)]))

    def ring(z):
        dz = max(z0 + r_edge - z, z - (z1 - r_edge), 0)
        inset = r_edge - np.sqrt(max(r_edge ** 2 - dz ** 2, 0))
        return plan_ring(x0 + inset, x1 - inset, hw - inset,
                         max(r_rear - inset, 15), max(r_front - inset, 15))
    return loft_z(zs, ring)


def wheel_parts():
    """Reifen und Stahlfelge mit Radkappe, Achse = z, aussen = +z."""
    seg = 128
    tire = Manifold.revolve(rrect(208, WHEEL_R, -TIRE_HALF, TIRE_HALF, 38), seg)
    for h in (-55, -18, 18, 55):
        tire -= Manifold.revolve(rrect(WHEEL_R - 8, WHEEL_R + 30, h - 6, h + 6), seg)
    # Querrillen im Profil (Schulter)
    for i in range(48):
        a = 360.0 * i / 48
        g = box(WHEEL_R - 9, WHEEL_R + 30, -8, 8, 60, TIRE_HALF + 10).rotate([0, 0, a])
        tire -= g + g.mirror([0, 0, 1])
    tire -= Manifold.revolve(rrect(208, 222, TIRE_HALF - 14, TIRE_HALF + 5), seg)

    prof = [(0, -90), (212, -90), (212, 60), (200, 66), (186, 56), (150, 50),
            (150, 54), (0, 54)]
    rim = Manifold.revolve(CrossSection([np.array(prof, float)]), seg)
    # Radkappe (fruehe T4-Kunststoffkappe: flache Schuessel mit Rippen)
    cap_prof = [(0, 50), (176, 50), (176, 58), (165, 68), (120, 76), (60, 80), (0, 81)]
    cap = Manifold.revolve(CrossSection([np.array(cap_prof, float)]), seg)
    for i in range(10):
        a = 360.0 * i / 10
        cap -= box(95, 160, -8, 8, 70, 90).rotate([0, 0, a])
    cap -= Manifold.revolve(rrect(0, 38, 77, 95), 64)
    return tire, rim + cap


def place_wheel(m, x, side):
    R = (np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float) if side > 0 else
         np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float))
    return m.transform(np.column_stack([R, [x, side * TRACK_Y, WHEEL_R]]))


# ---------------------------------------------------------------------------
# Modell
# ---------------------------------------------------------------------------

def build(sockel=False):
    P = {}  # Farbteile
    body = body_offset(0)
    in6, in12, in18, in30 = (body_offset(-6), body_offset(-12), body_offset(-18),
                             body_offset(-30))
    out8, out12 = body_offset(8), body_offset(12)
    side_r = (-1200, -560)   # y-Bereich rechte Seite
    side_l = (560, 1200)

    # ---------------- erhabene Karosseriedetails ------------------------
    # Regenrinnen am Dachrand
    gutter = box(380, 3210, -1000, 1000, 1856, 1874) ^ out8
    # Radlauf-Lippen
    lips = []
    for xa in (X_RA, X_FA):
        ring = cyl_y(xa, WHEEL_R, ARCH_R + 45, 820, 1100, 137) - cyl_y(xa, WHEEL_R, ARCH_R - 5, 810, 1110, 131)
        lips.append(mirror_y(ring))
    lips = union(lips) ^ out8 ^ box(517, 4247, -1200, 1200, Z_FLOOR + 5, 2000)
    body = union([body, gutter, lips])

    # ---------------- Vertiefungen (Fenster, Fugen, Front) --------------
    glass_cut = []
    # Frontscheibe (umlaufend bis zur A-Saeule)
    zz = np.linspace(1360, 1888, 40)
    ws_poly = [(float(pillar_x(z)), float(z)) for z in zz] + [(6000, 1888), (6000, 1360)]
    glass_cut.append(prism_xz(rounded(ws_poly, 45), -1100, 1100))
    # Seitenfenster
    win = [
        rounded([(345, 1300), (1300, 1300), (1300, 1805), (425, 1805)], 70),   # hinten
        rrect(1470, 2625, 1300, 1810, 60),                                     # Mitte
        rounded([(2765, 1282), (3590, 1282), (3205, 1810), (2765, 1810)], 55),  # Tuer
    ]
    sidewin = union([prism_xz(c, 500, 1200) for c in win])
    glass_cut.append(mirror_y(sidewin))
    # Heckscheibe
    glass_cut.append(prism_yz(rrect(-645, 645, 1345, 1885, 95), -200, 700))
    glass_region = union(glass_cut)
    glass_recess = glass_region - in18
    glass_part = glass_region ^ (in6 - in18)

    G = 16
    grooves = []
    for sgn in (-1, 1):
        y0, y1 = (side_r if sgn < 0 else side_l)
        # Vordertuer
        grooves.append(groove_xz([(2722, 300), (2722, 1846), (3190, 1846)], G, y0, y1))
        grooves.append(groove_xz([(3236, 1846), (3640, 1290), (3655, 700)], G, y0, y1))
        # seitliche Sicke
        grooves.append(prism_xz(rrect(-100, 4800, Z_CREASE - 7, Z_CREASE + 7), y0, y1))
    # Schiebetuer rechts
    grooves.append(groove_xz([(1425, 300), (1425, 1846), (2685, 1846), (2685, 300)],
                             G, *side_r))
    # Heckklappe
    hatch = rrect(-652, 652, 497, 1928, 90)
    grooves.append(prism_yz(hatch - rrect(-636, 636, 513, 1912, 74), -200, 700))
    # Haube / Windlauf
    grooves.append(box(4252, 4268, -820, 820, 1250, 1400))
    groove_cut = union(grooves) - in12

    # Front: Grill oben/unten, Scheinwerfer, Blinker
    x_in = X_FACE - 600
    grille_up = box(x_in, 5000, -470, 470, 852, 988)
    grille_lo = box(x_in, 5000, -470, 470, 698, 798)
    heads = mirror_y(box(x_in, 5000, 482, 712, 852, 988))
    indic = mirror_y(box(4300, 5000, 722, 1100, 852, 988))
    front_cut = (grille_up + grille_lo) - in30 + (heads - in30) + (indic - in18)

    # Griffe, Heckgriff, Kennzeichenmulde hinten
    small = union([
        mirror_y(box(2740, 2850, 560, 1100, 1120, 1165)),       # Vordertuergriffe
        box(2560, 2670, -1100, -560, 1120, 1165),               # Schiebetuergriff
        box(-200, 400, -110, 110, 860, 895),                    # Heckklappengriff
        prism_yz(rrect(-300, 300, 715, 840, 15), -200, 400),    # Kennzeichenmulde
    ]) - in12

    body = body - union([glass_recess, groove_cut, front_cut, small])

    # ---------------- Einsaetze / Reliefs in den Vertiefungen -----------
    P["glas"] = glass_part
    # Kuehlergrill: Lamellen
    slats = union([box(X_FACE - 40, X_FACE - 8, -465, 465, zc - 10, zc + 10)
                   for zc in (885, 920, 955, 730, 765)])
    grille_fill = (grille_up + grille_lo) ^ (in18 - in30)
    P["schwarz_grill"] = union([grille_fill, slats ^ (body_offset(-8) - in30)])
    # Scheinwerfer (zweigeteilt) und Blinker
    lens = mirror_y(union([box(X_FACE - 40, X_FACE - 12, 492, 590, 862, 978),
                           box(X_FACE - 40, X_FACE - 12, 600, 702, 862, 978)]))
    P["scheinwerfer"] = lens
    P["orange"] = indic ^ (in6 - in18)

    # ---------------- Stossfaenger, Leuchten, Spiegel, Leisten ----------
    fb = bumper_loft(4282, 4742, 936, 265, 25, Z_FLOOR, 688)
    fb -= box(4000, 5000, -1200, 1200, 598, 610) - bumper_loft(4295, 4729, 923, 252, 20,
                                                              Z_FLOOR + 10, 678)
    fb -= box(4000, 5000, -1200, 1200, 350, 360) - bumper_loft(4295, 4729, 923, 252, 20,
                                                              Z_FLOOR + 10, 678)
    fb += box(4730, 4752, -262, 262, 420, 532)                 # Kennzeichenplatte
    rb = bumper_loft(-28, 470, 936, 25, 210, Z_FLOOR, 688)
    rb -= box(-200, 330, -650, 650, 495, 900)                  # Ladekante tiefer
    rb -= box(-200, 600, -1200, 1200, 598, 610) - bumper_loft(-15, 457, 923, 20, 197,
                                                             Z_FLOOR + 10, 678)
    # Kennzeichen hinten
    plate_r = box(-20, 200, -258, 258, 722, 833) - in12 ^ body_offset(-4)
    # Heckleuchten (erhaben, um die Ecke gezogen): oben rot, unten orange
    lamp = mirror_y(box(-80, 175, 652, 1000, 700, 872)) ^ out12
    lamp_r = lamp ^ box(-200, 400, -1200, 1200, 790, 900)
    lamp_o = lamp ^ box(-200, 400, -1200, 1200, 600, 782)
    # Schiebetuerschiene (Abdeckung) rechts
    rail = box(275, 1430, -1200, -560, 1032, 1078) ^ body_offset(14)
    # Aussenspiegel (Unterseite 45 Grad)
    arm = hull([[3500, 860, 1340], [3585, 860, 1340], [3500, 860, 1420], [3585, 860, 1420],
                [3505, 950, 1400], [3580, 950, 1400], [3505, 950, 1450], [3580, 950, 1450]])
    housing = hull([[3478, 930, 1370], [3602, 930, 1370], [3478, 1085, 1470], [3602, 1085, 1470],
                    [3478, 930, 1545], [3602, 930, 1545], [3478, 1090, 1545], [3602, 1090, 1545]])
    mirr = (arm + housing) - box(3440, 3486, 950, 1072, 1475, 1532)
    mirr = mirror_y(mirr)
    # Scheibenwischer (in Ruhestellung unten auf der Scheibe)
    wip = union([prism_yz(seg_poly((y0, 1392), (y0 + sg * 560, 1428), 24), 3900, 4300)
                 for y0, sg in ((-700, 1), (-60, 1))])
    wip = (wip ^ body_offset(9)) - body_offset(-26)
    # Windlauf-Gitter (schwarz)
    cowl = box(4148, 4250, -780, 780, 1300, 1400) ^ body_offset(5)
    cowl -= union([box(4150, 4240, y - 8, y + 8, 1300, 1400) for y in range(-700, 701, 70)]) - body

    P["schwarz"] = union([fb, rb, rail, mirr, wip, cowl])
    P["rot"] = lamp_r
    P["orange_heck"] = lamp_o
    P["silber"] = plate_r + box(4742, 4752, -250, 250, 430, 522)

    # ---------------- Radlaeufe ausschneiden ------------------------------
    arch = union([mirror_y(cyl_y(xa, WHEEL_R, ARCH_R, 640, 1200)) for xa in (X_RA, X_FA)])
    body -= arch
    P["schwarz"] -= arch
    # Radhaus-Auskleidung (schwarz) als duenne Schale im Radlauf
    liner = union([mirror_y(cyl_y(xa, WHEEL_R, ARCH_R + 14, 626, 1200, 149)) for xa in (X_RA, X_FA)])
    P["radhaus"] = body ^ liner ^ box(-500, 5500, -1300, 1300, Z_FLOOR + 110, 2500)

    # ---------------- Raeder + Achsstummel --------------------------------
    tire, rim = wheel_parts()
    tires, rims = [], []
    for xa in (X_RA, X_FA):
        for s in (-1, 1):
            tires.append(place_wheel(tire, xa, s))
            rims.append(place_wheel(rim, xa, s))
    stubs = union([mirror_y(cyl_y(xa, WHEEL_R, 75, 520, 712, 48)) for xa in (X_RA, X_FA)])
    P["reifen"] = union(tires)
    P["silber"] = union([P["silber"], union(rims)])
    body = body + stubs

    if sockel:
        xs = np.linspace(-20, LENGTH + 30, 300)
        outline = np.vstack([np.column_stack([xs, -np.full_like(xs, 860)]),
                             np.column_stack([xs[::-1], np.full_like(xs, 860)])])
        blk = prism_xy(rounded(outline, 200), -100, Z_FLOOR + 30)
        trap = CrossSection([np.array([[-600, -100], [600, -100], [880, Z_FLOOR + 30],
                                       [-880, Z_FLOOR + 30]], float)])
        blk ^= prism_yz(trap, -100, LENGTH + 100)
        blk -= union([mirror_y(cyl_y(xa, WHEEL_R, WHEEL_R + 42, 650, 1200))
                      for xa in (X_RA, X_FA)])
        body = body + blk

    P["karosserie"] = body
    return P


ORDER = ["glas", "orange", "rot", "scheinwerfer", "silber", "schwarz", "karosserie"]
COLORS = {"karosserie": "weiss / Wagenfarbe", "glas": "schwarz oder dunkelgrau",
          "schwarz": "schwarz", "schwarz_grill": "schwarz", "radhaus": "schwarz", "reifen": "schwarz",
          "silber": "silber/grau", "scheinwerfer": "weiss/transparent",
          "orange": "orange", "rot": "rot"}


def finalize(P, scale, cut=8.0):
    """Unten abflachen, skalieren, ausrichten; Teile disjunkt machen."""
    s = 1.0 / scale
    plane = box(-1000, 6000, -2000, 2000, cut, 3000)
    out = {k: (v ^ plane).translate([0, 0, -cut]).scale([s, s, s]) for k, v in P.items()}
    total = union(list(out.values()))
    # Einfarbig: Glas und Front-Blinker bleiben vertieft (keine Einsaetze)
    single = union([out[k] for k in out if k not in ("glas", "orange")])
    bb = total.bounding_box()
    shift = [-(bb[0] + bb[3]) / 2, -(bb[1] + bb[4]) / 2, 0]
    single = single.translate(shift)
    parts, taken = {}, Manifold()
    merged = dict(out)
    merged["orange"] = union([out["orange"], out["orange_heck"]])
    merged["schwarz"] = union([out["schwarz"], out["schwarz_grill"], out["radhaus"],
                               out["reifen"]])
    for k in ("orange_heck", "schwarz_grill", "radhaus", "reifen"):
        del merged[k]
    for k in ORDER:
        raw = merged[k].translate(shift) - taken
        taken = taken + raw
        m = raw
        if not m.is_empty():
            parts[k] = m
    return single, parts


def components(m):
    """Zusammenhaengende Teile eines Netzes: Liste (Volumen, Dreiecksindizes)."""
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64)
    t = np.asarray(mesh.tri_verts).astype(np.int64)
    parent = np.arange(len(v))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    # Kanten ueber Union-Find (vektorisiert wiederholt)
    e = np.vstack([t[:, [0, 1]], t[:, [1, 2]]])
    for _ in range(64):
        ra, rb = parent[e[:, 0]], parent[e[:, 1]]
        lo = np.minimum(ra, rb)
        changed = (ra != rb)
        if not changed.any():
            break
        np.minimum.at(parent, ra, lo)
        np.minimum.at(parent, rb, lo)
        parent = parent[parent]
    lab = parent[t[:, 0]]
    p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    vol = np.einsum("ij,ij->i", p0, np.cross(p1, p2)) / 6
    out = []
    for l in np.unique(lab):
        idx = np.nonzero(lab == l)[0]
        out.append((vol[idx].sum(), idx))
    return v, t, out


def clean(m, min_vol=1e-3):
    """Entfernt Splitter ohne Volumen (entstehen beim Vereinfachen)."""
    if m.is_empty():
        return m
    v, t, comps = components(m)
    keep = [idx for vol, idx in comps if abs(vol) > min_vol]
    if len(keep) == len(comps):
        return m
    tt = t[np.concatenate(keep)] if keep else t[:0]
    mm = Manifold(mf.Mesh(vert_properties=v.astype(np.float32), tri_verts=tt.astype(np.uint32)))
    return mm


def stl_check(v, t):
    """Prueft das Netz so, wie es im STL steht (float32-Positionen)."""
    u, inv = np.unique(v.reshape(-1, 3), axis=0, return_inverse=True)
    tt = inv.reshape(-1, 3)
    deg = (tt[:, 0] == tt[:, 1]) | (tt[:, 1] == tt[:, 2]) | (tt[:, 0] == tt[:, 2])
    e = np.sort(np.vstack([tt[:, [0, 1]], tt[:, [1, 2]], tt[:, [2, 0]]]), 1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    return int(deg.sum()), int((cnt != 2).sum())


def weld_repair(tri):
    """Verschweisst float32-Punkte, entfernt entartete und doppelte Gegenflaechen."""
    u, inv = np.unique(tri.reshape(-1, 3), axis=0, return_inverse=True)
    t = inv.reshape(-1, 3)
    t = t[(t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])]
    key = np.sort(t, axis=1)
    _, first, cnt = np.unique(key, axis=0, return_index=True, return_counts=True)
    keep = np.zeros(len(t), bool)
    keep[first[cnt == 1]] = True          # Paare identischer Flaechen heben sich auf
    t = t[keep]
    return u[t]


def mesh_tris(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float32)
    t = np.asarray(mesh.tri_verts).astype(np.int64)
    return np.stack([v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]], axis=1)


def save_stl(m, path, name="VW T4"):
    """Speichert binaer; waehlt die kleinste Vereinfachung, die ein sauberes
    (geschlossenes, mannigfaltiges) float32-Netz ergibt."""
    best = None
    for tol in (0.0, 0.002, 0.005, 0.01, 0.02, 0.04):
        mm = clean(m.simplify(tol)) if tol else clean(m)
        tri = weld_repair(mesh_tris(mm))
        deg, bad = stl_check(tri, None)
        if best is None or deg + bad < best[0]:
            best = (deg + bad, tri, tol)
        if deg + bad == 0:
            break
    nbad, tri, tol = best
    if nbad:
        print(f"  WARNUNG {path}: {nbad} Netzfehler")
    p0, p1, p2 = tri[:, 0], tri[:, 1], tri[:, 2]
    n = np.cross(p1 - p0, p2 - p0)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    data = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    data["n"], data["v"] = n, tri
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b" "))
        f.write(np.uint32(len(tri)).tobytes())
        f.write(data.tobytes())
    return len(tri), tri


def describe(m):
    bb = m.bounding_box()
    return (f"{bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm, "
            f"{m.num_tri()} Dreiecke, Koerper: {len(components(m)[2])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=30.0, help="Massstab 1:N")
    ap.add_argument("--sockel", action="store_true",
                    help="Unterboden-Sockel: stuetzenfrei druckbar, weniger realistisch")
    ap.add_argument("--keine-teile", action="store_true", help="keine Mehrfarben-Teile")
    a = ap.parse_args()
    P = build(sockel=a.sockel)
    single, parts = finalize(P, a.scale)
    tag = f"1-{a.scale:g}" + ("_sockel" if a.sockel else "")
    n, tri = save_stl(single, f"vw_t4_{tag}.stl", f"VW T4 1:{a.scale:g}")
    ext = tri.reshape(-1, 3).max(0) - tri.reshape(-1, 3).min(0)
    print(f"vw_t4_{tag}.stl: {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm, {n} Dreiecke")
    if not a.keine_teile:
        d = f"mehrfarbig_{tag}"
        os.makedirs(d, exist_ok=True)
        for k, m in parts.items():
            n, _ = save_stl(m, os.path.join(d, f"{k}.stl"), k)
            print(f"  {d}/{k}.stl ({COLORS[k]}): {n} Dreiecke")
