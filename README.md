# Harmonized garment-variant dataset for textile sorting and fibre-to-fibre recycling analysis

This repository contains a curated garment-variant dataset and preprocessing pipeline derived from publicly accessible online product pages of H&M and Uniqlo in the United Kingdom and Australia.

The dataset was developed to support garment-level analysis of textile sorting compatibility, preprocessing requirements, and potential barriers to fibre-to-fibre recycling. It provides harmonized information on product identifiers, retailer region, colour-specific variants, material composition, normalized material names, normalized garment categories, normalized component structures, and derived rule-based analytical inputs.

The final dataset file is:

```text
6_JSONL_component_normalized.jsonl
```

This file contains **47,522 colour-specific garment variants** and is the direct input used for the associated sorting and preprocessing/disruptor analyses.

## Repository purpose

This repository documents how raw retailer product-page records were transformed into a harmonized, analysis-ready garment dataset.

The repository is intended to support:

- automated textile sorting research;
- textile preprocessing and feedstock-preparation analysis;
- garment-level fibre composition analysis;
- analysis of garment components, linings, trims, and secondary structures;
- fibre-to-fibre recycling-barrier assessment;
- reproducible use of retailer web data for textile circularity research.

The repository provides a curated research dataset. It is **not** a redistribution or mirror of retailer webpages.

## Dataset overview

The data were collected from online product pages of two major fast-fashion retailers:

- H&M
- Uniqlo

The geographic scope covers retailer websites in:

- United Kingdom
- Australia

The dataset includes men’s, women’s, and children’s clothing. The analytical unit is the **colour-specific garment variant**, rather than the original product-page record.

This unit was chosen because colour, material composition, and product details can differ across variants of the same nominal product. These differences are relevant for sorting and recycling analysis, especially where colour or component-level composition influences the interpretation of a garment.

## Final dataset

The final processed dataset is:

```text
6_JSONL_component_normalized.jsonl
```

Each line is one JSON object representing one colour-specific garment variant.

The final dataset contains:

```text
47,522 garment-variant records
```

The final records include harmonized product metadata, normalized material text, normalized garment categories, and structured component-level composition information.

## Data-processing workflow

The dataset was produced through six sequential preprocessing steps:

1. minimum-information filtering;
2. Uniqlo colour-variant expansion;
3. cross-retailer schema harmonization;
4. material-name normalization;
5. category normalization and scope filtering;
6. component normalization and consistency filtering.

The scripts are numbered according to this workflow:

```text
1_JSONL_drop_empty_summary.py
2_JSONL_uniqlo_variants_expansion.py
3_JSONL_key_harmonization.py
4_JSONL_material_normalization.py
5_JSONL_category_normalization.py
6_JSONL_component_normalization.py
```

## Step 1: Minimum-information filtering

Raw product-page records were first filtered to retain only records with the minimum information required for downstream rule evaluation.

For H&M records, the required fields were:

```text
material_sum
colour_label
```

For Uniqlo records, the required fields were:

```text
fabric_details_raw
colour_labels
```

Records were removed if they lacked material information, colour information, or both.

The raw scraped dataset contained **47,834 product-page records**. After removing records with missing material or colour information, **47,570 records** remained.

Summary:

| Retailer-region | Original rows | Dropped rows | Rows after dropping |
|---|---:|---:|---:|
| H&M AU | 15,539 | 85 | 15,454 |
| H&M GB | 29,701 | 178 | 29,523 |
| Uniqlo AU | 1,104 | 1 | 1,103 |
| Uniqlo UK | 1,490 | 0 | 1,490 |
| **Total** | **47,834** | **264** | **47,570** |

## Step 2: Uniqlo colour-variant expansion

The analytical unit of this dataset is the colour-specific garment variant.

H&M records were already treated as colour-specific variants because colour variants were represented through product-page URLs. Uniqlo records required additional processing because one Uniqlo product page could contain multiple colour variants and, in some cases, variant-specific material composition.

The Uniqlo expansion script creates one row per colour variant.

Where no internal material-composition branching was detected, the same composition text was assigned to all listed colours. Where product-ID-specific or colour-specific branching was present in the raw material field, the script isolated the relevant segment and assigned it to the corresponding colour. Records for which no reliable assignment could be established were removed rather than inferred.

### Uniqlo UK

| Metric | Count |
|---|---:|
| Cleaned product-page records | 1,490 |
| Expanded rows before dropping unresolved cases | 3,952 |
| Dropped unresolved rows | 16 |
| Final variant rows | 3,936 |

