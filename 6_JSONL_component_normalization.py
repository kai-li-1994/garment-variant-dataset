# -*- coding: utf-8 -*-
"""
6_JSONL_component_normalization.py

Purpose
-------
Build a neutral component structure on top of the already material-normalized
and category-normalized JSONL.

This script does NOT redo material normalization.
It only:
- reads raw_material_text_norm first
- parses component-material blocks from raw_material_text_norm
- normalizes component names
- assigns component_class
- appends components_structured

It also records whether each parsed component path matched:
- PAT_COMPONENT_PATH_EXACT
- or remained unmatched

Input
-----
5_JSONL_category_normalized.jsonl

Output
------
6_JSONL_component_normalized.jsonl
6_JSONL_component_normalized_summary.txt
"""

#%% Import packages
import csv
import json
import re
from collections import Counter
import pandas as pd
#%% Input / output

input_file = r"5_JSONL_category_normalized.jsonl"
output_file = r"6_JSONL_component_normalized.jsonl"
summary_file = r"6_JSONL_component_normalized_summary.txt"

#%% Regex for block parsing

RE_PERCENT = re.compile(r"\d+(?:\.\d+)?\s*%")

RE_PCT_BEFORE = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*([A-Za-z][A-Za-z0-9_\s\-/&™®©\.]*?)(?=\s*(?:\d+(?:\.\d+)?\s*%|,|/|;|$|\(|\)))",
    flags=re.I
)

RE_PCT_AFTER = re.compile(
    r"\b([A-Za-z][A-Za-z0-9_\s\-/&™®©\.]*?)\s*(\d+(?:\.\d+)?)\s*%(?=\s*(?:\d+(?:\.\d+)?\s*%|,|/|;|$|\(|\)))",
    flags=re.I
)

DROP_EXACT = {
    "exclusive of decoration",
    "exclusive of trims",
    "-",
}

DROP_CONTAINS = [
    "may release plastic microfibres",
]

RE_RECYCLED_NOTE = re.compile(
    r"\(\s*(\d+(?:\.\d+)?)%\s*(?:made\s+from|uses)\s+recycled\s+([^)]+?)\s*\)",
    flags=re.I
)

