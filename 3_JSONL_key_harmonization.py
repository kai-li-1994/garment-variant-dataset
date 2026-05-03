# -*- coding: utf-8 -*-
"""
Harmonize H&M and Uniqlo JSONL records into one reduced schema.
This step only renames / keeps / drops keys.
Also writes a summary of input/output JSON line counts.
"""

import json

# input files
INPUT_FILES = [
    # Uniqlo expanded variant files
    r"uniqlo_JSONL_uk_cleaned_variants.jsonl",
    r"uniqlo_JSONL_au_cleaned_variants.jsonl",

    # H&M base-unit raw files
    r"hm_JSONL_au_cleaned.jsonl",
    r"hm_JSONL_gb_cleaned.jsonl",
]

output_file = r"3_JSONL_harmonized.jsonl"
summary_file = r"3_JSONL_harmonized_summary.txt"

# store file-level counts
file_stats = {}
for input_file in INPUT_FILES:
    file_stats[input_file] = {
        "raw_json_lines": 0,
        "written_json_lines": 0,
    }

total_written = 0

with open(output_file, "w", encoding="utf-8") as fout:
    for input_file in INPUT_FILES:
        print(f"Reading: {input_file}")

        with open(input_file, "r", encoding="utf-8") as fin:
            for line in fin:
                line = line.strip()
                if not line:
                    continue

                # count raw non-empty JSONL lines from this input file
                file_stats[input_file]["raw_json_lines"] += 1

                try:
                    rec = json.loads(line)
                except Exception:
                    continue

                brand = rec.get("brand")
                if brand not in ["hm", "uniqlo"]:
                    continue

                # default output format
                out = {
                    "parent_product_id": None,
                    "brand": None,
                    "region": None,
                    "url": None,
                    "url_collected_at": None,
                    "scraped_at": None,

                    "gender_section": None,
                    "raw_category": None,
                    "product_name": None,

                    "variant_colour": None,
                    "all_colour_labels": [],

                    "raw_material_text": None,
                    "raw_material_text_full": None,
                    "composition_assignment_type": None,

                    "raw_description_text": None,
                    "raw_function_text": None,

                    "rating": None,
                    "reviewCount": None,
                }

                # common fields
                out["parent_product_id"] = rec.get("id")
                out["brand"] = rec.get("brand")
                out["region"] = rec.get("region")
                out["url"] = rec.get("url")
                out["url_collected_at"] = rec.get("url_collected_at")
                out["scraped_at"] = rec.get("scraped_at")
                out["rating"] = rec.get("rating")
                out["reviewCount"] = rec.get("reviewCount")

                # H&M
                if brand == "hm":
                    out["gender_section"] = rec.get("section")
                    out["raw_category"] = rec.get("category")
                    out["product_name"] = rec.get("marketingName")

                    out["all_colour_labels"] = rec.get("colour_label", [])
                    colour_list = rec.get("colour_label", [])
                    out["variant_colour"] = colour_list[0] if colour_list else None

                    out["raw_material_text"] = rec.get("material_sum")
                    out["raw_material_text_full"] = rec.get("material_sum")
                    out["composition_assignment_type"] = "native_variant_hm"

                    out["raw_description_text"] = rec.get("description_all")

                    # collect all H&M product-attribute key-value pairs after "figure_urls"
                    raw_function_parts = []
                    seen_figure_urls = False

                    for k, v in rec.items():
                        if k == "figure_urls":
                            seen_figure_urls = True
                            continue

                        if not seen_figure_urls:
                            continue

                        if v not in [None, "", [], {}]:
                            raw_function_parts.append(f"{k}: {v}")

                    out["raw_function_text"] = " | ".join(raw_function_parts) if raw_function_parts else None

                # Uniqlo
                elif brand == "uniqlo":
                    out["gender_section"] = rec.get("gender")
                    out["raw_category"] = rec.get("category")
                    out["product_name"] = rec.get("marketingName")

                    out["all_colour_labels"] = rec.get("colour_labels", [])
                    out["variant_colour"] = rec.get("variant_colour")

                    out["raw_material_text"] = rec.get("raw_material_text")
                    out["raw_material_text_full"] = rec.get("fabric_details_raw")
                    out["composition_assignment_type"] = rec.get("composition_assignment_type")

                    features = rec.get("features", [])
                    details = rec.get("details", [])
                    desc_parts = []
                    if isinstance(features, list):
                        desc_parts.extend([str(x).strip() for x in features if str(x).strip()])
                    if isinstance(details, list):
                        desc_parts.extend([str(x).strip() for x in details if str(x).strip()])
                    out["raw_description_text"] = " | ".join(desc_parts) if desc_parts else None

                    function_details = rec.get("function_details")
                    if isinstance(function_details, dict):
                        func_parts = []
                        for k, v in function_details.items():
                            if k or v:
                                func_parts.append(f"{k}: {v}")
                        out["raw_function_text"] = " | ".join(func_parts) if func_parts else None
                    else:
                        out["raw_function_text"] = None

                fout.write(json.dumps(out, ensure_ascii=False) + "\n")
                file_stats[input_file]["written_json_lines"] += 1
                total_written += 1

# summary
with open(summary_file, "w", encoding="utf-8") as fsum:
    fsum.write("JSONL harmonization summary\n\n")
    fsum.write(f"Output file: {output_file}\n")
    fsum.write(f"Total JSON lines in final aggregated output: {total_written}\n\n")

    fsum.write("Counts by input file\n")
    fsum.write("=" * 60 + "\n")

    for input_file in INPUT_FILES:
        fsum.write(f"{input_file}\n")
        fsum.write(f"Raw JSON lines: {file_stats[input_file]['raw_json_lines']}\n")
        fsum.write(f"Written JSON lines to harmonized output: {file_stats[input_file]['written_json_lines']}\n\n")

print(f"\nDone. Output: {output_file}")
print(f"Summary: {summary_file}")