#!/usr/bin/env python3
"""Score how closely the rendered map's black lines match the reference.

Maps the map-axes region of visuals/last_mile_regulation_map.png back to
slide pixels (1280 x 800), extracts thick dark strokes from both images, and
reports IoU plus mean nearest-distance. Writes visuals/reference/line_check.png:
reference | render | overlay (reference red, render blue, agreement black).
"""
import sys
from pathlib import Path
import numpy as np, cv2

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "visuals/reference/last_mile_reference.png"
RENDER = ROOT / "visuals/last_mile_regulation_map.png"
OUT = ROOT / "visuals/reference/line_check.png"
FIG_W, FIG_H, DPI = 17, 11, 200
AX = (0.02, 0.30, 0.96, 0.96 * FIG_W / FIG_H * 520 / 1280)   # must match make_last_mile_figure.py
MAP_Y0, MAP_Y1 = 40, 560


def strokes(img, exclude_text=True):
    b, g, r = cv2.split(img)
    dark = ((r < 110) & (g < 110) & (b < 110)).astype(np.uint8) * 255
    dark[MAP_Y1:, :] = 0; dark[:50, :] = 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    m = cv2.morphologyEx(cv2.morphologyEx(dark, cv2.MORPH_CLOSE, k), cv2.MORPH_OPEN, k)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i][4] >= 120 or max(st[i][2], st[i][3]) >= 40:
            keep[lab == i] = 255
    return keep


def main():
    ref = cv2.imread(str(REF)); rend = cv2.imread(str(RENDER))
    H, W = rend.shape[:2]
    x0, y1 = int(AX[0] * W), int((1 - AX[1]) * H)
    x1, y0 = int((AX[0] + AX[2]) * W), int((1 - AX[1] - AX[3]) * H)
    crop = cv2.resize(rend[y0:y1, x0:x1], (1280, MAP_Y1 - MAP_Y0), interpolation=cv2.INTER_AREA)
    canvas = np.full_like(ref, 255); canvas[MAP_Y0:MAP_Y1, :] = crop
    a, b = strokes(ref), strokes(canvas)
    b[330:, 1030:] = 0                      # figure legend swatches (no roads there)
    a[440:, 25:300] = 0; b[440:, 25:300] = 0   # truck icon / truck rules box
    inter, union = np.logical_and(a > 0, b > 0).sum(), np.logical_or(a > 0, b > 0).sum()
    iou = inter / union if union else 0
    da = cv2.distanceTransform(255 - a, cv2.DIST_L2, 5); db = cv2.distanceTransform(255 - b, cv2.DIST_L2, 5)
    d_ref_to_rend = float(db[a > 0].mean()); d_rend_to_ref = float(da[b > 0].mean())
    far_ref = float((db[a > 0] > 4).mean()); far_rend = float((da[b > 0] > 4).mean())
    ov = np.full_like(ref, 255)
    ov[(a > 0) & (b == 0)] = (0, 0, 255); ov[(b > 0) & (a == 0)] = (255, 0, 0); ov[(a > 0) & (b > 0)] = (0, 0, 0)
    for name, mask in (("reference-only (red)", (a > 0) & (db > 4)), ("render-only (blue)", (b > 0) & (da > 4))):
        n, lab, st, cen = cv2.connectedComponentsWithStats(mask.astype(np.uint8) * 255, 8)
        blobs = sorted([(int(st[i][4]), int(cen[i][0]), int(cen[i][1])) for i in range(1, n) if st[i][4] >= 15], reverse=True)[:12]
        print(f"{name} clusters (area, x, y): {blobs}")
    cv2.imwrite(str(OUT), np.vstack([ref, canvas, ov]))
    print(f"stroke IoU={iou:.3f}  mean dist ref->render={d_ref_to_rend:.2f}px  render->ref={d_rend_to_ref:.2f}px  "
          f"ref px farther than 4px={far_ref:.1%}  render px farther than 4px={far_rend:.1%}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
