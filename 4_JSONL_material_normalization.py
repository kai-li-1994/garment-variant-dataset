# -*- coding: utf-8 -*-
"""
Material names were standardized by mapping different labels that refer to the
same material to a common term, for example nylon and polyamide, elastane and
spandex, or polyester and PES, so that materially equivalent inputs were
treated consistently in the subsequent analysis.
"""
import json
import re
from collections import Counter
import pandas as pd

input_file = r"3_JSONL_harmonized.jsonl"
output_file = r"4_JSONL_material_normalized.jsonl"
summary_file = r"4_JSONL_material_normalization_summary.txt"
mapping_table_file = r"4_material_normalization_table.csv"

# =====================================================
# Canonical material groups reused from parser logic
# =====================================================
CANON_GROUPS = {
    # synthetic textile fibres
    "nylon": ["nylon", "polyamide", "pa", "pa6", "pa66"],
    "polyester": ["polyester", "pes", "pet", "repreve"],
    "elastane": ["elastane", "spandex", "lycra"],
    "acrylic": ["acrylic"],
    "modacrylic": ["modacrylic"],
    "acetate": ["acetate", "naia"],
    "triacetate": ["triacetate"],
    "elastodiene": ["elastodiene"],
    "elastomultiester": ["elastomultiester"],
    "metallised_fibre": [
        "metallised fibre", "metallised fiber", "metalised fibre",
        "metalised fiber", "metallic fibre", "metallic fiber"
    ],

    # natural fibres
    "cotton": ["cotton", "supima"],
    "wool": ["wool", "merino", "merino wool"],
    "cashmere": ["cashmere"],
    "alpaca": ["alpaca"],
    "mohair": ["mohair"],
    "silk": ["silk"],
    "linen": ["linen", "flax"],
    "hemp": ["hemp"],
    "jute": ["jute"],
    "ramie": ["ramie"],

    # regenerated cellulose fibres
    "viscose": ["viscose", "rayon"],
    "modal": ["modal", "tencel modal"],
    "lyocell": ["lyocell", "tencel lyocell", "tencel"],
    "cupro": ["cupro"],
    "cellulose": ["cellulose"],

    # animal-derived materials
    "leather": [
        "genuine cowhide", "genuine leather", "cowhide", "goatskin",
        "sheepskin", "lambskin", "nappa", "leather"
    ],
    "suede": ["suede"],
    "down": ["down"],
    "feather": ["feather", "feathers"],

    # structural plastics, coatings, and foams
    "polyethylene": ["polyethylene", "pe", "epe"],
    "polypropylene": ["polypropylene", "pp"],
    "polyurethane": ["polyurethane", "pu"],
    "tpu": ["thermoplastic polyurethane", "tpu"],
    "tpe": ["thermoplastic elastomer", "tpe"],
    "eva": ["ethylene vinyl acetate", "eva"],
    "ptfe": ["ptfe"],
    "rubber": ["rubber"],
    "latex": ["latex"],
    "silicone": ["silicone"],
    "resin": ["resin"],
    "polycarbonate": ["polycarbonate", "pc"],
    "polystyrene": ["polystyrene"],
    "pbt": ["polybutylene terephthalate", "pbt"],
    "pctg": [
        "pctg",
        "polycyclohexylenedimethylene terephthalate",
        "polycyclohexylene dimethyl terephthalate glycol",
        "polycyclohexylene dimethylene terephthalate glycol",
        "poly cyclohexylene dimethylene terephthalate glycol",
    ],
    "abs": ["abs", "acrylonitrile-butadiene-styrene", "acrylonitrile butadiene styrene"],
    "mabs": ["methyl acrylate-butadiene-styrene", "methyl acrylate butadiene styrene", "mabs"],
    "pom": ["polyoxymethylene", "pom", "acetal"],
    "pmma": ["pmma", "polymethyl methacrylate"],

    # hardware or accessory materials
    "paper": ["paper"],
    "glass": ["glass", "fiberglass"],
    "pearl": ["fresh water pearl", "freshwater pearl", "pearl"],
    "steel": ["steel", "stainless steel"],
    "iron": ["iron"],
    "brass": ["brass"],
    "zinc": ["zinc"],
    "copper": ["copper"],
    "metal": ["metal"],
    "wax": ["wax"],

    # generic or unspecified materials
    "unspecified_material": [
        "other materials", "other material", "other fibres", "other fibers",
        "unspecified", "unknown", "synthetic"
    ],
    "textile": ["textile"],
}