#%% Component normalization rules
# first match wins
PAT_COMPONENT_PATH_EXACT = [
    # --------------------------------------------------
    # 1. surface_component
    # --------------------------------------------------
    (r"^back\s*body:\s*collar$", "body", "surface_component"),  # raw=Back Body: Collar | n=4
    (r"^body:\s*base$", "body", "surface_component"),  # raw=Body: Base | n=2
    (r"^body:\s*face$", "body", "surface_component"),  # raw=Body: Face | n=33
    (r"^body:\s*knit$", "body", "surface_component"),  # raw=Body: Knit | n=2
    (r"^body:\s*scarf$", "body", "surface_component"),  # raw=Body: Scarf | n=5
    (r"^body:\s*shell$", "shell", "surface_component"),  # raw=Body: Shell | n=2
    (r"^body:\s*skirt$", "body", "surface_component"),  # raw=Body: Skirt | n=20
    (r"^body:\s*woven$", "body", "surface_component"),  # raw=Body: Woven | n=2
    (r"^bottoms:\s*body$", "body", "surface_component"),  # raw=Bottoms: Body | n=4
    (r"^crotch:\s*face$", "face", "surface_component"),  # raw=Crotch: Face | n=2
    (r"^dress:\s*body$", "body", "surface_component"),  # raw=Dress: Body | n=2
    (r"^face:\s*base$", "face", "surface_component"),  # raw=Face: Base | n=4
    (r"^front\s*body:\s*sleeve$", "body", "surface_component"),  # raw=Front Body: Sleeve | n=4
    (r"^hood:\s*shell$", "shell", "surface_component"),  # raw=Hood: Shell | n=13
    (r"^lower\s*body:\s*sides\s*of\s*the\s*item:\s*sleeve$", "body", "surface_component"),  # raw=Lower Body: Sides of The Item: Sleeve / Lower Body: Sides of the Item: Sleeve | n=8
    (r"^lower\s*body:\s*top\s*sleeve$", "body", "surface_component"),  # raw=Lower Body: Top Sleeve | n=3
    (r"^shell:\s*base$", "shell", "surface_component"),  # raw=Shell: Base | n=38
    (r"^shell:\s*body$", "shell", "surface_component"),  # raw=Shell: Body | n=3
    (r"^shell:\s*knit$", "shell", "surface_component"),  # raw=Shell: Knit | n=5
    (r"^shell:\s*woven$", "shell", "surface_component"),  # raw=Shell: Woven | n=5
    (r"^skirt:\s*shell$", "shell", "surface_component"),  # raw=Skirt: Shell | n=1
    (r"^tops:\s*body$", "body", "surface_component"),  # raw=Tops: Body | n=9
    (r"^upper\s*body:\s*collar:\s*sleeve$", "body", "surface_component"),  # raw=Upper Body: Collar: Sleeve | n=1
    (r"^woven:\s*face$", "face", "surface_component"),  # raw=Woven: Face | n=3
    (r"^base$", "base_fabric", "surface_component"),  # raw=Base | n=7
    (r"^base\s*fabric$", "base_fabric", "surface_component"),  # raw=Base fabric | n=101
    (r"^back\s*body$", "body", "surface_component"),  # raw=Back Body | n=4
    (r"^body$", "body", "surface_component"),  # raw=Body | n=2107
    (r"^lower\s*body$", "body", "surface_component"),  # raw=Lower Body | n=2
    (r"^upper\s*body$", "body", "surface_component"),  # raw=Upper Body | n=3
    (r"^coating$", "coating", "surface_component"),  # raw=Coating | n=241
    (r"^face$", "face", "surface_component"),  # raw=Face | n=135
    (r"^main$", "main", "surface_component"),  # raw=main | n=29436
    (r"^main\s*fabric$", "main", "surface_component"),  # raw=Main fabric | n=4
    (r"^main\s*part$", "main", "surface_component"),  # raw=Main part | n=9
    (r"^outer\s*layer$", "outer_layer", "surface_component"),  # raw=Outer layer / Outer Layer | n=12
    (r"^back\s*shell$", "shell", "surface_component"),  # raw=Back shell | n=3
    (r"^front\s*shell$", "shell", "surface_component"),  # raw=Front shell | n=4
    (r"^shell$", "shell", "surface_component"),  # raw=Shell | n=16315
    (r"^wing\s*shell$", "shell", "surface_component"),  # raw=Wing shell | n=3

    # --------------------------------------------------
    # 2. lining_component
    # --------------------------------------------------
    (r"^body:\s*hood\s*lining$", "hood_lining", "lining_component"),  # raw=Body: Hood Lining | n=7
    (r"^body:\s*lining$", "body_lining", "lining_component"),  # raw=Body: Lining | n=4
    (r"^waist:\s*inner\s*pants$", "inner_pants", "lining_component"),  # raw=Waist: Inner Pants | n=4
    (r"^elastic\s*part:\s*interlining$", "interlining", "lining_component"),  # raw=Elastic Part: Interlining | n=2
    (r"^hood\s*edge:\s*inner\s*layer$", "inner_layer", "lining_component"),  # raw=Hood Edge: Inner Layer | n=25
    (r"^lining:\s*front\s*body$", "front_body_lining", "lining_component"),  # raw=Lining: Front Body | n=4
    (r"^lining:\s*body$", "body_lining", "lining_component"),  # raw=Lining: Body | n=11
    (r"^skirt:\s*lining$", "skirt_lining", "lining_component"),  # raw=Skirt: Lining | n=1
    (r"^lining:\s*checks$", "lining", "lining_component"),  # raw=Lining: Checks | n=4
    (r"^lining:\s*checks\s*pattern$", "lining", "lining_component"),  # raw=Lining: Checks Pattern | n=8
    (r"^lining:\s*knit$", "lining", "lining_component"),  # raw=Lining: Knit | n=1
    (r"^lining:\s*woven$", "lining", "lining_component"),  # raw=Lining: Woven | n=1
    (r"^body\s*lining$", "body_lining", "lining_component"),  # raw=Body lining / Body Lining | n=107
    (r"^cup\s*\(\s*inner\s*lining\s*\)$", "cup_lining", "lining_component"),  # raw=Cup ( Inner Lining ) | n=185
    (r"^cup\s*lining$", "cup_lining", "lining_component"),  # raw=Cup lining | n=219
    (r"^hood\s*lining$", "hood_lining", "lining_component"),  # raw=Hood lining / Hood Lining | n=260
    (r"^inner\s*layer$", "inner_layer", "lining_component"),  # raw=Inner layer / Inner Layer | n=170
    (r"^inner\s*pants$", "inner_pants", "lining_component"),  # raw=Inner Pants | n=8
    (r"^interlining$", "interlining", "lining_component"),  # raw=Interlining | n=4
    (r"^back\s*lining$", "lining", "lining_component"),  # raw=Back lining | n=24
    (r"^crotch\s*lining$", "lining", "lining_component"),  # raw=Crotch lining | n=810
    (r"^front\s*lining$", "lining", "lining_component"),  # raw=Front lining | n=67
    (r"^lining$", "lining", "lining_component"),  # raw=Lining | n=7139
    (r"^linings$", "lining", "lining_component"),  # raw=Linings | n=3
    (r"^neck\s*lining$", "lining", "lining_component"),  # raw=Neck lining | n=208
    (r"^net\s*lining$", "lining", "lining_component"),  # raw=Net lining | n=7
    (r"^upper\s*lining$", "lining", "lining_component"),  # raw=Upper lining | n=10
    (r"^waist\s*lining$", "lining", "lining_component"),  # raw=Waist lining | n=6
    (r"^wing\s*lining$", "lining", "lining_component"),  # raw=Wing lining | n=81
    (r"^petticoat$", "petticoat", "lining_component"),  # raw=Petticoat | n=39
    (r"^sleeve\s*lining$", "sleeve_lining", "lining_component"),  # raw=Sleeve lining / Sleeve Lining | n=202
    (r"^down\s*proof\s*fabric$", "down_proof_fabric", "lining_component"),  # raw=Down Proof Fabric

    # --------------------------------------------------
    # 3. pocket_component
    # --------------------------------------------------
    (r"^body:\s*pocket\s*lining$", "pocket_lining", "pocket_component"),  # raw=Body: Pocket Lining | n=81
    (r"^chest\s*pocket\s*fabric:\s*collar\s*lining$", "chest_pocket_fabric", "pocket_component"),  # raw=Chest Pocket Fabric: Collar Lining | n=6
    (r"^chest\s*pocket\s*fabric:\s*inner\s*layer$", "chest_pocket_fabric", "pocket_component"),  # raw=Chest Pocket Fabric: Inner Layer | n=5
    (r"^chest\s*pocket\s*fabric:\s*inner\s*layer:\s*side\s*pocket\s*fabric:\s*inner\s*layer$", "chest_pocket_fabric", "pocket_component"),  # raw=Chest Pocket Fabric: Inner Layer: Side Pocket Fabric: Inner Layer | n=3
    (r"^chest\s*pocket\s*fabric:\s*inner\s*pocket\s*fabric$", "chest_pocket_fabric", "pocket_component"),  # raw=Chest Pocket Fabric: Inner Pocket Fabric | n=1
    (r"^hood\s*lining:\s*pocket\s*lining$", "pocket_lining", "pocket_component"),  # raw=Hood Lining: Pocket Lining | n=2
    (r"^inner\s*layer:\s*patch\s*pocket$", "patch_pocket", "pocket_component"),  # raw=Inner Layer: Patch Pocket | n=2
    (r"^inner\s*pocket\s*fabric:\s*base$", "pocket_fabric", "pocket_component"),  # raw=Inner Pocket Fabric: Base | n=2
    (r"^inner\s*pocket\s*fabric:\s*chest\s*pocket\s*fabric$", "pocket_fabric", "pocket_component"),  # raw=Inner Pocket Fabric: Chest Pocket Fabric | n=8
    (r"^inner\s*pocket\s*fabric:\s*chest\s*pocket\s*fabric:\s*outer\s*layer$", "chest_pocket_fabric", "pocket_component"),  # raw=Inner Pocket Fabric: Chest Pocket Fabric: Outer Layer | n=1
    (r"^inner\s*pocket\s*fabric:\s*chest\s*pocket\s*fabric:\s*outer\s*layer:\s*side\s*pocket\s*fabric:\s*outer\s*layer$", "chest_pocket_fabric", "pocket_component"),  # raw=Inner Pocket Fabric: Chest Pocket Fabric: Outer Layer: Side Pocket Fabric: Outer Layer | n=3
    (r"^inner\s*pocket\s*fabric:\s*side\s*pocket\s*fabric$", "pocket_fabric", "pocket_component"),  # raw=Inner Pocket Fabric: Side Pocket Fabric | n=2
    (r"^inner\s*pocket\s*fabric:\s*side\s*pocket\s*fabric:\s*chest\s*pocket\s*fabric:\s*outer\s*layer$", "chest_pocket_fabric", "pocket_component"),  # raw=Inner Pocket Fabric: Side Pocket Fabric: Chest Pocket Fabric: Outer Layer | n=4
    (r"^lining:\s*pocket\s*lining$", "pocket_lining", "pocket_component"),  # raw=Lining: Pocket Lining | n=23
    (r"^lower\s*body:\s*pocket\s*lining$", "pocket_lining", "pocket_component"),  # raw=Lower Body: Pocket Lining | n=1
    (r"^pocket\s*lining:\s*inner\s*layer$", "pocket_lining", "pocket_component"),  # raw=Pocket Lining: Inner Layer | n=109
    (r"^pocket\s*lining:\s*inner\s*layer:\s*base$", "pocket_lining", "pocket_component"),  # raw=Pocket Lining: Inner Layer: Base | n=2
    (r"^pocket\s*lining:\s*inner\s*layer:\s*face$", "pocket_lining", "pocket_component"),  # raw=Pocket Lining: Inner Layer: Face | n=6
    (r"^pocket\s*lining:\s*mesh$", "pocket_lining", "pocket_component"),  # raw=Pocket Lining: Mesh | n=22
    (r"^pocket\s*lining:\s*other\s*fabric$", "pocket_lining", "pocket_component"),  # raw=Pocket Lining: Other Fabric | n=15
    (r"^pocket\s*lining:\s*outer\s*layer$", "pocket_lining", "pocket_component"),  # raw=Pocket Lining: Outer Layer | n=167
    (r"^pocket\s*lining:\s*trim$", "pocket_lining", "pocket_component"),  # raw=Pocket Lining: Trim | n=11
    (r"^side\s*pocket\s*fabric:\s*inner\s*layer$", "pocket_fabric", "pocket_component"),  # raw=Side Pocket Fabric: Inner Layer | n=20
    (r"^side\s*pocket\s*fabric:\s*mesh$", "pocket_fabric", "pocket_component"),  # raw=Side Pocket Fabric: Mesh | n=2
    (r"^side\s*pocket\s*fabric:\s*other\s*fabric$", "pocket_fabric", "pocket_component"),  # raw=Side Pocket Fabric: Other Fabric | n=3
    (r"^side\s*pocket\s*fabric:\s*outer\s*layer$", "pocket_fabric", "pocket_component"),  # raw=Side Pocket Fabric: Outer Layer | n=17
    (r"^side\s*pocket\s*fabric:\s*outer\s*layer:\s*inner\s*pocket\s*fabric:\s*chest\s*pocket\s*fabric$", "chest_pocket_fabric", "pocket_component"),  # raw=Side Pocket Fabric: Outer Layer: Inner Pocket Fabric: Chest Pocket Fabric | n=3
    (r"^side\s*pocket\s*fabric:\s*trim$", "pocket_fabric", "pocket_component"),  # raw=Side Pocket Fabric: Trim | n=2
    (r"^pocket$", "pocket", "pocket_component"),  # raw=Pocket | n=187
    (r"^inner\s*pocket\s*fabric$", "pocket_fabric", "pocket_component"),  # raw=Inner Pocket Fabric | n=28
    (r"^side\s*pocket\s*fabric$", "pocket_fabric", "pocket_component"),  # raw=Side Pocket Fabric | n=50
    (r"^pocket\s*lining$", "pocket_lining", "pocket_component"),  # raw=Pocket lining / Pocket Lining | n=3993

    # --------------------------------------------------
    # 4. trim_component
    # --------------------------------------------------
    (r"^collar:\s*face$", "collar", "trim_component"),  # raw=Collar: Face | n=17
    (r"^collar:\s*trim:\s*cuff:\s*trim$", "collar", "trim_component"),  # raw=Collar: Trim: Cuff: Trim | n=3
    (r"^lace:\s*waist$", "waist", "trim_component"),  # raw=Lace: Waist | n=12
    (r"^binder\-processed\s*part$", "binder_part", "trim_component"),  # raw=Binder-processed Part | n=100
    (r"^collar$", "collar", "trim_component"),  # raw=Collar | n=159
    (r"^cuff$", "cuff", "trim_component"),  # raw=Cuff | n=100
    (r"^elastic\s*part$", "elastic_part", "trim_component"),  # raw=Elastic Part | n=87
    (r"^flock\s*part$", "flock_part", "trim_component"),  # raw=Flock Part | n=6
    (r"^hem$", "hem", "trim_component"),  # raw=Hem | n=24
    (r"^cup\s*lace$", "lace", "trim_component"),  # raw=Cup lace | n=4
    (r"^lace$", "lace", "trim_component"),  # raw=Lace | n=514
    (r"^piping$", "piping", "trim_component"),  # raw=Piping | n=9
    (r"^elastic\s*rib$", "rib", "trim_component"),  # raw=Elastic rib | n=18
    (r"^rib$", "rib", "trim_component"),  # raw=Rib | n=1043
    (r"^ribbed$", "rib", "trim_component"),  # raw=Ribbed | n=2
    (r"^ribbed\s*pattern$", "rib", "trim_component"),  # raw=Ribbed Pattern | n=6
    (r"^shirring\s*part$", "shirring_part", "trim_component"),  # raw=Shirring Part | n=3
    (r"^tape$", "tape", "trim_component"),  # raw=Tape | n=77
    (r"^trim$", "trim", "trim_component"),  # raw=Trim | n=36
    (r"^waist$", "waist", "trim_component"),  # raw=Waist | n=351
    (r"^belt$", "belt", "trim_component"),  # raw=Belt | n=2
    (r"^belts$", "belt", "trim_component"),  # raw=Belts | n=41
    (r"^elastic$", "elastic", "trim_component"),  # raw=Elastic | n=15
    (r"^elastic\s*ribs$", "elastic ribs", "trim_component"),  # raw=Elastic ribs | n=1
    (r"^binding$", "binding", "trim_component"),  # raw=Binding | n=29
    (r"^strap$", "strap", "trim_component"),  # raw=Strap | n=11

    # --------------------------------------------------
    # 5. panel_component
    # --------------------------------------------------
    (r"^collar:\s*hood\s*edge$", "hood_edge", "panel_component"),  # raw=Collar: Hood Edge | n=6
    (r"^mesh:\s*hood$", "hood", "panel_component"),  # raw=Mesh: Hood | n=11
    (r"^sides\s*of\s*the\s*item:\s*under\s*sleeve$", "sleeve", "panel_component"),  # raw=Sides of The Item: Under Sleeve | n=3
    (r"^back$", "back_panel", "panel_component"),  # raw=Back | n=210
    (r"^bottom$", "bottom_panel", "panel_component"),  # raw=Bottom | n=114
    (r"^bottoms$", "bottom_panel", "panel_component"),  # raw=Bottoms | n=25
    (r"^bottom\s*part$", "bottom_panel", "panel_component"),  # raw=Bottom part | n=181
    (r"^front$", "front_panel", "panel_component"),  # raw=Front | n=120
    (r"^hood$", "hood", "panel_component"),  # raw=Hood | n=21
    (r"^hood\s*edge$", "hood", "panel_component"),  # raw=Hood Edge | n=10
    (r"^knit$", "knit_part", "panel_component"),  # raw=Knit | n=4
    (r"^knitted\s*part$", "knit_part", "panel_component"),  # raw=Knitted part | n=18
    (r"^plain$", "panel", "panel_component"),  # raw=Plain | n=17
    (r"^side$", "side_panel", "panel_component"),  # raw=Side | n=4
    (r"^side\s*part$", "side_panel", "panel_component"),  # raw=Side part | n=13
    (r"^skirt$", "skirt", "panel_component"),  # raw=Skirt | n=6
    (r"^sleeve$", "sleeve", "panel_component"),  # raw=Sleeve | n=7
    (r"^sleeve\s*panel$", "sleeve", "panel_component"),  # raw=Sleeve panel | n=1
    (r"^top$", "top_panel", "panel_component"),  # raw=Top | n=202
    (r"^tops$", "top_panel", "panel_component"),  # raw=Tops | n=20
    (r"^woven$", "woven_part", "panel_component"),  # raw=Woven | n=1
    (r"^woven\s*part$", "woven_part", "panel_component"),  # raw=Woven part | n=27
    (r"^crotch$", "crotch", "panel_component"),  # raw=Crotch | n=170
    (r"^elastic\s*section$", "elastic section", "panel_component"),  # raw=Elastic section | n=5
    (r"^inside\s*panel$", "inside_panel", "panel_component"),  # raw=Inside panel | n=15
    (r"^sleeves$", "sleeves", "panel_component"),  # raw=Sleeves | n=42
    (r"^lower$", "lower", "panel_component"),  # raw=Lower | n=3
    (r"^upper$", "upper", "panel_component"),  # raw=Upper | n=3
    (r"^panel$", "panel", "panel_component"),  # raw=Panel | n=6
    (r"^panels$", "panels", "panel_component"),  # raw=Panels | n=4
    (r"^upper\s*part$", "upper_part", "panel_component"),  # raw=Upper part | n=17
    (r"^wing$", "wing", "panel_component"),  # raw=Wing | n=62


    # --------------------------------------------------
    # 6. filling_component
    # --------------------------------------------------
    (r"^filling:\s*under\s*body$", "under_body_filling", "filling_component"),  # raw=Filling: Under Body | n=4
    (r"^filling:\s*upper\s*body$", "upper_body_filling", "filling_component"),  # raw=Filling: Upper Body | n=7
    (r"^filling:\s*body$", "body_filling", "filling_component"),  # raw=Filling: Body | n=62
    (r"^filling$", "filling", "filling_component"),  # raw=Filling | n=157
    (r"^padding$", "padding", "filling_component"),  # raw=Padding | n=646

    # --------------------------------------------------
    # 7. decoration_component
    # --------------------------------------------------
    (r"^application$", "application", "decoration_component"),  # raw=Application | n=6
    (r"^decorating\s*thread$", "decorating_thread", "decoration_component"),  # raw=Decorating Thread | n=2
    (r"^faux\s*fur$", "faux_fur", "decoration_component"),  # raw=Faux Fur | n=3
    (r"^allover\s*design$", "pattern_area", "decoration_component"),  # raw=Allover Design | n=1
    (r"^allover\s*pattern$", "pattern_area", "decoration_component"),  # raw=Allover Pattern | n=8
    (r"^animal\s*patterns$", "pattern_area", "decoration_component"),  # raw=Animal Patterns | n=4
    (r"^dot$", "pattern_area", "decoration_component"),  # raw=Dot | n=1
    (r"^dot\s*pattern$", "pattern_area", "decoration_component"),  # raw=Dot Pattern | n=2
    (r"^floral\s*pattern$", "pattern_area", "decoration_component"),  # raw=Floral Pattern | n=2
    (r"^hearts$", "pattern_area", "decoration_component"),  # raw=Hearts | n=2
    (r"^herringbone\s*pattern$", "pattern_area", "decoration_component"),  # raw=Herringbone Pattern | n=6
    (r"^jacquard\s*pattern$", "pattern_area", "decoration_component"),  # raw=Jacquard Pattern | n=2
    (r"^placement\s*design$", "pattern_area", "decoration_component"),  # raw=Placement Design | n=3
    (r"^star\s*pattern$", "pattern_area", "decoration_component"),  # raw=Star Pattern | n=4
    (r"^stripe$", "pattern_area", "decoration_component"),  # raw=Stripe | n=1
    (r"^stripe\s*pattern$", "pattern_area", "decoration_component"),  # raw=Stripe Pattern | n=2
    (r"^waffle\s*pattern$", "pattern_area", "decoration_component"),  # raw=Waffle Pattern | n=6
    (r"^embroidery$", "embroidery", "decoration_component"),  # raw=Embroidery | n=85
    (r"^tulle$", "tulle", "decoration_component"),  # raw=Tulle | n=15
    (r"^frill$", "frill", "decoration_component"),  # raw=Frill | n=15
    (r"^fringe$", "fringe", "decoration_component"),  # raw=Fringe | n=5

    # --------------------------------------------------
    # 8. other_component
    # remaining reviewed leftovers
    # --------------------------------------------------
    (r"^brown:\s*navy$", "brown: navy", "other_component"),  # raw=Brown: Navy | n=1
    (r"^green$", "green", "other_component"),  # raw=Green | n=1
    (r"^mesh$", "mesh", "other_component"),  # raw=Mesh | n=194
    (r"^middle\s*layer$", "middle layer", "other_component"),  # raw=Middle layer | n=12
    (r"^other$", "other", "other_component"),  # raw=Other | n=37
    (r"^other\s*fabric$", "other fabric", "other_component"),  # raw=Other Fabric | n=15
    (r"^sock$", "sock", "other_component"),  # raw=Sock | n=4
    (r"^net$", "net", "other_component"),  # raw=Net | n=4
    (r"^inner$", "inner_support", "other_component"),  # raw=Inner | n=21
    (r"^detail$", "detail", "other_component"),  # raw=Detail | n=1
    (r"^details$", "details", "other_component"),  # raw=Details | n=73
    (r"^body:\s*storage\s*bag$", "storage_bag", "other_component"),  # raw=Body: Storage Bag | n=4
    (r"^lining:\s*storage\s*bag$", "storage_bag", "other_component"),  # raw=Lining: Storage Bag | n=3
    (r"^storage\s*bag$", "storage_bag", "other_component"),  # raw=Storage Bag | n=2
]
#%% Parsing helpers