### Uniqlo Australia

| Metric | Count |
|---|---:|
| Cleaned product-page records | 1,103 |
| Expanded rows before dropping unresolved cases | 3,088 |
| Dropped unresolved rows | 7 |
| Final variant rows | 3,081 |

### Composition-assignment types

The field `composition_assignment_type` records how material composition was assigned to each colour-specific variant.

| Value | Meaning |
|---|---|
| `native_variant_hm` | H&M record was already treated as a colour-specific variant through the product-page URL |
| `shared_no_variants` | No composition branching was detected; the same composition was assigned to all colour variants |
| `mapped_by_colour_only` | Composition was assigned using colour labels in the raw composition field |
| `mapped_by_id_only` | Composition was assigned using product-ID-specific information |
| `mapped_by_id_then_colour` | Product-ID-specific information was first isolated, then assigned by colour |
| `mapped_by_other_colours_default` | A default “other colours” composition segment was assigned |
| `unresolved_colour_mapping` | Colour-specific mapping could not be resolved; these rows were removed |
| `unresolved_mapping` | General mapping could not be resolved; these rows were removed |

## Step 3: Cross-retailer schema harmonization

Cleaned H&M records and expanded Uniqlo records were harmonized into a common JSONL schema.

This step renamed, retained, and dropped keys to align records across brands and regions. The harmonized schema includes product identifiers, brand, region, URL, timestamps, gender section, raw retailer category, product name, colour information, material-composition fields, description/function fields, and selected metadata.

The harmonized output is:

```text
3_JSONL_harmonized.jsonl
```

The harmonized dataset contained **51,994 variant-level records**.

| Input file | Written rows |
|---|---:|
| `uniqlo_JSONL_uk_cleaned_variants.jsonl` | 3,936 |
| `uniqlo_JSONL_au_cleaned_variants.jsonl` | 3,081 |
| `hm_JSONL_au_cleaned.jsonl` | 15,454 |
| `hm_JSONL_gb_cleaned.jsonl` | 29,523 |
| **Total** | **51,994** |

The increase from 47,570 cleaned product records to 51,994 harmonized variant-level records occurs because Uniqlo product-page records were expanded into colour-specific garment variants.

## Step 4: Material-name normalization

Material normalization was applied to the harmonized JSONL file.

The input file was:

```text
3_JSONL_harmonized.jsonl
```

The output file was:

```text
4_JSONL_material_normalized.jsonl
```

This step preserved the original material-composition fields and added a normalized material-text field:

```text
raw_material_text_norm
```

The original fields were retained unchanged:

```text
raw_material_text
raw_material_text_full
```

The material-normalization step processed **51,994 records** and wrote **51,994 records**. In total, **9,392 records** had changed normalized material text after material-name normalization.

Material names were normalized by replacing common synonyms, abbreviations, branded names, and analytically equivalent labels with canonical material names. The table below documents the mapping used in `CANON_GROUPS`.

