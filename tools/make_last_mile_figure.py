#!/usr/bin/env python3
"""Map-style figure: where regulation concentrates on the last mile.

Draws the inbound road network to APM Terminals Elizabeth with the exact
line geometry of the approved reference graphic (visuals/last_mile_reference_lines.json,
built by tools/trace_reference_lines.py), annotates the rules coupled to ramps,
corridor, vehicle and gate, washes the streets that are
banded by jurisdictions with coupled rules or absence findings, shows coupled rules at each point of the shared
corridor as a thin strip, and lists the coupled rules grouped by governing
authority or operator.

Output: visuals/last_mile_regulation_map.png and .svg
"""

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

# Helvetica Neue ships as a .ttc; matplotlib reads only its first face, so
# "bold" and "medium" silently render as regular. If the faces have been
# extracted (fontTools TTCollection -> ~/.cache/last-mile-fonts), register them.
FONT_CACHE = Path.home() / ".cache/last-mile-fonts"
for _f in sorted(FONT_CACHE.glob("*.ttf")) if FONT_CACHE.exists() else []:
    font_manager.fontManager.addfont(str(_f))
MEDIUM = 500

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "visuals"
P = ROOT / "data/processed"

# ---------------------------------------------------------------- palette
INK, INK2, MUTED, GRID, BASE, SURFACE = ("#0b0b0b", "#52514e", "#898781",
                                         "#e1e0d9", "#c3c2b7", "#fcfcfb")
BOX = "#ffffff"
INK3 = "#6b6a66"                 # muted text that still prints
HAIR = "#ffffff"                 # hairline between lanes
BOX_LW = 0.6


