#!/usr/bin/env python3
"""Render the road-network / regulatory-rule coupling figure.

Reads data/processed/coupling_edges.json and draws the 74 verified
rule-to-physical/profile couplings as a matrix aligned under the inbound
road-network spine (paths A southbound, A northbound candidate, B), with
segments colored by their raw NJOGIS road-authority category.

Output: visuals/road_rule_coupling.png and .svg
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "visuals"

# ---------------------------------------------------------------- palette
# Validated categorical slots 1-4 (dataviz reference palette, light mode).
AUTHORITY_COLOR = {
    "road_authority_category_highway_authority": "#2a78d6",
    "road_authority_category_state": "#eb6834",
    "road_authority_category_county": "#1baf7a",
    "road_authority_category_municipal": "#eda100",
}
AUTHORITY_LABEL = {
    "road_authority_category_highway_authority": "Highway Authority (NJTA)",
    "road_authority_category_state": "State",
    "road_authority_category_county": "County",
    "road_authority_category_municipal": "Municipal",
}
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
SURFACE = "#fcfcfb"
BAND = "#f0efec"
WASH = "#f6f5f2"

# ---------------------------------------------------------------- columns
# Travel order across the three inbound approaches, then gate and profile.
COLUMNS = [
    ("edge_a_nb_turnpike_exit", "Tpk NB\nExit 13A ramps"),
    ("edge_a_nb_state_ramps_to_north_ave", "Rt 81 state\nramps"),
    ("edge_a_exit13a_connector", "Tpk SB Exit 13A\nconnector"),
    ("edge_b_us1_south", "US 1 & 9\nSouth"),
    ("edge_b_north_avenue_to_merge", "North Ave\n(US 1 & 9 exit)"),
    ("edge_ab_shared_north_ave_to_all_merge", "North Ave\n(NB join)"),
    ("edge_shared_north_avenue", "North Avenue\nEast"),
    ("edge_shared_mclester", "McLester St"),
    ("edge_shared_tripoli_gate", "Tripoli St"),
    ("node_apm_inbound_gate", "APM inbound\ngate"),
    ("scoped_80000lb_5axle_nonhaz_inbound_apm", "Vehicle profile\n80,000 lb 5-axle"),
]
COL_X = {cid: i for i, (cid, _) in enumerate(COLUMNS)}
N_COLS = len(COLUMNS)
GATE_X = COL_X["node_apm_inbound_gate"]
PROFILE_X = COL_X["scoped_80000lb_5axle_nonhaz_inbound_apm"]

# Spine lanes (drawing coordinate d, increasing downward).
LANE_NB, LANE_MID, LANE_B = 0.55, 1.95, 3.35
SEGMENT_LANE = {
    "edge_a_nb_turnpike_exit": LANE_NB,
    "edge_a_nb_state_ramps_to_north_ave": LANE_NB,
    "edge_ab_shared_north_ave_to_all_merge": LANE_NB,
    "edge_a_exit13a_connector": LANE_MID,
    "edge_b_us1_south": LANE_B,
    "edge_b_north_avenue_to_merge": LANE_B,
    "edge_shared_north_avenue": LANE_MID,
    "edge_shared_mclester": LANE_MID,
    "edge_shared_tripoli_gate": LANE_MID,
}

# ---------------------------------------------------------------- rows
# (rule_id, short label); grouped by issuing authority, top = federal.
GROUPS = [
    ("FEDERAL", [
        ("reg_federal_group_a_cmv", "49 CFR 383.5 — Group A combination CMV class"),
        ("reg_federal_cdl", "49 CFR 383.23 — Commercial driver's license"),
        ("reg_federal_interstate_weight", "23 CFR 658.17 — Interstate weight limits"),
        ("reg_federal_twic", "33 CFR 101.514 — TWIC for secure-area access"),
    ]),
    ("STATE OF NEW JERSEY — NJDOT", [
        ("reg_nj_width_limit", "Size & Weight Guidebook 2.1.1 — Width limit"),
        ("reg_nj_height_limit", "Size & Weight Guidebook 2.1.2 — Height limit"),
        ("reg_nj_semitrailer_length", "Size & Weight Guidebook 2.1.3.6 — Semitrailer length"),
        ("reg_nj_tandem_gross_bridge", "Size & Weight Guidebook 2.2.2 — Gross / bridge formula"),
        ("reg_nj_noninterstate_single_axle", "Size & Weight Guidebook 2.2.1 — Single-axle (non-interstate)"),
        ("reg_nj_access_network_600_series", "N.J.A.C. 16:32 App. C — County 600-series access network"),
    ]),
    ("NJ TURNPIKE AUTHORITY", [
        ("reg_njta_roadway_use_limitations", "N.J.A.C. 19:9-1.9 — Roadway use limitations"),
    ]),
    ("UNION COUNTY", [
        ("reg_union_county_truck_routes_reserved", "Laws § 138-9 — Truck routes (schedule reserved)"),
    ]),
    ("CITY OF ELIZABETH", [
        ("reg_elizabeth_four_ton_limit_streets", "Code 10.16.010 — Four-ton limit street table"),
        ("reg_elizabeth_five_ton_limit_streets", "Code 10.16.040 — Five-ton limit street table"),
        ("reg_elizabeth_north_avenue_east_zone", "Code 10.16.050 — North Ave East 80,000 lb zone"),
    ]),
    ("PORT AUTHORITY NY & NJ", [
        ("reg_panynj_terminal_traffic", "Tariff PA-10 34-290 — Terminal traffic rules"),
        ("reg_panynj_dtr", "Tariff PA-10 34-1100 — Drayage Truck Registry"),
        ("reg_panynj_rfid", "RFID tag requirement"),
        ("reg_panynj_sealink_twic", "SeaLink / TWIC credential"),
    ]),
    ("APM TERMINALS (OPERATOR)", [
        ("reg_apm_appointment", "All gate moves require an appointment"),
        ("reg_apm_safety_induction", "Mandatory trucker safety induction"),
    ]),
]

GOVERNS_RELS = {
    "GOVERNS", "OVERLAPS_PART_OF", "GOVERNS_ENTRY_AT", "GOVERNS_GATE_MOVE_AT",
    "GOVERNS_ACCESS_AT", "GOVERNS_PORT_ENTRY_MOVEMENT_AT",
    "GOVERNS_UNESCORTED_SECURE_ACCESS_AT",
}
APPLIES_RELS = {"APPLIES_TO", "CLASSIFIES"}
ABSENCE_RELS = {"STREET_NOT_LISTED_IN_RESTRICTION_TABLE",
                "ROUTE_NUMBER_NOT_LISTED_IN_APPENDIX_C"}
RESERVED_RELS = {"TRUCK_ROUTE_SCHEDULE_RESERVED"}


def load_couplings():
    data = json.loads((ROOT / "data/processed/coupling_edges.json").read_text())
    rule_cells = {}   # rule_id -> list[(col_x, relationship)]
    seg_authority = {}
    for e in data["edges"]:
        frm, rel, to = e["from_node"], e["relationship"], e["to_node"]
        if frm.startswith("reg_"):
            if to not in COL_X:
                sys.exit(f"coupling target {to} has no column — update the figure layout")
            rule_cells.setdefault(frm, []).append((COL_X[to], rel))
        elif rel == "HAS_NJOGIS_JURISDICTION_CATEGORY":
            seg_authority[frm] = to
    drawn_rules = {rid for _, rules in GROUPS for rid, _ in rules}
    missing = set(rule_cells) - drawn_rules
    if missing:
        sys.exit(f"rules with couplings missing from figure rows: {sorted(missing)}")
    n_cells = sum(len(v) for v in rule_cells.values())
    return rule_cells, seg_authority, n_cells


def draw():
    rule_cells, seg_authority, n_cells = load_couplings()

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "svg.fonttype": "none",
    })

    n_rows = sum(len(rules) for _, rules in GROUPS)
    header_h, row_h = 0.85, 1.0
    matrix_top = 6.4
    matrix_h = len(GROUPS) * header_h + n_rows * row_h
    legend_top = matrix_top + matrix_h + 0.9
    d_max = legend_top + 4.6

    fig = plt.figure(figsize=(16, 12.4), facecolor=SURFACE)
    ax = fig.add_axes([0.005, 0.005, 0.99, 0.925])
    ax.set_facecolor(SURFACE)
    ax.set_xlim(-4.35, N_COLS + 0.35)
    ax.set_ylim(d_max, -0.4)          # d increases downward
    ax.axis("off")

    # ---------------- road-network spine ----------------
    bar_h = 0.52
    for cid, lane in SEGMENT_LANE.items():
        x = COL_X[cid]
        color = AUTHORITY_COLOR[seg_authority[cid]]
        ax.add_patch(FancyBboxPatch(
            (x + 0.06, lane - bar_h / 2), 0.88, bar_h,
            boxstyle="round,pad=0,rounding_size=0.10",
            facecolor=color, edgecolor="none", zorder=3))
        ax.plot([x + 0.80], [lane], marker=">", ms=5, color=SURFACE,
                mec="none", zorder=4)

    def connector(x0, d0, x1, d1):
        if d0 == d1:
            ax.plot([x0, x1], [d0, d1], color=BASE, lw=1.1, zorder=2)
        else:
            xm = x1 - 0.28
            ax.plot([x0, xm, xm, x1], [d0, d0, d1, d1], color=BASE, lw=1.1,
                    zorder=2, solid_joinstyle="round")

    connector(COL_X["edge_a_nb_state_ramps_to_north_ave"] + 0.94, LANE_NB,
              COL_X["edge_ab_shared_north_ave_to_all_merge"] + 0.06, LANE_NB)
    connector(COL_X["edge_ab_shared_north_ave_to_all_merge"] + 0.94, LANE_NB,
              COL_X["edge_shared_north_avenue"] + 0.06, LANE_MID)
    connector(COL_X["edge_a_exit13a_connector"] + 0.94, LANE_MID,
              COL_X["edge_shared_north_avenue"] + 0.06, LANE_MID)
    connector(COL_X["edge_b_north_avenue_to_merge"] + 0.94, LANE_B,
              COL_X["edge_shared_north_avenue"] + 0.06, LANE_MID)
    connector(COL_X["edge_shared_tripoli_gate"] + 0.94, LANE_MID,
              GATE_X + 0.42, LANE_MID)

    # gate node and vehicle-profile chip
    ax.plot([GATE_X + 0.5], [LANE_MID], marker="D", ms=9, color=INK, zorder=4)
    ax.text(GATE_X + 0.5, LANE_MID - 0.62, "gate", ha="center", va="bottom",
            fontsize=7.5, color=INK_2)
    ax.add_patch(FancyBboxPatch(
        (PROFILE_X + 0.08, LANE_MID - 0.62), 0.84, 1.24,
        boxstyle="round,pad=0,rounding_size=0.12",
        facecolor=WASH, edgecolor=BASE, lw=1.0, zorder=3))
    ax.text(PROFILE_X + 0.5, LANE_MID, "80,000 lb\n5-axle\nnon-haz", ha="center",
            va="center", fontsize=6.4, color=INK_2, zorder=4, linespacing=1.4)

    lane_labels = [
        (LANE_NB, "A′  NJ Turnpike NB Exit 13A  (candidate approach)"),
        (LANE_MID, "A  NJ Turnpike SB Exit 13A  (operator-published)"),
        (LANE_B, "B  US 1 & 9 South  (operator-published)"),
    ]
    for lane, label in lane_labels:
        ax.text(-0.18, lane, label, ha="right", va="center", fontsize=8,
                color=INK_2)

    # ---------------- column labels ----------------
    for cid, label in COLUMNS:
        ax.text(COL_X[cid] + 0.5, 4.55, label, ha="center", va="top",
                fontsize=7.6, color=INK, linespacing=1.3)

    # ---------------- matrix ----------------
    # background wash for non-roadway target columns (gate, profile)
    ax.add_patch(Rectangle((GATE_X, matrix_top), 2, matrix_h,
                           facecolor=WASH, edgecolor="none", zorder=0))

    d = matrix_top
    row_centers = {}
    for group_name, rules in GROUPS:
        ax.add_patch(Rectangle((-4.35, d), 4.35 + N_COLS + 0.35, header_h - 0.12,
                               facecolor=BAND, edgecolor="none", zorder=1))
        ax.text(-4.15, d + (header_h - 0.12) / 2, group_name, ha="left",
                va="center", fontsize=7.8, color=INK_2, fontweight="bold",
                zorder=2)
        d += header_h
        for rid, label in rules:
            c = d + row_h / 2
            row_centers[rid] = c
            ax.text(-0.18, c, label, ha="right", va="center", fontsize=8,
                    color=INK, zorder=2)
            ax.plot([0, N_COLS], [d + row_h, d + row_h], color=GRID, lw=0.5,
                    zorder=1)
            d += row_h
    matrix_bottom = d

    for x in range(N_COLS + 1):
        lw, color = (0.5, GRID)
        if x in (GATE_X, PROFILE_X, N_COLS):
            lw, color = (1.0, BASE)
        ax.plot([x, x], [matrix_top, matrix_bottom], color=color, lw=lw,
                zorder=1)
    ax.plot([-4.35, N_COLS], [matrix_top, matrix_top], color=BASE, lw=1.0,
            zorder=1)
    ax.plot([-4.35, N_COLS], [matrix_bottom, matrix_bottom], color=BASE,
            lw=1.0, zorder=1)

    # cells
    pts = {"governs": [], "applies": [], "absence": [], "reserved": [],
           "partial": []}
    for rid, cells in rule_cells.items():
        for col, rel in cells:
            xy = (col + 0.5, row_centers[rid])
            if rel == "OVERLAPS_PART_OF":
                pts["partial"].append(xy)
            elif rel in GOVERNS_RELS:
                pts["governs"].append(xy)
            elif rel in APPLIES_RELS:
                pts["applies"].append(xy)
            elif rel in ABSENCE_RELS:
                pts["absence"].append(xy)
            elif rel in RESERVED_RELS:
                pts["reserved"].append(xy)
            else:
                sys.exit(f"unhandled relationship {rel}")

    def scatter(key, **kw):
        if pts[key]:
            xs, ys = zip(*pts[key])
            ax.scatter(xs, ys, zorder=3, **kw)

    scatter("governs", marker="s", s=86, color=INK)
    scatter("applies", marker="o", s=86, color=INK)
    scatter("absence", marker="s", s=86, facecolors="none", edgecolors=MUTED,
            linewidths=1.3)
    scatter("reserved", marker="s", s=86, facecolors="none", edgecolors=MUTED,
            linewidths=1.3, linestyle=(0, (2, 2)))
    for x, y in pts["partial"]:
        ax.plot([x], [y], marker="s", ms=9.3, fillstyle="left", mfc=INK,
                mfcalt="none", mec=INK, mew=1.3, ls="none", zorder=3)

    # ---------------- legend ----------------
    ly = legend_top + 0.7
    ax.text(-4.15, ly, "Coupling", fontsize=8, fontweight="bold", color=INK_2,
            va="center")
    legend_glyphs = [
        ("governs segment / gate move", dict(marker="s", color=INK)),
        ("applies to vehicle / driver", dict(marker="o", color=INK)),
        ("verified absence — route not listed in rule's schedule",
         dict(marker="s", facecolors="none", edgecolors=MUTED, linewidths=1.3)),
        ("schedule reserved — no designations published",
         dict(marker="s", facecolors="none", edgecolors=MUTED, linewidths=1.3,
              linestyle=(0, (2, 2)))),
    ]
    lx = -2.7
    for label, kw in legend_glyphs:
        ax.scatter([lx], [ly], s=80, zorder=3, **kw)
        ax.text(lx + 0.22, ly, label, fontsize=8, color=INK, va="center")
        lx += 0.65 + len(label) * 0.062
    ax.plot([-2.7 + 0.1], [ly + 0.9], marker="s", ms=9, fillstyle="left",
            mfc=INK, mfcalt="none", mec=INK, mew=1.3, ls="none")
    ax.text(-2.7 + 0.32, ly + 0.9, "governs part of segment", fontsize=8,
            color=INK, va="center")

    ax.text(-4.15, ly + 1.8, "Road authority\n(raw NJOGIS)", fontsize=8,
            fontweight="bold", color=INK_2, va="center", linespacing=1.3)
    lx = -2.7
    for key in ("road_authority_category_highway_authority",
                "road_authority_category_state",
                "road_authority_category_county",
                "road_authority_category_municipal"):
        ax.add_patch(FancyBboxPatch(
            (lx, ly + 1.62), 0.42, 0.36,
            boxstyle="round,pad=0,rounding_size=0.08",
            facecolor=AUTHORITY_COLOR[key], edgecolor="none"))
        label = AUTHORITY_LABEL[key]
        ax.text(lx + 0.54, ly + 1.8, label, fontsize=8, color=INK,
                va="center")
        lx += 0.95 + len(label) * 0.062

    notes = [
        "Open cells are verified absences: the road segment was checked against the rule's street/route schedule and is not listed — an explicit finding, not missing data.",
        "Segment color is the raw NJOGIS road-authority category (9 HAS_NJOGIS_JURISDICTION_CATEGORY couplings). All nine segments additionally carry LOCATED_WITHIN City of Elizabeth and Union County (18 couplings, not drawn).",
        f"Coupling edges assert governance links only, never compliance (compliance_status: not_a_compliance_claim). {n_cells} rule couplings drawn; rule-text records without verified physical couplings are omitted.",
        "Source: data/processed/coupling_edges.json (schema 1.1-rule-to-physical), physical_edges.json, regulatory_nodes.json · paths path_a_exit13a_to_apm, path_b_us1_9_to_apm.",
    ]
    for i, note in enumerate(notes):
        ax.text(-4.15, ly + 2.7 + i * 0.55, note, fontsize=7, color=MUTED,
                va="center")

    fig.text(0.012, 0.985, "Coupling of the road network with regulatory rules",
             fontsize=15, fontweight="bold", color=INK, va="top")
    fig.text(0.012, 0.962,
             "Inbound APM Terminals Elizabeth · scoped vehicle profile 80,000 lb 5-axle non-hazardous · "
             "each mark is one verified coupling edge between a rule and a road segment, the terminal gate, or the vehicle profile",
             fontsize=9.5, color=INK_2, va="top")

    OUT_DIR.mkdir(exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(OUT_DIR / f"road_rule_coupling.{ext}", dpi=200,
                    facecolor=SURFACE)
    print(f"drew {n_cells} coupling cells for {len(rule_cells)} rules")
    print(f"wrote {OUT_DIR}/road_rule_coupling.png and .svg")


if __name__ == "__main__":
    draw()
