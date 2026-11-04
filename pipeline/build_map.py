"""Convert dataofjapan/land japan.topojson (source: 地球地図日本 / GSI) into compact SVG paths.

Usage: python3 -I build_map.py TOPOJSON OUT_JSON
Output: {"viewBox": "...", "prefs": [{"id", "name", "d", "cx", "cy"}], "inset": {...}}
Okinawa is drawn in an inset box at the top-left.
"""
import json
import math
import sys

KX = math.cos(math.radians(36))  # equirectangular with latitude correction
SCALE = 46
MIN_RING_AREA = 0.0035  # deg^2; drop tiny islets
TOL = 0.012             # deg; Douglas-Peucker tolerance


def decode_arcs(t):
    sx, sy = t["transform"]["scale"]
    tx, ty = t["transform"]["translate"]
    arcs = []
    for arc in t["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def ring_pts(ring, arcs):
    pts = []
    for i in ring:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(a if not pts else a[1:])
    return pts


def area(p):
    return abs(sum(p[i][0] * p[i - 1][1] - p[i - 1][0] * p[i][1] for i in range(len(p)))) / 2


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    best, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norm
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [pts[0], pts[-1]]
    return dp(pts[:idx + 1], tol)[:-1] + dp(pts[idx:], tol)


def simplify_ring(p):
    if len(p) < 8:
        return p
    half = len(p) // 2
    return dp(p[:half + 1], TOL)[:-1] + dp(p[half:], TOL)


def main():
    t = json.load(open(sys.argv[1], encoding="utf-8"))
    arcs = decode_arcs(t)
    geoms = t["objects"]["japan"]["geometries"]
    rings_by = {}
    for g in geoms:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        rings = []
        for poly in polys:
            outer = ring_pts(poly[0], arcs)
            if area(outer) < MIN_RING_AREA:
                continue
            clon = sum(q[0] for q in outer) / len(outer)
            clat = sum(q[1] for q in outer) / len(outer)
            pid = g["properties"]["id"]
            if pid == 47 and not (126.5 <= clon <= 128.5 and 25.9 <= clat <= 27.2):
                continue  # Okinawa inset: main island group only
            if pid != 47 and clat < 30.6:
                continue  # far southern islets (Amami etc.) would stretch the frame
            if pid == 13 and clat < 34.3:
                continue  # Tokyo's Izu/Ogasawara islands
            rings.append(simplify_ring(outer))
        if not rings:  # keep the largest ring at least
            biggest = max((ring_pts(poly[0], arcs) for poly in polys), key=area)
            rings = [simplify_ring(biggest)]
        rings_by[g["id"] if "id" in g else g["properties"]["id"]] = (g["properties"]["nam_ja"], rings)

    # main projection bounds (exclude Okinawa = 47)
    def proj(lon, lat):
        return lon * KX * SCALE, -lat * SCALE

    main_pts = [proj(*p) for pid, (_, rs) in rings_by.items() if pid != 47 for r in rs for p in r]
    minx = min(p[0] for p in main_pts)
    miny = min(p[1] for p in main_pts)
    maxx = max(p[0] for p in main_pts)
    maxy = max(p[1] for p in main_pts)
    pad = 10
    ox, oy = minx - pad, miny - pad

    # Okinawa inset: place top-left
    oki = [proj(*p) for r in rings_by[47][1] for p in r]
    o_minx, o_miny = min(p[0] for p in oki), min(p[1] for p in oki)
    o_w = max(p[0] for p in oki) - o_minx
    o_h = max(p[1] for p in oki) - o_miny
    inset_scale = min(150 / o_w, 120 / o_h)
    ix, iy = pad + 8, pad + 8

    prefs = []
    for pid, (name, rings) in sorted(rings_by.items()):
        parts, xs, ys = [], [], []
        for r in rings:
            pts = []
            for lon, lat in r:
                x, y = proj(lon, lat)
                if pid == 47:
                    x = ix + (x - o_minx) * inset_scale
                    y = iy + (y - o_miny) * inset_scale
                else:
                    x, y = x - ox, y - oy
                pts.append((round(x, 1), round(y, 1)))
            xs += [p[0] for p in pts]
            ys += [p[1] for p in pts]
            parts.append("M" + "L".join(f"{x:g},{y:g}" for x, y in pts) + "Z")
        # label point: centroid of the largest ring's bbox
        big = max(rings, key=area)
        bx = [proj(*p) for p in big]
        if pid == 47:
            cx = ix + ((min(p[0] for p in bx) + max(p[0] for p in bx)) / 2 - o_minx) * inset_scale
            cy = iy + ((min(p[1] for p in bx) + max(p[1] for p in bx)) / 2 - o_miny) * inset_scale
        else:
            cx = (min(p[0] for p in bx) + max(p[0] for p in bx)) / 2 - ox
            cy = (min(p[1] for p in bx) + max(p[1] for p in bx)) / 2 - oy
        prefs.append({"id": pid, "name": name, "d": "".join(parts), "cx": round(cx, 1), "cy": round(cy, 1)})

    w, h = round(maxx - minx + 2 * pad), round(maxy - miny + 2 * pad)
    out = {"viewBox": f"0 0 {w} {h}", "prefs": prefs,
           "inset": {"x": ix - 6, "y": iy - 6, "w": round(o_w * inset_scale + 12), "h": round(o_h * inset_scale + 12)},
           "source": "地球地図日本（国土地理院）をもとに dataofjapan/land が変換したデータを簡略化"}
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("prefs", len(prefs), "viewBox", out["viewBox"])


if __name__ == "__main__":
    main()
