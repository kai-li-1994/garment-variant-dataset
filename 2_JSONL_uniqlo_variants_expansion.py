import json
import re
from collections import Counter
"""
While product URLs were collected from retailer product-listing pages, 
a single scraped record did not always correspond to the unit of analysis 
used in this study. In particular, one record could still aggregate multiple 
colour variants of the same garment. Distinguishing these variants was 
necessary for two reasons. First, colour itself is relevant for textile 
sorting, especially in the context of near-infrared (NIR) sorting, where 
colour-related constraints may affect sorting performance. Second, material 
composition was not always constant across colour variants of the same nominal 
product. Although many products shared the same composition across colours, 
some showed subtle but relevant differences. For this reason, the unit of 
analysis adopted in the subsequent assessment was the colour-specific garment 
variant, rather than the original product URL or page-level product record.

The need for variant expansion differed by retailer. In H&M, colour variants 
were already separated at the URL-collection stage, because different colours 
were represented by distinct product-page URLs. In Uniqlo, however, a single 
product URL could aggregate several colour variants and, in some cases, 
multiple product IDs and multiple composition variants within the same raw 
fabric-details field. To convert these page-level records into variant-level 
observations, each Uniqlo record was expanded into one row per colour variant. 
Where no internal branching structure was detected in the raw material 
information, the same composition text was assigned to all listed colours. 
Where branching information was present, the script first isolated the segment 
corresponding to the relevant product ID and then assigned composition text to 
individual colours using the bracketed colour labels embedded in the raw field. 
Records for which no reliable colour-specific assignment could be established 
were excluded rather than inferred. This procedure ensured that all downstream
calculations were based on comparable variant-level observations, each 
representing one garment variant defined by retailer item, colour, and 
assigned material composition.
"""
RE_OPTION_HEADER = re.compile(
    r"""
    (
        \b\d{6}(?:\s*,\s*\d{6})*:\s*\[[^\]]+\]
        |
        \b\d{6}(?:\s*,\s*\d{6})*:
        |
        \[[^\]]+\]
    )
    """,
    re.X
)

RE_ID_HEADER = re.compile(r'\b\d{6}(?:\s*,\s*\d{6})*:')
RE_BRACKET = re.compile(r'\[[^\]]+\]')

SPLIT_OPTION_CLEANUPS = [
    r"^\s*this item ships with one of the below options\.?\s*(?:note that you cannot specify a preference at this time\.?\s*)?",
]

input_file = r"uniqlo_JSONL_uk_cleaned.jsonl"
output_file = input_file.replace(".jsonl", "_variants.jsonl")
summary_file = "2_"+ input_file.replace(".jsonl", "_variants_summary.txt")

n_total = 0
n_out = 0
n_expanded_before_drop = 0
n_dropped_unresolved = 0
assignment_counter = Counter()
dropped_counter = Counter()