CANON = {
    variant: canon
    for canon, variants in CANON_GROUPS.items()
    for variant in variants
}

CANON_KEYS = sorted(CANON.keys(), key=len, reverse=True)
CANON_PATTERNS = [
    (re.compile(r"\b" + re.escape(k) + r"\b", flags=re.I), CANON[k], k)
    for k in CANON_KEYS
]

MULTILINGUAL_ALIASES = {
    "katoen": "cotton",
    "elastaan": "elastane",
    "acryl": "acrylic",
}

# =====================================================
# Export material mapping table for documentation
# =====================================================
mapping_rows = []

for canon_name, raw_labels in CANON_GROUPS.items():
    mapping_rows.append({
        "mapping_type": "canonical_group",
        "canonical_material_name": canon_name,
        "raw_labels_joined": " ; ".join(raw_labels),
        "n_raw_labels": len(raw_labels),
    })

for alias, canon_name in MULTILINGUAL_ALIASES.items():
    mapping_rows.append({
        "mapping_type": "multilingual_alias",
        "canonical_material_name": canon_name,
        "raw_labels_joined": alias,
        "n_raw_labels": 1,
    })

mapping_df = pd.DataFrame(mapping_rows)
mapping_df.to_csv(mapping_table_file, index=False, encoding="utf-8-sig")

line_count = 0
written_count = 0
bad_json = 0
changed_raw_material_text = 0
brand_counter = Counter()

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

        brand_counter[str(rec.get("brand"))] += 1
        out = dict(rec)

        raw_material_text = rec.get("raw_material_text")

        if raw_material_text in [None, ""]:
            out["raw_material_text_norm"] = raw_material_text
        else:
            text = str(raw_material_text)

            for k, v in MULTILINGUAL_ALIASES.items():
                text = re.sub(r"\b" + re.escape(k) + r"\b", v, text, flags=re.I)

            for pattern, canon, raw_key in CANON_PATTERNS:
                text = pattern.sub(canon, text)

            out["raw_material_text_norm"] = text

        if rec.get("raw_material_text") not in [None, ""]:
            old_text = str(rec.get("raw_material_text"))
            new_text = str(out["raw_material_text_norm"])

            if old_text.lower() != new_text.lower():
                changed_raw_material_text += 1

        fout.write(json.dumps(out, ensure_ascii=False) + "\n")
        written_count += 1

with open(summary_file, "w", encoding="utf-8") as fsum:
    fsum.write("JSONL material normalization summary\n\n")
    fsum.write(f"Input file: {input_file}\n")
    fsum.write(f"Output file: {output_file}\n")
    fsum.write(f"Material mapping table file: {mapping_table_file}\n\n")

    fsum.write("Row processing summary\n")
    fsum.write("=" * 60 + "\n")
    fsum.write(f"Processed non-empty lines: {line_count}\n")
    fsum.write(f"Bad JSON lines skipped: {bad_json}\n")
    fsum.write(f"Written JSON lines: {written_count}\n\n")

    fsum.write("Brand counts\n")
    fsum.write("=" * 60 + "\n")
    for k in sorted(brand_counter):
        fsum.write(f"{k}: {brand_counter[k]}\n")

    fsum.write("\nNormalization changes\n")
    fsum.write("=" * 60 + "\n")
    fsum.write(f"Rows with changed raw_material_text_norm: {changed_raw_material_text}\n\n")

    fsum.write("Notes\n")
    fsum.write("=" * 60 + "\n")
    fsum.write("- raw_material_text is preserved unchanged.\n")
    fsum.write("- raw_material_text_full is preserved unchanged.\n")
    fsum.write("- raw_material_text_norm is added as a new normalized field.\n")
    fsum.write("- Material mapping table is exported directly from CANON_GROUPS and MULTILINGUAL_ALIASES.\n")

print(f"Done. Output: {output_file}")
print(f"Summary: {summary_file}")
print(f"Material mapping table: {mapping_table_file}")