def is_drop_line(text):
    t = str(text).strip().lower()

    if t in DROP_EXACT:
        return True

    if re.fullmatch(r"[-–—]+", t):
        return True

    for s in DROP_CONTAINS:
        if s in t:
            return True

    return False


def split_component_blocks(text):
    """
    Split on / or ; only when followed by a new component header.
    """
    text = str(text).strip()

    parts = re.split(
        r"\s*(?:/|;)\s*(?=[A-Z][A-Za-z0-9\s\-&()]+:\s*)",
        text
    )

    return [p.strip(" ;") for p in parts if p.strip(" ;")]


def split_component_and_rest(block):
    """
    Use the last colon before the first percentage.
    This preserves nested paths such as:
        Collar: Face: 100% cotton
        Lining: Checks Pattern: 65% polyester, 35% cotton
    """
    block = str(block).strip()

    pct_match = RE_PERCENT.search(block)
    if not pct_match:
        return "main", block

    pct_pos = pct_match.start()
    colon_positions = [m.start() for m in re.finditer(r":", block[:pct_pos])]

    if not colon_positions:
        return "main", block

    split_pos = colon_positions[-1]
    component = block[:split_pos].strip(" :")
    rest = block[split_pos + 1:].strip()

    if not component:
        component = "main"

    return component, rest