| Canonical material name | Raw labels mapped to this name |
|---|---|
| `nylon` | `nylon`, `polyamide`, `pa`, `pa6`, `pa66` |
| `polyester` | `polyester`, `pes`, `pet`, `repreve` |
| `elastane` | `elastane`, `spandex`, `lycra` |
| `acrylic` | `acrylic` |
| `modacrylic` | `modacrylic` |
| `acetate` | `acetate`, `naia` |
| `triacetate` | `triacetate` |
| `elastodiene` | `elastodiene` |
| `elastomultiester` | `elastomultiester` |
| `metallised_fibre` | `metallised fibre`, `metallised fiber`, `metalised fibre`, `metalised fiber`, `metallic fibre`, `metallic fiber` |
| `cotton` | `cotton`, `supima` |
| `wool` | `wool`, `merino`, `merino wool` |
| `cashmere` | `cashmere` |
| `alpaca` | `alpaca` |
| `mohair` | `mohair` |
| `silk` | `silk` |
| `linen` | `linen`, `flax` |
| `hemp` | `hemp` |
| `jute` | `jute` |
| `ramie` | `ramie` |
| `viscose` | `viscose`, `rayon` |
| `modal` | `modal`, `tencel modal` |
| `lyocell` | `lyocell`, `tencel lyocell`, `tencel` |
| `cupro` | `cupro` |
| `cellulose` | `cellulose` |
| `leather` | `genuine cowhide`, `genuine leather`, `cowhide`, `goatskin`, `sheepskin`, `lambskin`, `nappa`, `leather` |
| `suede` | `suede` |
| `down` | `down` |
| `feather` | `feather`, `feathers` |
| `polyethylene` | `polyethylene`, `pe`, `epe` |
| `polypropylene` | `polypropylene`, `pp` |
| `polyurethane` | `polyurethane`, `pu` |
| `tpu` | `thermoplastic polyurethane`, `tpu` |
| `tpe` | `thermoplastic elastomer`, `tpe` |
| `eva` | `ethylene vinyl acetate`, `eva` |
| `ptfe` | `ptfe` |
| `rubber` | `rubber` |
| `latex` | `latex` |
| `silicone` | `silicone` |
| `resin` | `resin` |
| `polycarbonate` | `polycarbonate`, `pc` |
| `polystyrene` | `polystyrene` |
| `pbt` | `polybutylene terephthalate`, `pbt` |
| `pctg` | `pctg`, `polycyclohexylenedimethylene terephthalate`, `polycyclohexylene dimethyl terephthalate glycol`, `polycyclohexylene dimethylene terephthalate glycol`, `poly cyclohexylene dimethylene terephthalate glycol` |
| `abs` | `abs`, `acrylonitrile-butadiene-styrene`, `acrylonitrile butadiene styrene` |
| `mabs` | `methyl acrylate-butadiene-styrene`, `methyl acrylate butadiene styrene`, `mabs` |
| `pom` | `polyoxymethylene`, `pom`, `acetal` |
| `pmma` | `pmma`, `polymethyl methacrylate` |
| `paper` | `paper` |
| `glass` | `glass`, `fiberglass` |
| `pearl` | `fresh water pearl`, `freshwater pearl`, `pearl` |
| `steel` | `steel`, `stainless steel` |
| `iron` | `iron` |
| `brass` | `brass` |
| `zinc` | `zinc` |
| `copper` | `copper` |
| `metal` | `metal` |
| `wax` | `wax` |
| `unspecified_material` | `other materials`, `other material`, `other fibres`, `other fibers`, `unspecified`, `unknown`, `synthetic` |
| `textile` | `textile` |

The script also applies a small set of multilingual aliases before the main canonical mapping:

| Alias | Canonical material name |
|---|---|
| `katoen` | `cotton` |
| `elastaan` | `elastane` |
| `acryl` | `acrylic` |

The purpose of this step was to improve consistency for subsequent category, component, sorting-rule, and disruptor-rule analyses while preserving the original retailer-disclosed material text. Some brand-specific, qualified, or highly specific material labels may remain unchanged where no unambiguous mapping was applied.

## Step 5: Category normalization and scope filtering

Category normalization mapped retailer-specific category information into a harmonized two-level garment taxonomy.

The input file was:

```text
4_JSONL_material_normalized.jsonl
```

The output file was:

```text
5_JSONL_category_normalized.jsonl
```

The category-normalization procedure combined:

- retailer-native category information;
- product names;
- product descriptions where needed;
- sorting-oriented grouping logic.

Because H&M and Uniqlo used different category structures, field priority differed by brand. H&M mapping relied more strongly on detailed category breadcrumbs, whereas Uniqlo mapping relied more strongly on product names.

The output taxonomy contains:

```text
parent_category
detail_category
```

The full parent–detail category mapping is:

| Parent category | Detail categories |
|---|---|
| `tops` | `outerwear_coat`, `outerwear_jacket`, `outerwear_gilet`, `shirt_blouse`, `tshirt_polo`, `tank_camisole_vest`, `sweater_cardigan`, `sweatshirt_hoodie`, `top_generic` |
| `bottoms` | `jeans`, `trousers`, `leggings`, `joggers`, `shorts`, `skirts` |
| `underwear` | `underwear_bottoms`, `bras_lingerie`, `swimwear`, `socks_hosiery` |
| `overall` | `dresses`, `jumpsuits_overalls`, `sleepwear_homewear`, `set` |
| `footwear` | `footwear` |
| `accessories` | `accessories` |

Records assigned to `footwear`, `accessories`, or no resolved category were treated as out of scope for the garment-level sorting and preprocessing analyses and were removed from the exported category-normalized dataset.

Out-of-scope records were removed at this stage:

| Removed category | Count |
|---|---:|
| Accessories | 2,648 |
| Footwear | 1,087 |
| Unallocated | 15 |
| **Total removed** | **3,750** |