with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
    for line_no, line in enumerate(fin, start=1):
        line = line.strip()
        if not line:
            continue

        try:
            rec = json.loads(line)
        except Exception:
            continue

        n_total += 1

        product_id = str(rec.get("id", "")).strip()
        colour_labels = rec.get("colour_labels", [])
        raw = str(rec.get("fabric_details_raw", "")).strip()

        # -----------------------------------
        # light cleanup only
        # -----------------------------------
        text = raw.replace("：", ":")
        for pat in SPLIT_OPTION_CLEANUPS:
            text = re.sub(pat, "", text, flags=re.I)

        text = re.sub(r"\s+", " ", text).strip()

        # Main Fabric, 100% Cotton  -> Main Fabric: 100% Cotton
        text = re.sub(r"\bMain Fabric,\s*(?=\d+(?:\.\d+)?%)", "Main Fabric: ", text, flags=re.I)

        # Pocket65% Polyester -> Pocket: 65% Polyester
        text = re.sub(r"\bPocket(?=\d+(?:\.\d+)?%)", "Pocket: ", text, flags=re.I)

        # Pocket Lining65% Polyester -> Pocket Lining: 65% Polyester
        text = re.sub(r"\bPocket Lining(?=\d+(?:\.\d+)?%)", "Pocket Lining: ", text, flags=re.I)

        # Body67% Polyester -> Body: 67% Polyester
        text = re.sub(r"\bBody(?=\d+(?:\.\d+)?%)", "Body: ", text, flags=re.I)
        
        half = len(text) // 2
        if len(text) % 2 == 0:
            left = text[:half].strip()
            right = text[half:].strip()
            if left.lower() == right.lower():
                text = left

        # ====================================================
        # CASE 1: no branching pattern -> split only by colour
        # ====================================================
        if not RE_OPTION_HEADER.search(text):
            for colour in colour_labels:
                new_rec = dict(rec)
                new_rec["raw_material_text"] = text
                new_rec["variant_colour"] = colour
                new_rec["composition_assignment_type"] = "shared_no_variants"
                new_rec["_src_line"] = line_no

                assignment_counter[new_rec["composition_assignment_type"]] += 1
                n_expanded_before_drop += 1

                fout.write(json.dumps(new_rec, ensure_ascii=False) + "\n")
                n_out += 1
            continue

        # ====================================================
        # CASE 2: pattern exists -> first ID start/end
        # ====================================================
        retained_text = text
        matched_id = False

        id_matches = list(RE_ID_HEADER.finditer(text))
        if id_matches:
            start_pos = None
            end_pos = len(text)

            for i, m in enumerate(id_matches):
                header = m.group(0)
                ids_in_header = [x.strip() for x in header[:-1].split(",")]

                if product_id in ids_in_header:
                    matched_id = True
                    start_pos = m.end()
                    if i + 1 < len(id_matches):
                        end_pos = id_matches[i + 1].start()
                    break

            if start_pos is not None:
                retained_text = text[start_pos:end_pos].strip()

        # ====================================================
        # Then colour start/end inside retained_text
        # ====================================================
        colour_map = {}
        bracket_matches = list(RE_BRACKET.finditer(retained_text))
        default_other_colours_text = None

        if bracket_matches:
            for i, m in enumerate(bracket_matches):
                bracket_tag = m.group(0).strip()
                start_pos = m.end()
                end_pos = bracket_matches[i + 1].start() if i + 1 < len(bracket_matches) else len(retained_text)
                chunk_text = retained_text[start_pos:end_pos].strip(" ;/")
                
                half = len(chunk_text) // 2
                if len(chunk_text) % 2 == 0:
                    left = chunk_text[:half].strip()
                    right = chunk_text[half:].strip()
                    if left.lower() == right.lower():
                        chunk_text = left

                inside = bracket_tag[1:-1].strip()
                tokens = [x.strip() for x in inside.split(",")]

                for tok in tokens:
                    tok_norm = tok.lower().replace("gray", "grey").strip()

                    if tok_norm in ["other colors", "other colours"]:
                        default_other_colours_text = chunk_text
                        continue

                    mm = re.match(r"^(\d{2})\s+(.+)$", tok)
                    if mm:
                        colour_name = mm.group(2).strip()
                    else:
                        colour_name = tok.strip()

                    key = colour_name.lower().replace("gray", "grey")
                    colour_map[key] = chunk_text

        # ====================================================
        # Output one row per colour
        # ====================================================
        for colour in colour_labels:
            new_rec = dict(rec)
            new_rec["variant_colour"] = colour
            new_rec["_src_line"] = line_no

            key = str(colour).strip().lower().replace("gray", "grey")

            if colour_map:
                if key in colour_map:
                    new_rec["raw_material_text"] = colour_map[key]
                    if matched_id:
                        new_rec["composition_assignment_type"] = "mapped_by_id_then_colour"
                    else:
                        new_rec["composition_assignment_type"] = "mapped_by_colour_only"

                elif default_other_colours_text is not None:
                    new_rec["raw_material_text"] = default_other_colours_text
                    new_rec["composition_assignment_type"] = "mapped_by_other_colours_default"

                else:
                    new_rec["raw_material_text"] = retained_text
                    new_rec["composition_assignment_type"] = "unresolved_colour_mapping"

            else:
                new_rec["raw_material_text"] = retained_text

                if matched_id:
                    new_rec["composition_assignment_type"] = "mapped_by_id_only"
                else:
                    new_rec["composition_assignment_type"] = "unresolved_mapping"

            assignment_type = new_rec["composition_assignment_type"]
            assignment_counter[assignment_type] += 1
            n_expanded_before_drop += 1

            # ------------------------------------------------
            # DROP unresolved cases instead of writing them
            # ------------------------------------------------
            if assignment_type in ["unresolved_colour_mapping", "unresolved_mapping"]:
                dropped_counter[assignment_type] += 1
                n_dropped_unresolved += 1
                continue

            fout.write(json.dumps(new_rec, ensure_ascii=False) + "\n")
            n_out += 1


print(f"Total Uniqlo checked: {n_total}")
print(f"Expanded rows before dropping unresolved: {n_expanded_before_drop}")
print(f"Dropped unresolved rows: {n_dropped_unresolved}")
print(f"Final output rows: {n_out}")
print(f"Output: {output_file}")

with open(summary_file, "w", encoding="utf-8") as fsum:
    fsum.write("Uniqlo variant expansion summary\n")
    fsum.write(f"Input file: {input_file}\n")
    fsum.write(f"Output file: {output_file}\n\n")

    fsum.write(f"Total Uniqlo checked: {n_total}\n")
    fsum.write(f"Expanded rows before dropping unresolved: {n_expanded_before_drop}\n")
    fsum.write(f"Dropped unresolved rows: {n_dropped_unresolved}\n")
    fsum.write(f"Final output rows: {n_out}\n\n")

    fsum.write("Counts by composition_assignment_type (before dropping unresolved):\n")
    for k in sorted(assignment_counter):
        fsum.write(f"{k}: {assignment_counter[k]}\n")

    fsum.write("\nDropped unresolved counts:\n")
    for k in ["unresolved_colour_mapping", "unresolved_mapping"]:
        fsum.write(f"{k}: {dropped_counter[k]}\n")

print(f"Summary: {summary_file}")