def extract_materials_from_normalized_text(text):
    """
    Extract percentage-material pairs structurally, while preserving recycled
    information inside each material entry as:
        {"material": ..., "pct": ..., "recycled_pct": ...}

    recycled_pct:
    - 100.0 for forms like "70% polyester - Recycled Fiber"
    - X for forms like "(40% Made From Recycled polyester)"
    - None if no recycled information is attached
    """
    text = str(text)

    # ----------------------------------------
    # 1) capture parenthetical recycled notes first
    # ----------------------------------------
    recycled_notes = []
    for m in RE_RECYCLED_NOTE.finditer(text):
        recycled_pct = float(m.group(1))
        recycled_mat = re.sub(r"\s+", " ", m.group(2)).strip().lower()
        recycled_notes.append({
            "recycled_pct": recycled_pct,
            "material": recycled_mat
        })

    # remove parenthetical recycled notes before normal base parsing
    text_clean = RE_RECYCLED_NOTE.sub("", text)

    # keep hyphen " - Recycled Fiber" for now, because it helps identify
    # which material token is fully recycled
    text_clean = re.sub(r"\s+", " ", text_clean).strip()

    # ----------------------------------------
    # 2) collect pct-material matches in order
    # ----------------------------------------
    matches = []

    for m in RE_PCT_BEFORE.finditer(text_clean):
        pct = float(m.group(1))
        mat = re.sub(r"\s+", " ", m.group(2)).strip().lower()
        matches.append((m.start(), pct, mat))

    for m in RE_PCT_AFTER.finditer(text_clean):
        pct = float(m.group(2))
        mat = re.sub(r"\s+", " ", m.group(1)).strip().lower()
        matches.append((m.start(), pct, mat))

    if not matches:
        return []

    matches.sort(key=lambda x: x[0])

    # ----------------------------------------
    # 3) build token-level material entries
    #    do NOT merge same materials, so recycled splits are preserved
    # ----------------------------------------
    materials = []

    for _, pct, mat_raw in matches:
        recycled_pct = None

        # hyphen form: "polyester - Recycled Fiber"
        if re.search(r"\s*-\s*recycled(?:\s+fiber)?\s*$", mat_raw, flags=re.I):
            recycled_pct = 100.0
            mat_raw = re.sub(r"\s*-\s*recycled(?:\s+fiber)?\s*$", "", mat_raw, flags=re.I).strip()

        mat = re.sub(r"\s+", " ", mat_raw).strip().lower()

        if not mat:
            continue

        materials.append({
            "material": mat,
            "pct": pct,
            "recycled_pct": recycled_pct
        })

    if not materials:
        return []

    # ----------------------------------------
    # 4) attach parenthetical recycled notes, if possible
    #    Example:
    #    "100% polyester (40% Made From Recycled polyester)"
    #    -> {"material": "polyester", "pct": 100.0, "recycled_pct": 40.0}
    # ----------------------------------------
    for note in recycled_notes:
        note_mat = note["material"]
        note_pct = note["recycled_pct"]

        # try exact material match first
        assigned = False
        for item in materials:
            if item["material"] == note_mat and item["recycled_pct"] is None:
                item["recycled_pct"] = note_pct
                assigned = True
                break

        # fallback: if only one material entry exists, attach note there
        if not assigned and len(materials) == 1 and materials[0]["recycled_pct"] is None:
            materials[0]["recycled_pct"] = note_pct

    return materials