After category normalization and scope filtering, **48,244 garment-variant records** remained.

### Final parent-category counts after category filtering

| Parent category | Count |
|---|---:|
| `tops` | 22,185 |
| `bottoms` | 12,172 |
| `overall` | 7,836 |
| `underwear` | 6,051 |

## Step 6: Component normalization and consistency filtering

Component normalization parsed material-composition strings into structured component-level records.

The input file was:

```text
5_JSONL_category_normalized.jsonl
```

The output file was:

```text
6_JSONL_component_normalized.jsonl
```

This step does not redo material normalization. It uses the normalized material text field:

```text
raw_material_text_norm
```

The purpose of this step is to convert heterogeneous retailer composition strings into a structured component representation.

For example, composition strings may contain labels such as:

```text
Shell
Body
Main
Lining
Pocket lining
Collar
Cuff
Padding
Filling
Coating
Panel
```

These raw component labels are mapped to standardized component names and broader component classes.

### Component classes

The component taxonomy contains the following broad classes:

| Component class | Description |
|---|---|
| `surface_component` | Main visible or surface textile component, such as shell, body, main, face, coating |
| `lining_component` | Lining or concealed layer, such as lining, body lining, sleeve lining, hood lining, inner layer |
| `pocket_component` | Pocket-related material, such as pocket lining or pocket fabric |
| `trim_component` | Local trim or garment detail, such as collar, cuff, rib, lace, elastic part, tape |
| `panel_component` | Named panel or garment section, such as front panel, back panel, side panel, woven part |
| `filling_component` | Filling or padding material |
| `decoration_component` | Decorative textile or non-textile features such as embroidery, frill, fringe, faux fur |
| `other_component` | Residual component class for reviewed but less analytically specific components |

### Component-level structure

The field `components_structured` stores a list of parsed components. Each component entry contains:

| Field | Description |
|---|---|
| `component_path_raw` | Raw component label from the material-composition string |
| `component_name_norm` | Standardized component name |
| `component_class` | Broader component class |
| `component_norm_source` | Source of the component-normalization decision |
| `materials` | List of material entries for the component |
| `pct_sum` | Sum of reported material percentages for the component |
| `pct_sum_flag` | Percentage-sum consistency flag |
| `raw_text` | Component-level material-composition block |

Each entry in `materials` contains:

| Field | Description |
|---|---|
| `material` | Normalized material name |
| `pct` | Material percentage within the component |
| `recycled_pct` | Reported recycled-content percentage where available; otherwise null |

### Component-normalization filtering

During component normalization:

| Filtering reason | Count |
|---|---:|
| No usable material text | 4 |
| Component percentage sum above consistency threshold | 718 |
| **Total removed** | **722** |

After this step, the final dataset contained **47,522 records**.

### Component occurrence summary

The final dataset contains **68,427 component occurrences**.

| Component class | Count |
|---|---:|
| `surface_component` | 48,573 |
| `lining_component` | 9,621 |
| `pocket_component` | 4,786 |
| `trim_component` | 2,673 |
| `panel_component` | 1,348 |
| `filling_component` | 876 |
| `other_component` | 375 |
| `decoration_component` | 175 |

All retained component occurrences were matched by exact component-normalization rules.

## Dataset-size summary

| Step | Input records | Removed / unresolved records | Output records | Main purpose |
|---|---:|---:|---:|---|
| Raw scraped records | 47,834 | 264 removed | 47,570 | Remove records missing minimum material or colour information |
| Uniqlo AU colour-variant expansion | 1,103 cleaned Uniqlo AU records | 7 unresolved expanded rows | 3,081 variant rows | Convert Uniqlo AU records into colour-specific variants |
| Uniqlo UK colour-variant expansion | 1,490 cleaned Uniqlo UK records | 16 unresolved expanded rows | 3,936 variant rows | Convert Uniqlo UK records into colour-specific variants |
| Cross-retailer harmonization | 44,977 H&M records + 7,017 Uniqlo variant records | 0 | 51,994 | Align H&M and Uniqlo into a common schema |
| Material normalization | 51,994 | 0 | 51,994 | Add canonical material labels while preserving original material text |
| Category normalization and scope filtering | 51,994 | 3,750 removed | 48,244 | Assign harmonized garment categories and remove out-of-scope records |
| Component normalization and consistency filtering | 48,244 | 722 removed | 47,522 | Parse component-level composition and remove inconsistent records |
| Final analysis dataset | 47,522 | — | 47,522 | Direct input for sorting and preprocessing analyses |