def tint(hex_color, keep=0.42):
    """Opaque pastel of a palette color (keep = share of the color, rest white)."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(round(v * keep + 255 * (1 - keep))) for v in (r, g, b))

GROUP_COLOR = {              # validated categorical slots 1-6
    "federal": "#2a78d6", "state": "#eb6834", "county": "#1baf7a",
    "municipal": "#eda100", "panynj": "#e87ba4", "apm": "#008300",
}
AUTHORITY_GROUP = {
    "authority_fmcsa": "federal", "authority_fhwa": "federal",
    "authority_uscg": "federal", "authority_njdot": "state",
    "authority_njta": "state", "authority_njmvc": "state",
    "authority_union_county": "county", "authority_elizabeth_city": "municipal",
    "authority_panynj": "panynj", "operator_apm_terminals": "apm",
}
SHORT = {
    "reg_federal_group_a_cmv": "49 CFR 383.5 — CMV definition",
    "reg_federal_cdl": "49 CFR 383.23 — CDL",
    "reg_federal_interstate_weight": "23 CFR 658.17 — interstate weight",
    "reg_federal_twic": "33 CFR 101.514 — TWIC",
    "reg_nj_width_limit": "width limit",
    "reg_nj_height_limit": "height limit",
    "reg_nj_semitrailer_length": "semitrailer length",
    "reg_nj_tandem_gross_bridge": "gross / bridge formula",
    "reg_nj_noninterstate_single_axle": "single-axle (non-interstate)",
    "reg_nj_access_network_600_series": "N.J.A.C. 16:32 App. C — 600-series",
    "reg_njta_roadway_use_limitations": "N.J.A.C. 19:9-1.9 — Turnpike use limits",
    "reg_union_county_truck_routes_reserved": "Union County § 138-9 — \"(Reserved)\"",
    "reg_elizabeth_four_ton_limit_streets": "Elizabeth 10.16.010 — 4-ton table",
    "reg_elizabeth_five_ton_limit_streets": "Elizabeth 10.16.040 — 5-ton table",
    "reg_elizabeth_north_avenue_east_zone": "Elizabeth 10.16.050 — 80,000 lb zone",
    "reg_panynj_terminal_traffic": "PA-10 34-290 — state legislation applies",
    "reg_panynj_dtr": "PA-10 34-1100 — Drayage Truck Registry",
    "reg_panynj_rfid": "RFID tag",
    "reg_panynj_sealink_twic": "SeaLink / TWIC credential",
    "reg_apm_appointment": "APM — appointment required",
    "reg_apm_safety_induction": "APM — safety induction",
}
GROUP_NAME = {
    "federal": "Federal agencies", "state": "State of New Jersey",
    "panynj": "Port Authority of NY & NJ", "county": "Union County",
    "municipal": "City of Elizabeth", "apm": "APM Terminals",
}
ROSTER_ORDER = ["federal", "state", "panynj", "county", "municipal", "apm"]
THEME = {                    # rule -> roster line (grouped, not per citation)
    "reg_federal_group_a_cmv": "driver / vehicle qualification (49 CFR 383)",
    "reg_federal_cdl": "driver / vehicle qualification (49 CFR 383)",
    "reg_federal_interstate_weight": "interstate weight (23 CFR 658.17)",
    "reg_federal_twic": "port security credential — TWIC (33 CFR 101.514)",
    "reg_nj_width_limit": "size / weight limits (N.J.S.A. 39:3-84)",
    "reg_nj_height_limit": "size / weight limits (N.J.S.A. 39:3-84)",
    "reg_nj_semitrailer_length": "size / weight limits (N.J.S.A. 39:3-84)",
    "reg_nj_tandem_gross_bridge": "size / weight limits (N.J.S.A. 39:3-84)",
    "reg_nj_noninterstate_single_axle": "size / weight limits (N.J.S.A. 39:3-84)",
    "reg_nj_access_network_600_series": "App. C access network — route not listed",
    "reg_njta_roadway_use_limitations": "Turnpike use limits (NJTA 19:9-1.9)",
    "reg_union_county_truck_routes_reserved": "truck-route schedule § 138-9 — \"(Reserved)\"",
    "reg_elizabeth_four_ton_limit_streets": "weight-limit street tables — streets not listed",
    "reg_elizabeth_five_ton_limit_streets": "weight-limit street tables — streets not listed",
    "reg_elizabeth_north_avenue_east_zone": "{zone_weight:,} lb zone — overlap only",
    "reg_panynj_terminal_traffic": "tariff PA-10 — state legislation applies (34-290)",
    "reg_panynj_dtr": "tariff PA-10 — Drayage Truck Registry (34-1100)",
    "reg_panynj_rfid": "gate credentials — RFID tag, SeaLink / TWIC",
    "reg_panynj_sealink_twic": "gate credentials — RFID tag, SeaLink / TWIC",
    "reg_apm_appointment": "appointment required",
    "reg_apm_safety_induction": "safety induction",
}
THEME_ORDER = list(dict.fromkeys(THEME.values()))
WHERE = {                    # coupling target -> where the rule attaches
    "scoped_80000lb_5axle_nonhaz_inbound_apm": "carried by the truck",
    "node_apm_inbound_gate": "at the gate",
    "edge_a_nb_turnpike_exit": "approach ramps",
    "edge_a_exit13a_connector": "approach ramps",
    "edge_a_nb_state_ramps_to_north_ave": "approach ramps",
    "edge_b_us1_south": "approach ramps",
}
WHERE_ORDER = ["carried by the truck", "approach ramps", "corridor", "at the gate"]
ABSENCE_RELS = {"STREET_NOT_LISTED_IN_RESTRICTION_TABLE",
                "ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C",
                "TRUCK_ROUTE_SCHEDULE_RESERVED"}
PROFILE = "scoped_80000lb_5axle_nonhaz_inbound_apm"
GATE = "node_apm_inbound_gate"
SHARED = ["edge_shared_north_avenue", "edge_shared_mclester",
          "edge_shared_tripoli_gate"]
CANDIDATE = {"edge_a_nb_turnpike_exit", "edge_a_nb_state_ramps_to_north_ave",
             "edge_ab_shared_north_ave_to_all_merge"}

REF_LINES = ROOT / "visuals/last_mile_reference_lines.json"
# Which data edge each reference line piece stands for (see docstring of
# tools/trace_reference_lines.py for the piece names). Curves are assigned per
# vertex from the nearest anchor point.
SEGMENT_EDGE = {
    **{f"approach-north-{i}": ("edge_b_us1_south",) for i in range(1, 9)},
    **{f"approach-west-{i}": ("edge_b_us1_south",) for i in range(1, 7)},
    **{f"approach-west-{i}": ("edge_b_north_avenue_to_merge",) for i in range(7, 10)},
    **{f"shared-corridor-{i}": ("edge_shared_north_avenue",) for i in range(1, 5)},
    **{f"shared-corridor-{i}": ("edge_shared_mclester",) for i in range(5, 9)},
    "gate-link-1": ("edge_shared_tripoli_gate",),
}
CURVE_ANCHORS = [   # (x, y, edges) in slide px
    ((499, 551), ("edge_a_nb_turnpike_exit",)), ((515, 525), ("edge_a_nb_turnpike_exit",)),
    ((545, 500), ("edge_a_nb_turnpike_exit",)), ((578, 485), ("edge_a_nb_turnpike_exit",)),
    ((582, 465), ("edge_a_nb_turnpike_exit",)), ((572, 452), ("edge_a_nb_turnpike_exit",)),
    ((600, 447), ("edge_a_exit13a_connector",)), ((630, 430), ("edge_a_exit13a_connector",)),
    ((657, 401), ("edge_a_exit13a_connector",)), ((680, 372), ("edge_a_exit13a_connector",)),
    ((709, 331), ("edge_a_exit13a_connector",)),
    ((550, 443), ("edge_a_exit13a_connector", "edge_a_nb_turnpike_exit")),   # NB ramps run to the split
    ((534, 431), ("edge_a_exit13a_connector", "edge_a_nb_turnpike_exit")),   # ramp-split dot
    ((530, 400), ("edge_a_exit13a_connector", "edge_a_nb_state_ramps_to_north_ave")),
    ((540, 375), ("edge_a_exit13a_connector", "edge_ab_shared_north_ave_to_all_merge")),
    ((562, 356), ("edge_a_exit13a_connector", "edge_ab_shared_north_ave_to_all_merge")),
    ((500, 200), ("edge_a_exit13a_connector",)),     # inset ramp geometry
]
BAND_ORDER = ["state", "county", "municipal", "federal"]   # outermost first
BAND_PX = 3.0                                              # slide px per lane
LANE_GAP = 0.75                                            # hairline between lanes, slide px
SLIDE_W, MAP_Y0, MAP_Y1 = 1280, 40, 560      # reference slide px shown in the map
FIG_W, FIG_H = 17, 11
MAP_AX = [0.02, 0.30, 0.96, 0.96 * FIG_W / FIG_H * (MAP_Y1 - MAP_Y0) / SLIDE_W]
PX = 0.96 * FIG_W * 72 / SLIDE_W             # points per slide px
CHIP_IN = 0.09                               # color chip side, inches


def load():
    edges = json.loads((P / "physical_edges.json").read_text())["edges"]
    n_nodes = len(json.loads((P / "physical_nodes.geojson").read_text())["features"])
    rules = {r["rule_id"]: r for r in
             json.loads((P / "regulatory_nodes.json").read_text())["rules"]}
    couplings = json.loads((P / "coupling_edges.json").read_text())["edges"]
    lines = json.loads(REF_LINES.read_text())
    return edges, n_nodes, rules, couplings, lines


def main():
    edges, n_nodes, rules, couplings, L = load()
    group_of = {rid: AUTHORITY_GROUP[r["authority_entity_id"]]
                for rid, r in rules.items()}

    on_target = defaultdict(list)          # target -> [(rule, rel)]
    absence_rules, absence_edges = set(), set()
    for c in couplings:
        if not c["from_node"].startswith("reg_"):
            continue
        on_target[c["to_node"]].append((c["from_node"], c["relationship"]))
        if c["relationship"] in ABSENCE_RELS:
            absence_rules.add(c["from_node"])
            absence_edges.add(c["to_node"])
    coupled_rules = {r for lst in on_target.values() for r, _ in lst}
    carried = list(dict.fromkeys(r for r, _ in on_target[PROFILE]))
    at_gate = list(dict.fromkeys(r for r, _ in on_target[GATE]))
    gate_only = set(at_gate) - set(carried)
    gate_also_carried = set(at_gate) & set(carried)
    profile = next(p for p in json.loads((P / "vehicle_profiles.json").read_text())["profiles"]
                   if p["profile_id"] == PROFILE)["supplied_facts"]
    zone_label = rules["reg_elizabeth_north_avenue_east_zone"]["label"]
    zone_match = re.search(r"([\d,]+) pound", zone_label)
    if zone_match is None:
        raise ValueError(f"Missing weight in source rule label: {zone_label}")
    zone_weight = int(zone_match.group(1).replace(",", ""))
    traffic = json.loads((P / "traffic_analysis.json").read_text())["station_comparison"]
    ramp_rules = sorted({r for tgt in ("edge_a_nb_turnpike_exit",
                                       "edge_a_exit13a_connector")
                         for r, _ in on_target[tgt]
                         if group_of[r] in ("federal", "state")
                         and r not in {x for x, _ in on_target["edge_shared_mclester"]}})

    def stack(target):
        ids = defaultdict(set)
        for r, _ in on_target[target]:
            ids[group_of[r]].add(r)
        return {g: len(rids) for g, rids in ids.items()}

    def is_governing(rel):
        return rel == "GOVERNS" or rel.startswith("GOVERNS_")

    def breakdown(entries):
        """Distinct rule IDs in each relationship category, never row counts."""
        ids = {"governing": set(), "absence": set(), "overlap": set()}
        for rid, rel in entries:
            if is_governing(rel):
                ids["governing"].add(rid)
            elif rel in ABSENCE_RELS:
                ids["absence"].add(rid)
            elif rel == "OVERLAPS_PART_OF":
                ids["overlap"].add(rid)
            else:
                raise ValueError(f"Unclassified relationship in strip counts: {rel}")
        return {category: len(rids) for category, rids in ids.items()}

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "svg.fonttype": "path",          # outlines: renders identically anywhere
        "font.size": 8,
    })
    fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=SURFACE)

    # ================================================================ map
    # Road lines reproduce the approved reference graphic exactly: straight
    # segments, dots, arrows and wash are the editable pptx coordinates, the
    # redrawn curves are traced from its export (see tools/trace_reference_lines.py).
    ax = fig.add_axes(MAP_AX)
    ax.set_facecolor(SURFACE)
    ax.set_xlim(0, SLIDE_W)
    ax.set_ylim(MAP_Y1, MAP_Y0)
    ax.axis("off")

    def line(x0, y0, x1, y1, w, color, z, **kw):
        ax.plot([x0, x1], [y0, y1], lw=w * PX, color=color, zorder=z,
                solid_capstyle="round", solid_joinstyle="round", **kw)

    def cover(edge_ids):
        relationships = defaultdict(set)
        for eid in edge_ids:
            for rid, rel in on_target[eid]:
                relationships[group_of[rid]].add(rel)
        return relationships

    # Pattern lengths are in slide pixels, independent of the nested stroke
    # width. Short marks remain distinct from dashes at reduced viewing size.
    lane_patterns = {"dashed": (7, 5), "dotted": (1.3, 3.2)}

    def lane_style(rels):
        if any(is_governing(rel) for rel in rels):
            return "solid"
        if "OVERLAPS_PART_OF" in rels:
            return "dotted"
        if rels and rels <= ABSENCE_RELS:
            return "dashed"
        raise ValueError(f"Unclassified lane relationships: {rels}")

    def bands(xs, ys, w, groups):
        # lanes outer -> inner; every lane sits on a white hairline ring so the
        # lanes stay countable. Layer k of all pieces shares one zorder, so the
        # hairlines of one piece never cut into a neighbour's lane at a joint.
        present = [g for g in BAND_ORDER if g in groups]
        n = len(present)
        for k, g in enumerate(present):
            width = w + 2 * BAND_PX * (n - k)
            style = lane_style(groups[g])
            # Matplotlib scales dash lengths by linewidth. Undo that scaling
            # so all lanes use the same physical pattern. The solid white
            # underlay masks wider lanes throughout every dash/dot gap.
            stroke = ("solid" if style == "solid" else
                      (0, tuple(v / width for v in lane_patterns[style])))
            ax.plot(xs, ys, lw=(width + 2 * LANE_GAP) * PX, color=HAIR,
                    zorder=1.85 + 0.02 * k, solid_capstyle="round",
                    solid_joinstyle="round")
            ax.plot(xs, ys, lw=width * PX, color=tint(GROUP_COLOR[g]),
                    zorder=1.86 + 0.02 * k, solid_capstyle="round",
                    solid_joinstyle="round", linestyle=stroke,
                    dash_capstyle="butt")
        ax.plot(xs, ys, lw=(w + 2 * LANE_GAP) * PX, color=HAIR, zorder=1.97,
                solid_capstyle="round", solid_joinstyle="round")

    def nearest_edges(pt):
        return min(CURVE_ANCHORS, key=lambda a: (a[0][0] - pt[0]) ** 2 + (a[0][1] - pt[1]) ** 2)[1]

    for s_ in L["segments"]:
        bands([s_["x0"], s_["x1"]], [s_["y0"], s_["y1"]], s_["width"],
              cover(SEGMENT_EDGE[s_["name"]]))
    for c in L["curves"]:
        pts = c["pts"]
        runs, cur, cur_e = [], [pts[0]], nearest_edges(pts[0])
        for pt in pts[1:]:
            e = nearest_edges(pt)
            if e != cur_e:
                cur.append(pt); runs.append((cur, cur_e)); cur, cur_e = [pt], e
            else:
                cur.append(pt)
        runs.append((cur, cur_e))
        for run, e in runs:
            xs, ys = zip(*run)
            bands(xs, ys, c["width"], cover(e))
    for sp in L["spokes"]:
        line(sp["x0"], sp["y0"], sp["x1"], sp["y1"], 1.2, MUTED, 1.5)
    for c in L["curves"]:
        xs, ys = zip(*c["pts"])
        ax.plot(xs, ys, lw=c["width"] * PX, color=INK, zorder=2,
                solid_capstyle="round", solid_joinstyle="round")
    for s in L["segments"]:
        line(s["x0"], s["y0"], s["x1"], s["y1"], s["width"], INK, 3)
    for a in L["arrows"]:                      # pptx triangle: apex up, rot clockwise
        r = math.radians(a["rot"]); cs, sn = math.cos(r), math.sin(r)
        loc = [(0, -a["h"] / 2), (a["w"] / 2, a["h"] / 2), (-a["w"] / 2, a["h"] / 2)]
        ax.add_patch(plt.Polygon([(a["cx"] + x * cs - y * sn, a["cy"] + x * sn + y * cs)
                                  for x, y in loc], closed=True, facecolor=INK,
                                 edgecolor="none", zorder=4))
    for d in L["dots"]:
        ax.plot([d["x"]], [d["y"]], marker="o", ms=d["d"] * PX, mfc=INK, mec=SURFACE,
                mew=0.9 * PX, zorder=5, linestyle="none")
    for rg in L["rings"]:
        ax.plot([rg["x"]], [rg["y"]], marker="o", ms=rg["d"] * PX, mfc=SURFACE, mec=INK,
                mew=1.7 * PX, zorder=5, linestyle="none")

    def T(x, y, text, size=8.5, color=INK, bold=False, ha="left", va="center",
          linespacing=1.3, **kw):
        ax.text(x, y, text, fontsize=size, color=color, ha=ha, va=va,
                fontweight=MEDIUM if bold else "normal", zorder=6,
                linespacing=linespacing, **kw)

    # named points of the shared corridor
    T(578, 343, "all approaches merge", bold=True)
    T(877, 471, "North Ave × McLester", bold=True)
    T(893, 272, "McLester × Tripoli", bold=True)
    T(1003, 311, "APM inbound gate", bold=True)
    T(1003, 326, f"{len(gate_only)} gate-only rules", size=7.5, color=INK2, va="top")
    T(125, 385, "Traffic context upstream of the merge —\n"
      f"NJDOT {traffic['count_year']} two-station comparison:\n"
      f"{traffic['merge_station']['station_id']}: {traffic['merge_station']['aadt_total']:,} AADT, "
      f"{traffic['merge_station']['aadt_total'] / traffic['upstream_station']['aadt_total']:.2f}×\n"
      f"upstream station {traffic['upstream_station']['station_id']};\n"
      "both counts precede the full merge",
      size=7.5, color=INK2, va="top")

    # approaches
    T(722, 322, "Path A — NJ Tpk SB Exit 13A\noperator-published", bold=True)
    T(485, 551, "Path A′ — NJ Tpk NB Exit 13A\ncandidate approach, centerline-connected",
      size=8, color=INK2, ha="right")
    T(205, 78, "Path B — US 1 & 9 South (SB via NJ-81)\noperator-published", bold=True)
    T(212, 52, "Kearny / Meadowlands", size=7.5, color=INK2)
    T(10, 232, "US 1 & 9 NB", size=7.5, color=INK2)
    T(108, 290, "Linden / Tremley Point", size=7.5, color=INK2)

    # corridor names
    T(770, 460, "North Avenue East (CR 624)", size=8, color=INK2, ha="center",
      fontstyle="italic", rotation=-20)
    T(905, 372, "McLester St", size=8, color=INK2, ha="center", fontstyle="italic",
      rotation=51)
    T(430, 305, "North Avenue", size=8, color=INK2, ha="center", fontstyle="italic",
      rotation=-8)

    # ramp rules annotation
    T(563, 282, "on the Turnpike ramps:\n" + "\n".join(SHORT[r] for r in ramp_rules),
      size=7.5, color=INK2, va="top", linespacing=1.35)

    # The reference PNG explicitly captions this curve "Path A geometry
    # enlarged"; its CURVE_ANCHORS assignment is the Path A connector edge.
    ax.add_patch(FancyBboxPatch((414, 116), 245, 158,
                                boxstyle="round,pad=0,rounding_size=8",
                                facecolor=BOX, edgecolor=GRID, lw=BOX_LW, zorder=1.8))
    T(428, 133, "Exit 13A — published A, candidate A′", size=8, bold=True)
    T(428, 147, "Path A ramp geometry enlarged (reference)", size=7, color=INK2)
    T(585, 160, "NJ Tpk Exit 13A\n(from north)", size=7, color=INK2, va="top")
    T(468, 251, "NJ Tpk Exit 13A\n(from south)", size=7, color=INK2, va="top")
    T(550, 409, "Path A: see inset", size=7, color=INK2)

    # ---------------------------------------------------------- callouts
    def rule_box(fx, fy, title, sub, items, width):
        lines = [(None, title), (None, sub)] + items
        height = 0.017 * len(lines) + 0.03
        text_ax = fig.add_axes([fx, fy, width, height])
        text_ax.axis("off")
        text_ax.add_patch(FancyBboxPatch(
            (0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.03",
            transform=text_ax.transAxes, facecolor=BOX, edgecolor=GRID,
            lw=BOX_LW))
        n = len(lines)
        chip_w, chip_h = CHIP_IN / (width * FIG_W), CHIP_IN / (height * FIG_H)
        for i, (color, txt) in enumerate(lines):
            y = 1 - (i + 0.75) / (n + 0.35)
            if i == 0:
                text_ax.text(0.05, y, txt, fontsize=9.5, fontweight=MEDIUM,
                             color=INK, va="center", transform=text_ax.transAxes)
            elif i == 1:
                text_ax.text(0.05, y, txt, fontsize=7.5, color=INK2,
                             va="center", transform=text_ax.transAxes)
            else:
                text_ax.add_patch(FancyBboxPatch(
                    (0.05, y - chip_h / 2), chip_w, chip_h,
                    boxstyle="round,pad=0,rounding_size=0.004",
                    facecolor=color, edgecolor="none",
                    transform=text_ax.transAxes))
                text_ax.text(0.05 + chip_w + 0.025, y, txt, fontsize=8, color=INK,
                             va="center", transform=text_ax.transAxes)

    rule_box(0.025, 0.315,
             f"The truck enters carrying {len(carried)} rules",
             "attached to the vehicle or driver, not a road segment:",
             [(GROUP_COLOR[group_of[r]], SHORT[r]) for r in carried], 0.215)
    gate_items = [(GROUP_COLOR[group_of[r]],
                   SHORT[r] + ("  (also carried)" if r in carried else ""))
                  for r in at_gate]
    rule_box(0.755, 0.735, f"{len(at_gate)} gate-coupled rules",
             f"{len(gate_only)} only here; {len(gate_also_carried)} also carried by the truck",
             gate_items, 0.225)

    # map legend
    lx, ly = 0.80, 0.53
    fig.add_artist(plt.Line2D([lx, lx + 0.03], [ly, ly], lw=7.5, color=INK,
                              solid_capstyle="round"))
    fig.text(lx + 0.038, ly, "shared corridor (merged)",
             fontsize=8, color=INK, va="center")
    fig.add_artist(plt.Line2D([lx, lx + 0.03], [ly - 0.028, ly - 0.028], lw=4.2,
                              color=INK, solid_capstyle="round"))
    fig.text(lx + 0.038, ly - 0.028, "operator-published approach",
             fontsize=8, color=INK, va="center")
    fig.add_artist(plt.Line2D([lx, lx + 0.03], [ly - 0.056, ly - 0.056], lw=3.4,
                              color=INK, solid_capstyle="round"))
    fig.text(lx + 0.038, ly - 0.056, "candidate (centerline-connected,\nnot truck-verified)",
             fontsize=8, color=INK, va="center")
    fig.text(lx, ly - 0.092, "lanes = jurisdictions coupled to the road",
             fontsize=8, color=INK, va="center", fontweight=MEDIUM)
    for i, g in enumerate(BAND_ORDER):
        yy = ly - 0.120 - 0.026 * i
        fig.add_artist(plt.Line2D([lx, lx + 0.03], [yy, yy], lw=6,
                                  color=tint(GROUP_COLOR[g]),
                                  solid_capstyle="round"))
        fig.text(lx + 0.038, yy, GROUP_NAME[g], fontsize=8, color=INK, va="center")

    for i, (style, label) in enumerate((
            ("solid", "governing rule present"),
            ("dashed", "absence findings only"),
            ("dotted", "absence + partial overlap"))):
        yy = ly - 0.224 - 0.019 * i
        stroke = ("solid" if style == "solid" else
                  (0, tuple(v * PX / 2 for v in lane_patterns[style])))
        fig.add_artist(plt.Line2D([lx, lx + 0.03], [yy, yy], lw=2,
                                  color=INK2, linestyle=stroke, dash_capstyle="butt"))
        fig.text(lx + 0.038, yy, label, fontsize=7.5, color=INK2, va="center")

    # ============================================ bottom panel: strip + roster
    # The strip separates governing rules from findings at each downstream
    # road segment; the roster groups the full inventory by authority/operator.
    point_entries = [on_target[eid] for eid in SHARED]
    point_entries.append(on_target[SHARED[-1]] + on_target[GATE])
    point_counts = [breakdown(entries) for entries in point_entries]
    carried_down = point_counts[-2]["governing"]
    gate_governing = breakdown(on_target[GATE])["governing"]
    gate_total = point_counts[-1]["governing"]
    stops = list(zip(("all approaches merge", "North Ave × McLester",
                      "McLester × Tripoli", "APM gate"), point_counts))

    sx0, sx1, sy = 0.075, 0.60, 0.242
    fig.text(0.025, 0.290, "Rules coupled along the route", fontsize=11,
             fontweight=MEDIUM, color=INK, va="center")
    fig.add_artist(plt.Line2D([0.025, 0.72], [0.281, 0.281], lw=0.6, color=GRID))
    fig.text(0.025, 0.274,
             "Large numbers: distinct governing rules on each stop’s downstream road segment + gate rules at last stop; "
             "not cumulative truck obligations or burden / severity.",
             fontsize=7.5, color=INK2, va="center")
    fig.add_artist(plt.Line2D([sx0, sx1], [sy, sy], lw=0.8, color=BASE,
                              solid_capstyle="round"))
    for i, (nm, counts) in enumerate(stops):
        x = sx0 + (sx1 - sx0) * i / (len(stops) - 1)
        last = i == len(stops) - 1
        fig.add_artist(plt.Line2D([x], [sy], marker="D" if last else "o",
                                  ms=9 if last else 7, mfc=INK if last else SURFACE,
                                  mec=INK, mew=1.6, color="none"))
        fig.text(x, sy + 0.018, str(counts["governing"]), fontsize=13, fontweight="bold",
                 color=INK, ha="center", va="center")
        fig.text(x, sy - 0.014, nm, fontsize=7.5, color=INK, ha="center",
                 va="top", fontweight=MEDIUM, linespacing=1.2)
        findings = f"+{counts['absence']} absence findings"
        if counts["overlap"]:
            findings += f"; +{counts['overlap']} partial overlap"
        fig.text(x, sy - 0.028, findings,
                 fontsize=7, color=INK3, ha="center", va="top")
    fig.text(sx1 + 0.02, sy,
             f"{gate_total} governing = {carried_down} on Tripoli St + {gate_governing} at the gate",
             fontsize=7, color=INK3, va="center", linespacing=1.35)

    # roster: coupled rules grouped by governing authority or operator
    roster = defaultdict(lambda: defaultdict(int))
    where = defaultdict(set)
    for rid in coupled_rules:
        roster[group_of[rid]][THEME[rid]] += 1
        for tgt, lst in on_target.items():
            if any(r == rid for r, _ in lst):
                where[group_of[rid]].add(WHERE.get(tgt, "corridor"))
    n_rules = len(coupled_rules)
    fig.text(0.025, 0.190,
             f"Authorities and operators represented in the {n_rules} source-verified rules", fontsize=11,
             fontweight=MEDIUM, color=INK, va="center")
    fig.add_artist(plt.Line2D([0.025, 0.72], [0.182, 0.182], lw=0.6, color=GRID))
    fig.text(0.025, 0.175,
             "Grouped by authority / operator; includes governing rules, absence findings and partial overlap. "
             "Gray line = where the group attaches.",
             fontsize=7.5, color=INK2, va="center")
    cols, cw, ch, gx_, gy_ = 3, 0.222, 0.055, 0.012, 0.007
    for i, g in enumerate(ROSTER_ORDER):
        if g not in roster:
            continue
        cx = 0.025 + (i % cols) * (cw + gx_)
        cy = 0.162 - ch - (i // cols) * (ch + gy_)
        card = fig.add_axes([cx, cy, cw, ch])
        card.axis("off")
        card.add_patch(FancyBboxPatch(
            (0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.04",
            transform=card.transAxes, facecolor=BOX, edgecolor=GRID, lw=BOX_LW))
        chip_w, chip_h = CHIP_IN / (cw * FIG_W), CHIP_IN / (ch * FIG_H)
        card.add_patch(FancyBboxPatch((0.045, 0.82 - chip_h / 2), chip_w, chip_h,
                                      boxstyle="round,pad=0,rounding_size=0.004",
                                      facecolor=GROUP_COLOR[g], edgecolor="none",
                                      transform=card.transAxes))
        total = sum(roster[g].values())
        tx = 0.045 + chip_w + 0.03
        card.text(tx, 0.82, f"{GROUP_NAME[g]} — {total}", fontsize=8.5,
                  fontweight=MEDIUM, color=INK, va="center",
                  transform=card.transAxes)
        themes = [t for t in THEME_ORDER if t in roster[g]]
        for j, t in enumerate(themes):
            card.text(tx, 0.625 - 0.165 * j,
                      f"{t.format(zone_weight=zone_weight)} — {roster[g][t]}", fontsize=7.2, color=INK,
                      va="center", transform=card.transAxes)
        wtxt = " · ".join(w for w in WHERE_ORDER if w in where[g])
        card.text(tx, 0.625 - 0.165 * len(themes), wtxt, fontsize=6.8,
                  color=INK3, va="center", transform=card.transAxes)

    # Checked-source absence findings (not a legality determination).
    rule_box(0.755, 0.045, "No street listing found in checked sources",
             "Checked: street tables / App. C / reserved schedule",
             [(GROUP_COLOR[group_of[r]], SHORT[r]) for r in sorted(absence_rules)],
             0.225)

    # ============================================================ titles
    fig.text(0.025, 0.965, "Where does regulation concentrate on the last mile?",
             fontsize=20, fontweight=MEDIUM, color=INK, va="top")
    fig.text(0.025, 0.930,
             f"{len(coupled_rules)} source-verified rules coupled to an {profile['gross_weight_lbs']:,} lb, "
             f"{profile['axle_count']}-axle {'hazardous' if profile['cargo_hazardous'] else 'non-hazardous'} "
             f"container move {profile['movement_direction']} to "
             f"{profile['destination'].removesuffix('_gate').replace('_', ' ')} — "
             "the gate adds entry requirements beyond approach roads.", fontsize=11, color=INK2,
             va="top")
    n_coup = sum(len(v) for v in on_target.values())
    fig.text(0.025, 0.009,
             "Roads: approved visuals/last_mile_reference_lines.json (PPTX coordinates + traced curves); schematic, not georeferenced. "
             "Lanes: road-coupled rules or absence findings. "
             f"data/processed: {len(coupled_rules)} rules, {n_nodes} nodes, {len(edges)} edges, {n_coup} couplings; not compliance. "
             f"Traffic: traffic_analysis.json, NJDOT {traffic['count_year']}. "
             "Open circles: reference trip origins; apm_trip_origins.geojson noncanonical.\n"
             "AADT = annual average daily traffic; CMV = commercial motor vehicle; CDL = commercial driver's license; "
             "TWIC = Transportation Worker Identification Credential; DTR = Drayage Truck Registry; "
             "RFID = radio-frequency identification. Counts are a deduplicated inventory, not burden or severity.",
             fontsize=6.8, color=INK3, va="bottom", linespacing=1.45)

    OUT.mkdir(exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"last_mile_regulation_map.{ext}", dpi=300,
                    facecolor=SURFACE)
    print(f"rules coupled={len(coupled_rules)} carried={len(carried)} "
          f"gate={len(at_gate)} couplings={n_coup}")
    print("stacks:", {e: dict(stack(e)) for e in SHARED}, "gate:", dict(stack(GATE)))
    print("strip:", point_counts)
    print("roster:", {GROUP_NAME[g]: sum(v.values()) for g, v in roster.items()})
    print("wrote", OUT / "last_mile_regulation_map.png")


if __name__ == "__main__":
    main()