#%% Main

line_count = 0
written_count = 0
bad_json = 0
matched_pattern = None

component_class_counter = Counter()
component_name_counter = Counter()
raw_component_counter = Counter()
status_counter = Counter()

component_norm_source_counter = Counter()
unmatched_raw_component_counter = Counter()
matched_exact_pattern_counter = Counter()

n_scope_skipped = 0
n_missing_material_text = 0
n_blocks_over_100 = 0
n_rows_dropped_over_100 = 0

with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
    for line_no, line in enumerate(fin, start=1):
        line = line.strip()
        if not line:
            continue

        line_count += 1

        try:
            rec = json.loads(line)
        except Exception:
            bad_json += 1
            continue

        out = dict(rec)
        out["components_structured"] = []

        parent_category = str(rec.get("parent_category") or "").strip().lower()
        if parent_category in ["footwear", "accessories"]:
            # out-of-scope rows are counted in the summary but not written
            status_counter["skipped_scope"] += 1
            n_scope_skipped += 1
            continue

        raw_text = rec.get("raw_material_text_norm")

        if not raw_text:
            status_counter["no_material_text"] += 1
            n_missing_material_text += 1
            continue

        text = str(raw_text).replace("：", ":")
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\bCAUTION:\s*KEEP AWAY FROM HEAT AND FLAME\.?\s*$", "", text, flags=re.I).strip()

        components_structured = []
        row_has_over_100 = False

        for block in split_component_blocks(text):
            if not block or is_drop_line(block):
                continue

            component, rest = split_component_and_rest(block)
            mats = extract_materials_from_normalized_text(rest)

            if not mats:
                continue

            raw_component = str(component).strip().lower()
            raw_component = raw_component.replace("：", ":")
            raw_component = re.sub(r"\s+", " ", raw_component).strip(" :;/")

            component_name_norm = raw_component if raw_component else "main"
            component_class = "other_component"
            component_norm_source = "unmatched"
            matched_pattern = None

            for pat, norm_name, norm_class in PAT_COMPONENT_PATH_EXACT:
                if re.search(pat, raw_component, flags=re.I):
                    component_name_norm = norm_name
                    component_class = norm_class
                    component_norm_source = "exact_rule"
                    matched_pattern = pat
                    
                    break

            pct_sum = sum(x["pct"] for x in mats)
            pct_sum_flag = "over_100" if pct_sum > 102 else "ok"

            if pct_sum_flag == "over_100":
                n_blocks_over_100 += 1
                row_has_over_100 = True

            components_structured.append({
                "component_path_raw": component,
                "component_name_norm": component_name_norm,
                "component_class": component_class,
                "component_norm_source": component_norm_source,
                "materials": mats,
                "pct_sum": pct_sum,
                "pct_sum_flag": pct_sum_flag,
                "raw_text": block
            })

            raw_component_counter[component] += 1
            component_name_counter[component_name_norm] += 1
            component_class_counter[component_class] += 1

            component_norm_source_counter[component_norm_source] += 1
            if component_norm_source == "unmatched":
                unmatched_raw_component_counter[component] += 1
            elif component_norm_source == "exact_rule":
                if matched_pattern is not None:
                    matched_exact_pattern_counter[matched_pattern] += 1
        
        out["components_structured"] = components_structured
        
        if row_has_over_100:
            status_counter["dropped_over_100"] += 1
            n_rows_dropped_over_100 += 1
            continue

        if components_structured:
            status_counter["parsed"] += 1
        else:
            status_counter["parsed_no_components"] += 1

        fout.write(json.dumps(out, ensure_ascii=False) + "\n")
        written_count += 1
