#!/usr/bin/env python3
"""Derive the black route-line set of the approved reference graphic.

Sources
  * visuals/reference/last_mile_reference.png — Canva export of the approved
    graphic (1280 x 800 slide pixels).
  * visuals/reference/drayage_kg_final2-fixed-editable-google-route-match.pptx
    (the editable source of that graphic) — its straight roundRect segments,
    node dots, arrows and amber wash rectangles match the export pixel for
    pixel, so they are taken as exact coordinates.
  * curves that were redrawn in Canva (Exit 13A loop, south branch, "from
    north" branch, inset ramp) do not exist in the pptx; they are traced from
    the PNG: dark mask -> skeleton -> greedy centerline walk -> smoothing.
Output: visuals/last_mile_reference_lines.json (slide px, y down).
"""
import json, math, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np, cv2

ROOT = Path(__file__).resolve().parent.parent
REF_PNG = ROOT / "visuals/reference/last_mile_reference.png"
OUT = ROOT / "visuals/last_mile_reference_lines.json"
CHECK = ROOT / "visuals/reference/trace_check.png"
PPTX = ROOT / "visuals/reference/drayage_kg_final2-fixed-editable-google-route-match.pptx"
NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
SLIDE_W, SLIDE_H = 1280, 800
BLACK_GROUPS = ("approach-west", "approach-north", "shared-corridor", "gate-link")
# bold labels in the export that survive the size filter; excluded from tracing
TEXT_BOXES = [(585, 332, 705, 352), (420, 125, 615, 152), (950, 268, 995, 285),
              (1000, 303, 1110, 320), (870, 466, 1000, 484), (570, 155, 650, 182),
              (455, 244, 535, 270), (595, 352, 700, 366)]
EXTRA_DOTS = [dict(x=709.5, y=331, d=12), dict(x=534, y=431, d=12), dict(x=499, y=551, d=12)]
RINGS = [dict(x=61, y=294, d=24), dict(x=201.5, y=58, d=13)]


def pptx_shapes():
    z = zipfile.ZipFile(PPTX)
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    scale = SLIDE_W / int(pres.find("p:sldSz", NS).attrib["cx"])
    root = ET.fromstring(z.read("ppt/slides/slide1.xml"))
    shapes = []
    for sp in root.iter("{%s}sp" % NS["p"]):
        name = sp.find("p:nvSpPr/p:cNvPr", NS).attrib.get("name", "")
        xfrm = sp.find("p:spPr/a:xfrm", NS)
        if xfrm is None:
            continue
        off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
        x, y, w, h = [int(v) * scale for v in (off.attrib["x"], off.attrib["y"], ext.attrib["cx"], ext.attrib["cy"])]
        rot = int(xfrm.attrib.get("rot", 0)) / 60000
        geom = sp.find("p:spPr/a:prstGeom", NS)
        fill = sp.find("p:spPr/a:solidFill/a:srgbClr", NS)
        txt = "".join(t.text or "" for t in sp.iter("{%s}t" % NS["a"]))
        shapes.append(dict(name=name, g=geom.attrib.get("prst") if geom is not None else None,
                           x=x, y=y, w=w, h=h, rot=rot, fill=fill.attrib["val"] if fill is not None else None, txt=txt))
    return shapes


def seg(s):
    cx, cy, r = s["x"] + s["w"] / 2, s["y"] + s["h"] / 2, math.radians(s["rot"])
    dx, dy = s["w"] / 2 * math.cos(r), s["w"] / 2 * math.sin(r)
    return dict(name=s["name"], x0=round(cx - dx, 2), y0=round(cy - dy, 2), x1=round(cx + dx, 2), y1=round(cy + dy, 2), width=round(s["h"], 1))


def thin(mask):                      # Zhang-Suen
    im = (mask > 0).astype(np.uint8); changed = True
    while changed:
        changed = False
        for step in (0, 1):
            P = np.pad(im, 1)
            p2, p3, p4, p5 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:], P[2:, 2:]
            p6, p7, p8, p9 = P[2:, 1:-1], P[2:, :-2], P[1:-1, :-2], P[:-2, :-2]
            nb = [p2, p3, p4, p5, p6, p7, p8, p9]; B = sum(nb)
            A = sum(((nb[i] == 0) & (nb[(i + 1) % 8] == 1)).astype(np.uint8) for i in range(8))
            c1 = p2 * p4 * p6 if step == 0 else p2 * p4 * p8
            c2 = p4 * p6 * p8 if step == 0 else p2 * p6 * p8
            m = (im == 1) & (B >= 2) & (B <= 6) & (A == 1) & (c1 == 0) & (c2 == 0)
            if m.any():
                im[m] = 0; changed = True
    return im


