import json
from pathlib import Path
from collections import defaultdict

input_files = [
    # Uniqlo raw files
    r"uniqlo_JSONL_uk_20260324T190346Z.jsonl",
    r"uniqlo_JSONL_au_20260324T190106Z.jsonl",

    # H&M raw files
    r"hm_JSONL_au_men_20260326T092818Z.jsonl",
    r"hm_JSONL_au_women_20260326T092008Z.jsonl",
    r"hm_JSONL_au_kids_20260326T092954Z.jsonl",
    r"hm_JSONL_gb_men_20260326T092700Z.jsonl",
    r"hm_JSONL_gb_women_20260326T091410Z.jsonl",
    r"hm_JSONL_gb_kids_20260326T093523Z.jsonl",
]

summary_file = "1_JSONL_drop_empty_summary.txt"

stats = defaultdict(lambda: {
    "total": 0,
    "keep": 0,
    "drop": 0,
    "empty_material": 0,
    "empty_colour": 0,
    "empty_both": 0,
})

gender_counts = defaultdict(lambda: {
    "men": 0,
    "women": 0,
    "kids": 0,
    "other": 0,
})

output_paths = {
    ("hm", "au"): "hm_JSONL_au_cleaned.jsonl",
    ("hm", "gb"): "hm_JSONL_gb_cleaned.jsonl",
    ("uniqlo", "au"): "uniqlo_JSONL_au_cleaned.jsonl",
    ("uniqlo", "uk"): "uniqlo_JSONL_uk_cleaned.jsonl",
}

output_handles = {}

for key, path in output_paths.items():
    output_handles[key] = open(path, "w", encoding="utf-8")

try:
    for input_file in input_files:
        input_path = Path(input_file)
        parts = input_path.stem.lower().split("_")

        # examples:
        # hm_JSONL_au_men_20260326T092818Z
        # uniqlo_JSONL_uk_20260324T190346Z
        if len(parts) < 3:
            continue

        file_brand = parts[0]
        file_region = parts[2]
        key = (file_brand, file_region)

        if key not in output_handles:
            continue

        with open(input_path, "r", encoding="utf-8") as fin:
            for line_no, line in enumerate(fin, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    rec = json.loads(line)
                except Exception:
                    continue

                brand = rec.get("brand")

                # only keep rows matching the expected brand from filename
                if brand != file_brand:
                    continue

                # ------------------------------------------------------------
                # 1) count gender/section BEFORE empty-value dropping
                # ------------------------------------------------------------
                if brand == "hm":
                    section_text = rec.get("section")

                    if "women" in section_text:
                        gender_counts[key]["women"] += 1
                    elif "men" in section_text: 
                        gender_counts[key]["men"] += 1
                    elif "kids" in section_text or "baby" in section_text:
                        gender_counts[key]["kids"] += 1
                    else:
                        gender_counts[key]["other"] += 1

                elif brand == "uniqlo":
                    gender_text = rec.get("gender")
                    if "women" in gender_text:
                        gender_counts[key]["women"] += 1
                    elif "men" in gender_text: 
                        gender_counts[key]["men"] += 1
                    elif "baby" in gender_text or "kids" in gender_text:
                        gender_counts[key]["kids"] += 1
                    else:
                        gender_counts[key]["other"] += 1

                # ------------------------------------------------------------
                # 2) normal cleaning summary
                # ------------------------------------------------------------
                stats[key]["total"] += 1

                if brand == "hm":
                    material_empty = rec.get("material_sum") in [None, ""]
                    colour_empty = rec.get("colour_label") in [None, "", []]

                elif brand == "uniqlo":
                    material_empty = rec.get("fabric_details_raw") in [None, ""]
                    colour_empty = rec.get("colour_labels") in [None, "", []]

                else:
                    continue

                if material_empty:
                    stats[key]["empty_material"] += 1
                if colour_empty:
                    stats[key]["empty_colour"] += 1
                if material_empty and colour_empty:
                    stats[key]["empty_both"] += 1

                if material_empty or colour_empty:
                    stats[key]["drop"] += 1
                else:
                    stats[key]["keep"] += 1
                    output_handles[key].write(json.dumps(rec, ensure_ascii=False) + "\n")

finally:
    for f in output_handles.values():
        f.close()

with open(summary_file, "w", encoding="utf-8") as f:
    f.write("Raw data empty-key summary\n\n")
    f.write("Merged cleaned outputs by brand and region\n")
    f.write("=" * 60 + "\n\n")

    combined_total = 0
    combined_keep = 0
    combined_drop = 0

    for key in [("hm", "au"), ("hm", "gb"), ("uniqlo", "au"), ("uniqlo", "uk")]:
        s = stats[key]
        g = gender_counts[key]

        combined_total += s["total"]
        combined_keep += s["keep"]
        combined_drop += s["drop"]

        if key[0] == "hm":
            label = f"H&M - {key[1].upper()}"
            material_name = "material_sum"
            colour_name = "colour_label"
        else:
            label = f"Uniqlo - {key[1].upper()}"
            material_name = "fabric_details_raw"
            colour_name = "colour_labels"

        f.write(f"{label}\n")
        f.write(f"Output file: {output_paths[key]}\n")
        f.write("Original rows by gender/section (before dropping)\n")
        f.write(f"  Men: {g['men']}\n")
        f.write(f"  Women: {g['women']}\n")
        f.write(f"  Kids: {g['kids']}\n")
        f.write(f"  Other/unknown: {g['other']}\n")
        f.write(f"Original rows: {s['total']}\n")
        f.write(f"Dropped rows: {s['drop']}\n")
        f.write(f"Rows after dropping: {s['keep']}\n")
        f.write(f"Empty {material_name}: {s['empty_material']}\n")
        f.write(f"Empty {colour_name}: {s['empty_colour']}\n")
        f.write(f"Empty both keys: {s['empty_both']}\n\n")

    f.write("Combined total\n")
    f.write("=" * 60 + "\n")
    f.write(f"Original rows: {combined_total}\n")
    f.write(f"Dropped rows: {combined_drop}\n")
    f.write(f"Rows after dropping: {combined_keep}\n")

print("Finished.")
print(f"Summary file: {summary_file}")
print("Output cleaned merged files:")
for key in [("hm", "au"), ("hm", "gb"), ("uniqlo", "au"), ("uniqlo", "uk")]:
    print(f" - {output_paths[key]}")