#%% Export normalized component-name summary table

component_name_summary_file = "6_component_name_summary_table.csv"

component_name_rows = []

for component_name, count in component_name_counter.most_common():
    # find component class for this normalized name from the rule list
    classes = sorted({
        norm_class
        for _pattern, norm_name, norm_class in PAT_COMPONENT_PATH_EXACT
        if norm_name == component_name
    })

    component_name_rows.append({
        "component_name_norm": component_name,
        "component_class": " ; ".join(classes) if classes else "unmatched",
        "matched_count": count,
    })

df_component_name_summary = pd.DataFrame(component_name_rows)
df_component_name_summary.to_csv(
    component_name_summary_file,
    index=False,
    encoding="utf-8-sig"
)
#%% Export rule mapping table (inline, via DataFrame)

rule_table_file = "6_component_rule_mapping_table.csv"

rule_rows = []
for pattern, norm_name, component_class in PAT_COMPONENT_PATH_EXACT:
    readable_rule = str(pattern)

    # remove anchors
    readable_rule = readable_rule.replace("^", "").replace("$", "")

    # simplify common regex tokens
    readable_rule = readable_rule.replace(r"\s*", " ")
    readable_rule = readable_rule.replace(r"\s+", " ")
    readable_rule = readable_rule.replace(r"\-", "-")

    # light cleanup for readability
    readable_rule = readable_rule.replace("(?:", "(")
    readable_rule = readable_rule.replace("?:", "")
    readable_rule = readable_rule.replace(")?", "")

    # normalize spaces
    readable_rule = re.sub(r"\s+", " ", readable_rule).strip()

    # tidy punctuation spacing
    readable_rule = re.sub(r"\s*:\s*", ": ", readable_rule)
    readable_rule = re.sub(r"\s*\(\s*", " (", readable_rule)
    readable_rule = re.sub(r"\s*\)\s*", ")", readable_rule)
    readable_rule = re.sub(r"\s+", " ", readable_rule).strip(" ;,")

    rule_rows.append({
        "regex_pattern": pattern,
        "readable_rule": readable_rule,
        "component_name_norm": norm_name,
        "component_class": component_class,
        "matched_count": matched_exact_pattern_counter.get(pattern, 0),
    })