def walk_paths(skel):
    ys, xs = np.nonzero(skel); remaining = set(zip(xs.tolist(), ys.tolist())); paths = []
    def nb(p, r):
        return [(p[0] + dx, p[1] + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                if (dx or dy) and (p[0] + dx, p[1] + dy) in remaining]
    while remaining:
        ends = [p for p in remaining if len(nb(p, 1)) <= 1]
        start = ends[0] if ends else next(iter(remaining))
        path, cur, pdir = [start], start, None; remaining.remove(start)
        while True:
            c = nb(cur, 1) or nb(cur, 2) or nb(cur, 3)
            if not c:
                break
            def score(q):
                d = math.hypot(q[0] - cur[0], q[1] - cur[1])
                if pdir is None:
                    return d
                return d - 0.5 * ((q[0] - cur[0]) / d * pdir[0] + (q[1] - cur[1]) / d * pdir[1])
            q = min(c, key=score); d = math.hypot(q[0] - cur[0], q[1] - cur[1])
            pdir = ((q[0] - cur[0]) / d, (q[1] - cur[1]) / d)
            path.append(q); remaining.remove(q); cur = q
        paths.append(path)
    return paths


def smooth(path, k=5):
    P = np.array(path, dtype=float)
    if len(P) < k:
        return P
    pad = np.pad(P, ((k // 2, k // 2), (0, 0)), mode="edge")
    ker = np.ones(k) / k
    return np.stack([np.convolve(pad[:, 0], ker, "valid"), np.convolve(pad[:, 1], ker, "valid")], 1)


def main():
    shapes = pptx_shapes()
    segments = [seg(s) for s in shapes if s["fill"] == "0B0B0B" and s["g"] == "roundRect" and s["name"].startswith(BLACK_GROUPS)]
    wash = [seg(s) for s in shapes if s["fill"] == "FFF1CB" and s["g"] == "roundRect"]
    arrows = [dict(cx=s["x"] + s["w"] / 2, cy=s["y"] + s["h"] / 2, w=s["w"], h=s["h"], rot=s["rot"])
              for s in shapes if s["g"] == "triangle" and s["fill"] == "0B0B0B"
              and s["name"] != "south-direction"]      # its line was removed in the export
    dots = [dict(x=round(s["x"] + s["w"] / 2, 1), y=round(s["y"] + s["h"] / 2, 1), d=round(s["w"], 1))
            for s in shapes if s["g"] == "ellipse" and s["fill"] == "0B0B0B" and s["w"] >= 8 and s["y"] < 560
            and s["name"] not in ("node", "") and not s["name"].startswith("truck")] + EXTRA_DOTS

    img = cv2.imread(str(REF_PNG)); b, g, r = cv2.split(img)
    dark = ((r < 110) & (g < 110) & (b < 110)).astype(np.uint8) * 255
    dark[560:, :] = 0; dark[440:615, 25:300] = 0; dark[55:250, 1040:1280] = 0; dark[:50, :] = 0
    for x0, y0, x1, y1 in TEXT_BOXES:
        dark[y0:y1, x0:x1] = 0
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    closed = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, k3)
    n, lab, st, _ = cv2.connectedComponentsWithStats(closed, 8)
    keep = np.zeros_like(closed)
    for i in range(1, n):
        if st[i][4] >= 120 or max(st[i][2], st[i][3]) >= 40:
            keep[lab == i] = 255
    cover = np.zeros_like(keep)
    for s in segments:
        cv2.line(cover, (round(s["x0"]), round(s["y0"])), (round(s["x1"]), round(s["y1"])), 255, int(s["width"]) + 4)
    for d in dots[:-len(EXTRA_DOTS)]:
        cv2.circle(cover, (round(d["x"]), round(d["y"])), int(d["d"] / 2) + 2, 255, -1)
    resid = cv2.bitwise_and(keep, cv2.bitwise_not(cover))
    n, lab, st, _ = cv2.connectedComponentsWithStats(resid, 8)
    resid2 = np.zeros_like(resid)
    for i in range(1, n):
        if st[i][4] >= 60:
            resid2[lab == i] = 255
    dt = cv2.distanceTransform(keep, cv2.DIST_L2, 5)
    curves = []
    for path in walk_paths(thin(resid2)):
        if len(path) < 12:
            continue
        sm = smooth(path)
        simp = cv2.approxPolyDP(sm.astype(np.float32).reshape(-1, 1, 2), 0.8, False).reshape(-1, 2)
        width = float(np.median([2 * dt[y, x] for x, y in path]))
        curves.append(dict(pts=[[round(float(x), 1), round(float(y), 1)] for x, y in simp], width=round(width, 1), n=len(path)))
    # drop short pieces that duplicate a neighbouring curve
    def near(p, poly):
        P = np.array(poly); return float(np.min(np.hypot(P[:, 0] - p[0], P[:, 1] - p[1])))
    curves = [c for i, c in enumerate(curves)
              if not (c["n"] < 25 and any(j != i and near(c["pts"][len(c["pts"]) // 2], o["pts"]) < 8 for j, o in enumerate(curves)))]
    # bridge gaps left by the cover: end-to-end, else end-to-dot along the tangent
    big = [d for d in dots if d["d"] >= 12]
    ends = [(i, e, c["pts"][0 if e == 0 else -1]) for i, c in enumerate(curves) for e in (0, 1)]
    def tangent(c, at_start):
        P = np.array(c["pts"]); v = (P[0] - P[min(4, len(P) - 1)]) if at_start else (P[-1] - P[max(0, len(P) - 5)])
        return v / (np.linalg.norm(v) or 1)
    used, bridges = set(), []
    for i, e, p in ends:
        if (i, e) in used:
            continue
        cand = [(math.hypot(p[0] - q[0], p[1] - q[1]), j, f, q) for j, f, q in ends if j != i and (j, f) not in used]
        cand = [c for c in cand if c[0] <= 36]
        if cand:
            d, j, f, q = min(cand); used |= {(i, e), (j, f)}
            bridges.append(dict(pts=[p, q], width=round((curves[i]["width"] + curves[j]["width"]) / 2, 1), kind="bridge"))
            continue
        for dd in big:
            d = math.hypot(p[0] - dd["x"], p[1] - dd["y"])
            if 8 < d <= 48:
                t = tangent(curves[i], e == 0); ctrl = (p[0] + t[0] * d / 2, p[1] + t[1] * d / 2)
                pts = [[round(float((1 - u) ** 2 * p[0] + 2 * (1 - u) * u * ctrl[0] + u * u * dd["x"]), 1),
                        round(float((1 - u) ** 2 * p[1] + 2 * (1 - u) * u * ctrl[1] + u * u * dd["y"]), 1)] for u in np.linspace(0, 1, 12)]
                bridges.append(dict(pts=pts, width=curves[i]["width"], kind="bridge")); used.add((i, e)); break
    rx, ry, nx, ny = RINGS[0]["x"], RINGS[0]["y"], 78, 235
    v = np.array([nx - rx, ny - ry]); v = v / np.linalg.norm(v) * RINGS[0]["d"] / 2
    spokes = [dict(x0=round(float(rx + v[0]), 1), y0=round(float(ry + v[1]), 1), x1=nx, y1=ny)]
    out = dict(slide=[SLIDE_W, SLIDE_H], source=__doc__.strip(), segments=segments,
               curves=[dict(pts=c["pts"], width=c["width"]) for c in curves] + bridges,
               wash=wash, arrows=arrows, dots=dots, rings=RINGS, spokes=spokes)
    OUT.write_text(json.dumps(out, indent=1))
    blank = np.full_like(img, 255)
    for w in wash:
        cv2.line(blank, (round(w["x0"]), round(w["y0"])), (round(w["x1"]), round(w["y1"])), (203, 241, 255), int(w["width"]), lineType=cv2.LINE_AA)
    for c in out["curves"]:
        cv2.polylines(blank, [np.array(c["pts"], dtype=np.int32).reshape(-1, 1, 2)], False, (0, 0, 0), max(1, round(c["width"])), lineType=cv2.LINE_AA)
    for s in segments:
        cv2.line(blank, (round(s["x0"]), round(s["y0"])), (round(s["x1"]), round(s["y1"])), (0, 0, 0), int(s["width"]), lineType=cv2.LINE_AA)
    for d in dots:
        cv2.circle(blank, (round(d["x"]), round(d["y"])), int(d["d"] / 2), (0, 0, 0), -1, lineType=cv2.LINE_AA)
    for rg in RINGS:
        cv2.circle(blank, (round(rg["x"]), round(rg["y"])), int(rg["d"] / 2), (0, 0, 0), 2, lineType=cv2.LINE_AA)
    cv2.imwrite(str(CHECK), np.hstack([img, blank]))
    print(f"segments={len(segments)} curves={len(curves)} bridges={len(bridges)} wash={len(wash)} dots={len(dots)}")
    for c in curves:
        print("  curve n=%d w=%.1f %s -> %s" % (c["n"], c["width"], c["pts"][0], c["pts"][-1]))
    for b in bridges:
        print("  bridge %s -> %s" % (b["pts"][0], b["pts"][-1]))


if __name__ == "__main__":
    main()