## Key fields in the final dataset

| Field | Description |
|---|---|
| `parent_product_id` | Retailer product identifier for the parent product or product page |
| `brand` | Retailer brand, either `hm` or `uniqlo` |
| `region` | Retailer website region |
| `url` | Product-page URL used for provenance |
| `url_collected_at` | Timestamp when the product URL was collected |
| `scraped_at` | Timestamp when product details were scraped |
| `gender_section` | Retailer gender or section label |
| `raw_category` | Original retailer category information |
| `product_name` | Retailer product name |
| `variant_colour` | Colour label of the garment variant |
| `all_colour_labels` | All colour labels listed for the product |
| `raw_material_text` | Material-composition text assigned to the variant |
| `raw_material_text_full` | Full raw material-composition text from the source record |
| `composition_assignment_type` | Method used to assign composition information to the colour variant |
| `raw_description_text` | Retailer-facing product description text retained in the working schema where available |
| `raw_function_text` | Retailer-facing structured function or attribute text where available |
| `rating` | Retailer-disclosed product rating where available |
| `reviewCount` | Retailer-disclosed review count where available |
| `raw_material_text_norm` | Material-composition text after material-name normalization |
| `detail_category` | Harmonized detailed garment category |
| `detail_rule_source` | Field source used for category-rule assignment |
| `detail_rule_hit` | Category rule that triggered the detail-category assignment |
| `parent_category` | Harmonized parent garment category |
| `components_structured` | Parsed and normalized component-level material-composition records |

## Relationship to sorting and preprocessing analyses

The final file:

```text
6_JSONL_component_normalized.jsonl
```

is the shared empirical input for two related analyses.

The sorting-compatibility analysis uses normalized material, colour, category, and component fields to evaluate sorting-relevant barriers.

The preprocessing/disruptor analysis uses the same final dataset to identify garment features that may complicate preprocessing and fibre-to-fibre recycling, including hardware, trims, decorative or non-textile attachments, surface coatings or prints, linings, multilayer structures, and secondary components.

Study-specific rule outputs are generated from the final component-normalized dataset rather than from the raw scraped records.

## Public-release curation

This repository provides a curated research dataset rather than a full copy of retailer webpages.

The public release retains fields required for scientific reuse and reproducibility, including product-page URLs, scrape timestamps, product identifiers, product names, colour labels, material-composition fields, normalized materials, normalized categories, normalized components, quality-control flags, and analytical outputs.

The public release does not redistribute:

- product images;
- model images;
- screenshots;
- raw HTML;
- full webpage captures;
- direct image URLs;
- review text;
- unnecessary commercial metadata.

Long-form retailer marketing descriptions may be minimized or transformed into derived feature evidence in public-release versions, depending on the release package. The internal working pipeline retains raw text fields where needed for reproducibility, rule debugging, and validation.

## Limitations

This dataset is based on information disclosed on retailer product pages. It should not be interpreted as a physical teardown dataset.

Some garment features may be missing if they were not disclosed by the retailer or could not be inferred from product-page information.

The normalized material, category, and component fields are rule-based analytical constructs. They are designed to make heterogeneous retailer information comparable across brands and regions, but they do not replace physical inspection.

The dataset represents a fixed online product assortment defined by the URL-collection and product-detail scraping timestamps. Product pages may have changed after the recorded scrape dates.

The dataset supports reproducible assessment of potential sorting and preprocessing barriers, but it does not directly measure industrial sorting outcomes, preprocessing efficiency, or realized fibre-to-fibre recycling performance.

## Recommended citation

If you use this dataset or code, please cite the archived release:

```text
Li, Y., [co-authors]. (2026). Harmonized garment-variant dataset for textile sorting and fibre-to-fibre recycling analysis (Version 1.0.0) [Data set and code]. Zenodo. https://doi.org/xxxxx
```

Please replace the DOI above with the DOI assigned to the archived Zenodo release.

## License

Dataset files, derived tables, documentation, and metadata are licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0), unless otherwise stated.

Source code and scripts are licensed under the MIT License.

The dataset was derived from publicly accessible retailer product-page information. The public release does not redistribute product images, screenshots, raw HTML, review text, or full webpage captures. The above licenses apply only to the curated dataset, documentation, and code included in this repository.