df_rule_table = pd.DataFrame(rule_rows)
df_rule_table.to_csv(rule_table_file, index=False, encoding="utf-8-sig")

print("Finished.")
print(f"Output file: {output_file}")
print(f"Summary file: {summary_file}")
print(f"Component-name summary table file: {component_name_summary_file}")
print(f"Component rule mapping table file: {rule_table_file}")
#%% Summary

with open(summary_file, "w", encoding="utf-8") as fsum:
    fsum.write("JSONL component normalization summary\n\n")
    fsum.write(f"Input file: {input_file}\n")
    fsum.write(f"Output file: {output_file}\n")
    fsum.write(f"Component-name summary table file: {component_name_summary_file}\n")
    fsum.write(f"Component rule mapping table file: {rule_table_file}\n\n")

    # --------------------------------------------------
    # Row-level filtering summary first
    # --------------------------------------------------
    fsum.write("Row filtering summary\n")
    fsum.write("=" * 60 + "\n")
    fsum.write(f"Processed non-empty input lines: {line_count}\n")
    fsum.write(f"Bad JSON lines skipped: {bad_json}\n")
    fsum.write(f"Dropped rows: skipped_scope = {n_scope_skipped}\n")
    fsum.write(f"Dropped rows: no_material_text = {n_missing_material_text}\n")
    fsum.write(f"Dropped rows: over_100 = {n_rows_dropped_over_100}\n")
    fsum.write(f"Blocks with pct_sum > 102: {n_blocks_over_100}\n")
    fsum.write(f"Final written JSON lines: {written_count}\n")

    total_row_dropped = bad_json + n_scope_skipped + n_missing_material_text + n_rows_dropped_over_100
    fsum.write(f"Total removed before final output: {total_row_dropped}\n")

    # optional consistency check
    expected_final = line_count - bad_json - n_scope_skipped - n_missing_material_text - n_rows_dropped_over_100
    fsum.write(f"Consistency check (expected final lines): {expected_final}\n")

    # --------------------------------------------------
    # Status counts after row filtering
    # --------------------------------------------------
    fsum.write("\nStatus counts (kept + dropped-status logic)\n")
    fsum.write("=" * 60 + "\n")
    for k, v in status_counter.most_common():
        fsum.write(f"{k}: {v}\n")

    # --------------------------------------------------
    # Component-level summary for retained rows
    # --------------------------------------------------
    total_component_count = sum(component_class_counter.values())

    fsum.write("\nComponent summary for retained rows\n")
    fsum.write("=" * 60 + "\n")
    fsum.write(f"Total component occurrences: {total_component_count}\n")

    fsum.write("\nComponent class counts\n")
    fsum.write("-" * 60 + "\n")
    for k, v in component_class_counter.most_common():
        fsum.write(f"{k}: {v}\n")

    fsum.write("\nNormalized component name counts\n")
    fsum.write("-" * 60 + "\n")
    for k, v in component_name_counter.most_common():
        fsum.write(f"{k}: {v}\n")

    fsum.write("\nTop raw component paths\n")
    fsum.write("-" * 60 + "\n")
    for k, v in raw_component_counter.most_common():
        fsum.write(f"{k}: {v}\n")

    fsum.write("\nComponent normalization source counts\n")
    fsum.write("-" * 60 + "\n")
    for k, v in component_norm_source_counter.most_common():
        fsum.write(f"{k}: {v}\n")

    fsum.write("\nUnmatched raw component paths\n")
    fsum.write("-" * 60 + "\n")
    if unmatched_raw_component_counter:
        fsum.write(f"Total unique unmatched raw component paths: {len(unmatched_raw_component_counter)}\n")
        fsum.write(f"Total unmatched component occurrences: {sum(unmatched_raw_component_counter.values())}\n\n")
        for k, v in unmatched_raw_component_counter.most_common():
            fsum.write(f"{k}: {v}\n")
    else:
        fsum.write("None\n")

    # --------------------------------------------------
    # Over-100 diagnostics
    # --------------------------------------------------
    fsum.write("\nOver-100 diagnostics\n")
    fsum.write("=" * 60 + "\n")
    fsum.write(f"Blocks with pct_sum > 102: {n_blocks_over_100}\n")
    fsum.write(f"Rows dropped due to over_100 blocks: {n_rows_dropped_over_100}\n")
