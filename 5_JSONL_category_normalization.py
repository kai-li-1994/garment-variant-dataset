# -*- coding: utf-8 -*-
"""
Normalize garment categories in the material-normalized JSONL file.

Design
------
The garment-category mapping was developed by combining two complementary 
knowledge bases: retailer-native product taxonomies and sorter-oriented 
grouping logic. First, we examined the original category structures used 
by the retailers in the scraped dataset, with H&M serving as the main backbone 
because its breadcrumb taxonomy was substantially more detailed than that of 
Uniqlo. These retailer-native categories were used to identify fine-grained 
garment distinctions grounded in actual retail classification. Second, we 
aligned these distinctions with broader groups relevant for textile sorting 
analysis, drawing on the category logic and practical perspective of the 
Sorting for Circularity Europe sorter handbook. Based on these two inputs, 
we constructed a two-level taxonomy consisting of parent categories and 
more specific child categories.

The final mapping was implemented as a transparent rule-based procedure. 
For each product, the script assembled searchable text fields from retailer 
category tags, product name, and product description. Because the structure 
and granularity of retailer metadata differed, field priority was adapted by 
brand: for H&M, detailed category breadcrumbs were prioritized, whereas for 
Uniqlo, product names were more informative and therefore evaluated first. 
The mapping then applied hierarchical rules in a fixed order, beginning with 
early exclusion of out-of-scope categories such as footwear and accessories, 
followed by assignment to increasingly broader garment categories. 
More specific garment rules were always evaluated before generic 
fallback categories.

The rule inventory was refined iteratively through repeated inspection of 
unmatched rows, frequent generic assignments, and obvious misclassifications. 
This process helped resolve retailer-specific naming variants and improve 
consistency between retail terminology and sorting-relevant analytical 
categories. The resulting mapping is deterministic, reproducible, and fully 
documented in code through explicit regex inventories and parent-child lookup 
tables.

"""

import json
import re
from collections import Counter
import pandas as pd


# =========================================================
# Input / output
# =========================================================

input_file = r"4_JSONL_material_normalized.jsonl"
output_file = r"5_JSONL_category_normalized.jsonl"
summary_file = r"5_JSONL_category_normalized_summary.txt"
regex_table_file = r"5_category_regex_table.csv"

# =========================================================
# Taxonomy lookup
# =========================================================

DETAIL_TO_PARENT = {
    "outerwear_coat": "tops",
    "outerwear_jacket": "tops",
    "outerwear_gilet": "tops",
    "shirt_blouse": "tops",
    "tshirt_polo": "tops",
    "tank_camisole_vest": "tops",
    "sweater_cardigan": "tops",
    "sweatshirt_hoodie": "tops",
    "top_generic": "tops",

    "jeans": "bottoms",
    "trousers": "bottoms",
    "leggings": "bottoms",
    "joggers": "bottoms",
    "shorts": "bottoms",
    "skirts": "bottoms",

    "underwear_bottoms": "underwear",
    "bras_lingerie": "underwear",
    "swimwear": "underwear",
    "socks_hosiery": "underwear",

    "dresses": "overall",
    "jumpsuits_overalls": "overall",
    "sleepwear_homewear": "overall",
    "set": "overall",

    "footwear": "footwear",
    "accessories": "accessories",
}

HM_WRAPPER_TOKENS = {
    "hm.com", "women", "men", "kids", "kid", "baby", "girls", "boys"
}

# =========================================================
# Build search fields
# only assemble tags; no mapping here
# =========================================================

def build_search_fields(rec):
    brand = str(rec.get("brand") or "").lower().strip()
    name_text = str(rec.get("product_name") or "").lower().strip()
    description_text = str(rec.get("raw_description_text") or "").lower().strip()

    raw_category = rec.get("raw_category")

    if isinstance(raw_category, list):
        category_tags = [str(x).lower().strip() for x in raw_category if str(x).strip()]
    elif isinstance(raw_category, str):
        category_tags = [raw_category.lower().strip()] if raw_category.strip() else []
    else:
        category_tags = []

    # remove obvious wrapper levels for H&M breadcrumb
    if brand == "hm":
        category_tags = [x for x in category_tags if x not in HM_WRAPPER_TOKENS]

    return {
        "brand": brand,
        "category_tags": category_tags,
        "name_text": name_text,
        "description_text": description_text,
    }

# =========================================================
# Regex inventories
# ordered to match decide_from_text()
# design principles:
# - use (?:s)? for plural where practical
# - use [- ] for hyphen / space variants
# - group truly parallel items on one line
# - prefer flatter patterns that export cleanly
# =========================================================

# ---------------------------------------------------------
# 0) Stage-0 scope filters
# ---------------------------------------------------------

PAT_ACCESSORIES = [
    r"\bsunglasses\b",
    r"\bglasses\b",
    r"\bgoggles?\b",
    r"\bbag(?:s)?\b",
    r"\bbackpack(?:s)?\b",
    r"\bpouch(?:es)?\b",
    r"\bwallet(?:s)?\b",
    r"\bkeyring(?:s)?\b",
    r"\bwatch(?:es)?\b",
    r"\bumbrella(?:s)?\b",
    r"\bbelt(?:s)?\b",
    r"\bnecktie(?:s)?\b",
    r"\bbow tie(?:s)?\b",
    r"\bsatin tie(?:s)?\b",
    r"\bbib(?:s)?\b",
    r"\bhat(?:s)?\b",
    r"\bbeanie(?:s)?\b",
    r"\bbaseball cap(?:s)?\b",
    r"\bcap hat(?:s)?\b",
    r"\bcap(?:s)?\b",
    r"\bhairband(?:s)?\b",
    r"\bheadband(?:s)?\b",
    r"\balice band(?:s)?\b",
    r"\bhair claw(?:s)?\b",
    r"\bhair clip(?:s)?\b",
    r"\bhair band(?:s)?\b",
    r"\bhair elastic(?:s)?\b",
    r"\bbobby pin(?:s)?\b",
    r"\bhair pin(?:s)?\b",
    r"\bscrunchie(?:s)?\b",
    r"\b(?:scarf|scarves)\b",
    r"\bglove(?:s)?\b",
    r"\bmitten(?:s)?\b",
    r"\bearmuff(?:s)?\b",
    r"\barm cover(?:s)?\b",
    r"\bneck warmer(?:s)?\b",
    r"\bleg warmer(?:s)?\b",
    r"\bjewellery\b",
    r"\bjewelry\b",
    r"\bblue light glasses\b",
    r"\bwater bottle(?:s)?\b",
    r"\biphone case(?:s)?\b",
    r"\bphone case(?:s)?\b",
    r"\bmobile accessories\b",
    r"\bsleep mask(?:s)?\b",
    r"\bpress[- ]on nail(?:s)?\b",
    r"\bwrist weight(?:s)?\b",
    r"\btowel(?:s)?\b",
    r"\bstole(?:s)?\b",
    r"\bnecklace(?:s)?\b",
    r"\bbracelet(?:s)?\b",
    r"\bpendant(?:s)?\b",
    r"\bcuff bracelet(?:s)?\b",
    r"\bring(?:s)?\b",
    r"\bearring(?:s)?\b",
    r"\bhair extension clip(?:s)?\b",
    r"\bhairbrush(?:es)?\b",
    r"\bhair brush(?:es)?\b",
    r"\bwrist warmer(?:s)?\b",
    r"\bbra extender(?:s)?\b",
    r"\bbody tape\b",
    r"\bblanket(?:s)?\b",
    r"\bfitted sheet(?:s)?\b",
    r"\bsheet(?:s)?\b",
    r"\bcushion cover(?:s)?\b",
    r"\bcushion(?:s)?\b",
    r"\bmuslin cloth(?:s)?\b",
    r"\bstorage crate(?:s)?\b",
    r"\bstorage unit(?:s)?\b",
    r"\bwooden hook(?:s)?\b",
    r"\bhook(?:s)?\b",
    r"\bsoft toy(?:s)?\b",
    r"\btamagotchi\b",
    r"\bbook storage\b",
    r"\bcardboard suitcase(?:s)?\b",
    r"\bchildren'?s chair(?:s)?\b",
    r"\bchair(?:s)?\b",
    r"\bmug(?:s)?\b",
    r"\blunch box(?:es)?\b",
    r"\bstorage box(?:es)?\b",
    r"\bposter(?:s)?\b",
    r"\b(?:shelf|shelves)\b",
    r"\bgarland(?:s)?\b",
    r"\bpaper lamp shade(?:s)?\b",
    r"\blamp shade(?:s)?\b",
    r"\bduvet cover(?: set)?(?:s)?\b",
    r"\bplaymat(?:s)?\b",
    r"\brug(?:s)?\b",
    r"\bcurtain(?:s)?\b",
    r"\bpencil case(?:s)?\b",
    r"\brepair patch(?:es)?\b",
    r"\bmending patch(?:es)?\b",
    r"\biron[- ]on patch(?:es)?\b",
    r"\bwool comb(?:s)?\b",
    r"\bnail kit(?:s)?\b",
    r"\bnipple cover(?:s)?\b",
    r"\bbead box(?:es)?\b",
    r"\bnail sticker(?:s)?\b",
    r"\bhair accessories\b",
    r"\bbathroom accessories\b",
    r"\bvalance(?:s)?\b",
    r"\bhand tattoo(?:s)?\b",
    r"\bcalendar(?:s)?\b",
    r"\bstorage\b",
    r"\bheight chart(?:s)?\b",
    r"\bface decoration(?:s)?\b",
    r"\bwristband(?:s)?\b",
    r"\bmakeup\b",
    r"\bcare products\b",
    r"\btableware\b",
    r"\bgift box(?:es)?\b",
    r"\bhair bow(?:s)?\b",
    r"\bmassager brush(?:es)?\b",
]

PAT_ACCESSORIES_EXCLUDE = [
    r"\bcap sleeve(?:s)?\b",
    r"\bcap-sleeved\b",
    r"\bscarf(?: [\w-]+){0,2}(?:top|dress|blouse)\b",

    # tie-belt garments
    r"\btie[- ]belt(?:ed)? (?: [\w-]+){0,2} dress(?:es)?\b",
    r"\btie[- ]belt(?:ed)? coat(?:s)?\b",
    r"\btie[- ]belt(?:ed)? jacket(?:s)?\b",
    r"\btie[- ]belt(?:ed)? jumpsuit(?:s)?\b",
    r"\btie[- ]belt(?:ed)? trouser(?:s)?\b",
    r"\btie[- ]belt(?:ed)? pant(?:s)?\b",
    r"\btie[- ]belt(?:ed)? shirt dress(?:es)?\b",

    # paper-bag garments
    r"\bpaper bag jeans\b",
    r"\bpaper bag short(?:s)?\b",
    r"\bpaper bag skirt(?:s)?\b",
    r"\bpaper bag trouser(?:s)?\b",
    r"\bpaper bag pant(?:s)?\b",
    r"\bpaper bag denim skirt(?:s)?\b",
    r"\bpaper bag (?: [\w-]+){0,2} shorts(?:s)?\b",

    # scarf-detail / scarf-collar garments
    r"\bscarf[- ]detail top(?:s)?\b",
    r"\bscarf[- ]detail (?: [\w-]+){0,2} dress(?:es)?\b",
    r"\bscarf[- ]detail coat(?:s)?\b",
    r"\bscarf[- ]detail jumper(?:s)?\b",
    r"\bscarf[- ]detail blouse(?:s)?\b",
    r"\bscarf[- ]collar top(?:s)?\b",
    r"\bscarf[- ]collar blouse(?:s)?\b",

    # cap-sleeved garments
    r"\bcap[- ]sleeved top(?:s)?\b",
    r"\bcap[- ]sleeved dress(?:es)?\b",
    r"\bcap[- ]sleeved cardigan(?:s)?\b",
    r"\bcap[- ]sleeved jacket(?:s)?\b",
    r"\bcap[- ]sleeved t[- ]shirt(?:s)?\b",

    # tamagotchi apparel
    r"\btamagotchi (?: [\w-]+){0,2} t[- ]shirt(?:s)?\b",
    r"\btamagotchi top(?:s)?\b",
    r"\btamagotchi hoodie(?:s)?\b",
    r"\btamagotchi sweatshirt(?:s)?\b",
    r"\btamagotchi jumper(?:s)?\b",
]

PAT_FOOTWEAR = [
    r"\bsock boot(?:s)?\b",
    r"\bboot(?:s)?\b",
    r"\bgumboot(?:s)?\b",
    r"\bwellington(?:s)?\b",
    r"\bwellie(?:s)?\b",
    r"\bchelsea boot(?:s)?\b",
    r"\bankle boot(?:s)?\b",
    r"\bknee[- ]high boot(?:s)?\b",
    r"\brain boot(?:s)?\b",
    r"\bsnow boot(?:s)?\b",
    r"\bhiking boot(?:s)?\b",
    r"\bcombat boot(?:s)?\b",
    r"\bwork boot(?:s)?\b",
    r"\bsandal(?:s)?\b",
    r"\bslide(?:s)?\b",
    r"\bflip[- ]flop(?:s)?\b",
    r"\bmule(?:s)?\b",
    r"\bstrappy sandal(?:s)?\b",
    r"\bplatform sandal(?:s)?\b",
    r"\btrainer(?:s)?\b",
    r"\bsneaker(?:s)?\b",
    r"\brunning shoe(?:s)?\b",
    r"\brunner(?:s)?\b",
    r"\btennis shoe(?:s)?\b",
    r"\bhi[- ]top sneaker(?:s)?\b",
    r"\bhigh[- ]top sneaker(?:s)?\b",
    r"\bhi[- ]top trainer(?:s)?\b",
    r"\bhigh[- ]top trainer(?:s)?\b",
    r"\bshoe(?:s)?\b",
    r"\bloafer(?:s)?\b",
    r"\bheel(?:s)?\b",
    r"\bpump(?:s)?\b",
    r"\bflat(?:s)?\b",
    r"\bballet flat(?:s)?\b",
    r"\bslipper(?:s)?\b",
    r"\bmary jane(?:s)?\b",
    r"\bclog(?:s)?\b",
    r"\bmoccasin(?:s)?\b",
    r"\bbrogue(?:s)?\b",
    r"\bderby\b",
    r"\bderbies\b",
    r"\bespadrille(?:s)?\b",
]

PAT_FOOTWEAR_EXCLUDE = [
    r"\bsneaker sock(?:s)?\b",
    r"\btrainer sock(?:s)?\b",
]

# ---------------------------------------------------------
# 1) Underwear / swim / sleep / hosiery
# ---------------------------------------------------------

PAT_SWIMWEAR = [
    r"\bswimwear\b",
    r"\bbeachwear\b",
    r"\bswimsuit(?:s)?\b",
    r"\bbikini(?:s)?\b",
    r"\bswim brief(?:s)?\b",
    r"\bbikini bottom(?:s)?\b",
    r"\bbikini top(?:s)?\b",
    r"\bsarong(?:s)?\b",
    r"\bswim short(?:s)?\b",
    r"\bboard short(?:s)?\b",
    r"\brash vest\b",
    r"\brash guard\b",
    r"\brashie\b",
    r"\btankini(?:s)?\b",
    r"\bbeach kaftan(?:s)?\b",
    r"\bswim top(?:s)?\b",
]

PAT_SWIMWEAR_EXCLUDE = [
    r"\bkaftan dress(?:es)?\b",
    r"\bmaxi kaftan dress(?:es)?\b",
    r"\boversized kaftan dress(?:es)?\b",
]

PAT_SLEEPWEAR = [
    r"\bpyjama(?:s| set)?\b",
    r"\bpajama(?:s| set)?\b",
    r"\bloungewear\b",
    r"\bnightdress(?:es)?\b",
    r"\bbathrobe(?:s)?\b",
    r"\brobe(?:s)?\b",
    r"\bsleepsuit(?:s)?\b",
    r"\bnightshirt(?:s)?\b",
    r"\bnightwear\b",
    r"\bsleepwear\b",
    r"\bnightslip(?:s)?\b",
    r"\bdressing gown(?:s)?\b",
]

PAT_BRAS = [
    r"\bbra(?:s)?\b",
    r"\bbralette(?:s)?\b",
    r"\bbra top(?:s)?\b",
    r"\bsport bra(?:s)?\b",
    r"\bsports bra(?:s)?\b",
    r"\bunderwired bra(?:s)?\b",
    r"\bpush[- ]up bra(?:s)?\b",
    r"\bbustier(?:s)?\b",
]

PAT_UNDERWEAR = [
    r"\bbrief(?:s)?\b",
    r"\bpant(?:y|ies)\b",
    r"\bthong(?:s)?\b",
    r"\bundershort(?:s)?\b",
    r"\bunderwear\b",
    r"\bknicker(?:s)?\b",
    r"\bcorset(?:s)?\b",
    r"\bboxer(?:s)?\b",
    r"\bboxer brief(?:s)?\b",
    r"\btrunk(?:s)?\b",
    r"\bhalf slip(?:s)?\b",
    r"\bunderskirt(?:s)?\b",
    r"\bsculpting slip(?:s)?\b",
    r"\bfirm shape slip(?:s)?\b",
    r"\blight shape slip(?:s)?\b",
]

PAT_UNDERWEAR_EXCLUDE = [
    r"\bcorset(?: [\w-]+){0,2} skirt\b",
    r"\bcorset(?: [\w-]+){0,2} dress\b",
    r"\bcorset top(?:s)?\b",
    r"\bbodysuit dress(?:es)?\b",

]

PAT_BODYSUIT_UNDERWEAR = [
    r"\blight shape body\b",
    r"\bseamless light shape body\b",
    r"\bmicrofibre body\b",
    r"\blace body\b",
    r"\blace[- ]trimmed body\b",
    r"\blace[- ]trimmed cotton body\b",
    r"\bseamless body\b",
    r"\bpointelle body\b",
    r"\bshaping biker(?:s)?\b",
    r"\bbodysuit(?:s)?\b",
]

PAT_SOCKS_HOSIERY = [
    r"\bankle sock(?:s)?\b",
    r"\btrainer sock(?:s)?\b",
    r"\bsneaker sock(?:s)?\b",
    r"\bcrew sock(?:s)?\b",
    r"\bno[- ]show sock(?:s)?\b",
    r"\bknee[- ]high sock(?:s)?\b",
    r"\bslipper sock(?:s)?\b",
    r"\bsock(?:s)?\b",
    r"\btight(?:s)?\b",
    r"\bhosiery\b",
    r"\bpantyhose\b",
    r"\bhold[- ]up(?:s)?\b",
    r"\bstocking(?:s)?\b",
]

# ---------------------------------------------------------
# 2) Overall
# ---------------------------------------------------------

PAT_JUMPSUIT = [
    r"\bjumpsuit(?:s)?\b",
    r"\bplaysuit(?:s)?\b",
    r"\bromper(?:s)?\b",
    r"\bdungaree(?:s)?\b",
    r"\ball[- ]in[- ]one(?:s)?\b",
    r"\bcoverall(?:s)?\b",
    r"\bleotard(?:s)?\b",
    r"\bunitard(?:s)?\b",
    r"\bone[- ]piece outfit(?:s)?\b",
    r"\bone[- ]piece long sleeve outfit(?:s)?\b",
    r"\bsport body\b",
    r"\bsports body\b",
    r"\bsnowsuit(?:s)?\b",
    r"\bpramsuit(?:s)?\b",
    r"\bski suit(?:s)?\b",
    r"\boverall(?:s)?\b",
    r"\bpile overall(?:s)?\b",
]

PAT_DRESS = [
    r"\bblazer dress(?:es)?\b",
    r"\btee dress(?:es)?\b",
    r"\bcape dress(?:es)?\b",
    r"\btie dress(?:es)?\b",
    r"\bcorset dress(?:es)?\b",
    r"\bdress set(?:s)?\b",
    r"\bdressy set(?:s)?\b",
    r"\bdress & top set(?:s)?\b",
    r"\btop & dress set(?:s)?\b",
    r"\bdress(?:es)?\b",
    r"\bgathered chiffon kaftan\b",
]

PAT_DRESS_EXCLUDE = [
    r"\bdress shirt(?:s)?\b",
]

PAT_SET = [
    r"\b2[- ]piece set(?:s)?\b",
    r"\b3[- ]piece set(?:s)?\b",
    r"\bbase layer set(?:s)?\b",
    r"\bjersey set(?:s)?\b",
    r"\bknitted set(?:s)?\b",
    r"\bribbed set(?:s)?\b",
    r"\bcotton set(?:s)?\b",
    r"\bvelour set(?:s)?\b",
    r"\bfleece set(?:s)?\b",
    r"\bcostume set(?:s)?\b",
    r"\bcostume\b",
    r"\bset(?:s)?\b",
]

# ---------------------------------------------------------
# 3) Bottoms
# ---------------------------------------------------------

PAT_BOTTOMS_JEANS = [
    r"\bskinny jeans\b",
    r"\bstraight jeans\b",
    r"\bwide[- ]leg jeans\b",
    r"\bmom jeans\b",
    r"\bboyfriend jeans\b",
    r"\bflared jeans\b",
    r"\bdenim jeans\b",
    r"\bjegging(?:s)?\b",
    r"\bjeans\b",
]

PAT_BOTTOMS_LEGGINGS = [
    r"\blegging(?:s)?\b",
    r"\bjegging(?:s)?\b",
    r"\btregging(?:s)?\b",
    r"\brunning tight(?:s)?\b",
    r"\btraining tight(?:s)?\b",
    r"\bgym tight(?:s)?\b",
    r"\bsport tight(?:s)?\b",
    r"\bsports tight(?:s)?\b",
    r"\bbase layer tight(?:s)?\b",
    r"\bthermal tight(?:s)?\b",
    r"\bheattech tight(?:s)?\b",
    r"\bski tight(?:s)?\b",
    r"\bcompression tight(?:s)?\b",
    r"\bperformance tight(?:s)?\b",
    r"\bworkout tight(?:s)?\b",
    r"\bactive tight(?:s)?\b",
    r"\bactivewear tight(?:s)?\b",
    r"\byoga tight(?:s)?\b",
    r"\bcycling tight(?:s)?\b",
]

PAT_BOTTOMS_JOGGERS = [
    r"\bjogger(?:s)?\b",
    r"\bsweatpant(?:s)?\b",
    r"\btrack pant(?:s)?\b",
    r"\btrackie(?:s)?\b",
]

PAT_SKIRT = [
    r"\bmini skirt(?:s)?\b",
    r"\bmidi skirt(?:s)?\b",
    r"\bmaxi skirt(?:s)?\b",
    r"\bskort(?:s)?\b",
    r"\bskirt(?:s)?\b",
]

PAT_BOTTOMS_SHORTS = [
    r"\bsweatshort(?:s)?\b",
    r"\bbermuda short(?:s)?\b",
    r"\bcycling short(?:s)?\b",
    r"\bpaper bag short(?:s)?\b",
    r"\bshort(?:s)? set(?:s)?\b",
    r"\bshorts\b",
]

PAT_BOTTOMS_TROUSERS = [
    r"\btrouser(?:s)?\b",
    r"\bpant(?:s)?\b",
    r"\bchino(?:s)?\b",
    r"\bcargo(?:s)?\b",
    r"\bculotte(?:s)?\b",
    r"\bflared trouser(?:s)?\b",
    r"\bflared pant(?:s)?\b",
    r"\btailored trouser(?:s)?\b",
    r"\bsuit pant(?:s)?\b",
    r"\bwide[- ]leg pant(?:s)?\b",
    r"\bwide[- ]leg trouser(?:s)?\b",
    r"\bbreeches\b",
]

# ---------------------------------------------------------
# 4) Tops
# ---------------------------------------------------------

PAT_OUTERWEAR_GILET = [
    r"\bgilet(?:s)?\b",
    r"\bwaistcoat(?:s)?\b",
    r"\bpuffer vest(?:s)?\b",
    r"\bquilted vest(?:s)?\b",
    r"\bteddy vest(?:s)?\b",
    r"\bfluffy vest(?:s)?\b",
    r"\bpadded vest(?:s)?\b",
    r"\bwindproof vest(?:s)?\b",
    r"\bfleece vest(?:s)?\b",
    r"\bthermal vest(?:s)?\b",
    r"\bski vest(?:s)?\b",
    r"\brunning vest(?:s)?\b",
    r"\bpile vest(?:s)?\b",
    r"\bactivewear vest(?:s)?\b",
    r"\bcorduroy vest(?:s)?\b",
    r"\blined vest(?:s)?\b",
    r"\blinen vest(?:s)?\b",
    r"\bpufftech vest\b",
    r"\bpuffertech vest\b",
    r"\bpufftech blouson\b",
    r"\bpuffertech blouson\b",
    r"\bpufftech washable vest\b",
    r"\bpuffertech washable vest\b",
    r"\bpufftech compact vest\b",
    r"\bpuffertech compact vest\b",
    r"\bpufftech seamless vest\b",
    r"\bpuffertech seamless vest\b",
    r"\bpufftech cropped vest\b",
    r"\bpuffertech cropped vest\b",
    r"\bpufftech short blouson\b",
    r"\bpuffertech short blouson\b",
]

PAT_OUTERWEAR_JACKET = [
    r"\bjacket(?:s)?\b",
    r"\bblazer(?:s)?\b",
    r"\bbomber(?:s)?\b",
    r"\bwindbreaker(?:s)?\b",
    r"\bfleece jacket(?:s)?\b",
    r"\bshacket(?:s)?\b",
    r"\bblouson(?:s)?\b",
    r"\btrucker jacket(?:s)?\b",
]

PAT_OUTERWEAR_COAT = [
    r"\bpuffer coat(?:s)?\b",
    r"\btrench coat(?:s)?\b",
    r"\bcape coat(?:s)?\b",
    r"\bcaped coat(?:s)?\b",
    r"\bcoat(?:s)?\b",
    r"\bparka(?:s)?\b",
    r"\bovercoat(?:s)?\b",
    r"\banorak(?:s)?\b",
    r"\bmac(?:s)?\b",
    r"\bponcho(?:s)?\b",
    r"\btrenchcoat\b",
]

PAT_SWEATSHIRT_HOODIE = [
    r"\bhoodie(?:s)?\b",
    r"\bsweatshirt(?:s)?\b",
    r"\bsweat(?:s)?\b",
    r"\bcrewneck sweatshirt(?:s)?\b",
    r"\bhooded sweatshirt(?:s)?\b",
    r"\bzip[- ]up hoodie(?:s)?\b",
]

PAT_SWEATER_CARDIGAN = [
    r"\bknitwear\b",
    r"\bsweater(?:s)?\b",
    r"\bjumper(?:s)?\b",
    r"\bcardigan(?:s)?\b",
    r"\bturtleneck(?:s)?\b",
    r"\bpullover(?:s)?\b",
    r"\broll[- ]neck(?:s)?\b",
    r"\bzip[- ]up cardigan(?:s)?\b",
    r"\bknitted vest(?:s)?\b",
    r"\bknit(?: [\w-]+){0,2} top(?:s)?\b",
    r"\bwoollen top(?:s)?\b",
    r"\bknitted cape(?:s)?\b",
    r"\bknit cape(?:s)?\b",
    r"\brib[- ]knit cape(?:s)?\b",
    r"\bribbed knit cape(?:s)?\b",
    r"\bcable knit cape(?:s)?\b",
    r"\bsoft knit cape(?:s)?\b",
    r"\bchunky knit cape(?:s)?\b",
    r"\bcashmere cape(?:s)?\b",
    r"\bfringe[- ]trimmed cape(?:s)?\b",
]

PAT_SWEATER_CARDIGAN_EXCLUDE = [
    r"\bturtleneck(?:s)?(?: [\w-]+){0,2}(?:top|dress)\b",
    r"\bturtleneck(?:s)?(?: [\w-]+){0,2} t[- ]shirt(?:s)?\b",
    r"\bturtleneck(?:s)?(?: [\w-]+){0,2} tee(?:s)?\b",
]

PAT_TOPS_TANK = [
    r"\btank(?:s)?\b",
    r"\bcami(?:sole)?(?:s)?\b",
    r"\bvest top(?:s)?\b",
    r"\bstrappy top(?:s)?\b",
    r"\bhalter top(?:s)?\b",
    r"\bhalterneck top(?:s)?\b",
    r"\bsleeveless top(?:s)?\b",
    r"\bsinglet(?:s)?\b",
    r"\bbandeau(?:x)?\b",
    r"\btube top(?:s)?\b",
    r"\bpremium linen vest\b",
    r"\bnewborn body\b",
]

PAT_TOPS_TSHIRT = [
    r"\bt[- ]shirt(?:s)?\b",
    r"\btee(?:s)?\b",
    r"\bjersey top(?:s)?\b",
    r"\bgraphic tee(?:s)?\b",
    r"\blong sleeve tee(?:s)?\b",
    r"\bcrew neck t[- ]shirt(?:s)?\b",
    r"\bshort sleeve tee(?:s)?\b",
    r"\bshort sleeve t[- ]shirt(?:s)?\b",
    r"\bairism cotton crew neck t\b",
    r"\bcotton top(?:s)?\b",
    r"\bmicrofibre top(?:s)?\b",
    r"\bboat[- ]neck top(?:s)?\b",
    r"\bsport top(?:s)?\b",
    r"\bsports top(?:s)?\b",
    r"\bactivewear top(?:s)?\b",
    r"\brunning top(?:s)?\b",
    r"\bcycling top(?:s)?\b",
    r"\bfootball top(?:s)?\b",
    r"\bmuscle fit sport top(?:s)?\b",
    r"\bmuscle fit sports top(?:s)?\b",
    r"\bmuscle fit activewear top(?:s)?\b",
    r"\bhigh neck top(?:s)?\b",
    r"\bv[- ]neck top(?:s)?\b",
    r"\bcap sleeve top(?:s)?\b",
    r"\brib top(?:s)?\b",
    r"\blong[- ]sleeve(?:d)?(?: [\w-]+){0,2} top(?:s)?\b"
]

PAT_TOPS_SHIRT = [
    r"\bdress shirt(?:s)?\b",
    r"\bbutton[- ]down shirt(?:s)?\b",
    r"\bovershirt(?:s)?\b",
    r"\bpolo(?:s)?\b",
    r"\bblouse(?:s)?\b",
    r"\bhenley(?:s)?\b",
    r"\bshirt(?:s)?\b",
    r"\bbutton[- ]front top(?:s)?\b",
    r"\bpeplum top(?:s)?\b",
    r"\blace trim top(?:s)?\b",
    r"\blace[- ]trimmed top(?:s)?\b",
    r"\blace top(?:s)?\b",
    r"\bdraped top(?:s)?\b",
    r"\bdraped viscose top(?:s)?\b",
    r"\btwist[- ]detail top(?:s)?\b",
    r"\bcrinkled tie front top(?:s)?\b",
    r"\btie[- ]front top(?:s)?\b",
    r"\bballoon[- ]sleeved top(?:s)?\b",
    r"\bprint flutter sleeve top(?:s)?\b",
    r"\bflutter sleeve top(?:s)?\b",
    r"\brib[- ]knit collared top(?:s)?\b",
    r"\bcollared top(?:s)?\b",
    r"\bsmocked top(?:s)?\b",
    r"\bcollared knitted top(?:s)?\b",
]

PAT_TOPS_SHIRT_EXCLUDE = [
    r"\bt[- ]shirt(?:s)?\b",
    r"\btee(?:s)?\b",
    r"\bjersey top(?:s)?\b",
    r"\bsinglet(?:s)?\b",
]

PAT_TOPS_GENERIC = [
    r"\btop(?:s)?\b",
]

PAT_TOPS_GENERIC_EXCLUDE = [
    r"\btop(?:s)? shoe(?:s)?\b",
    r"\btop(?:s)? sneaker(?:s)?\b",
    r"\btop(?:s)? trainer(?:s)?\b",
    r"\btop(?:s)? runner(?:s)?\b",
    r"\btop(?:s)? tennis shoe(?:s)?\b",
    r"\btop(?:s)? backpack(?:s)?\b",
    r"\btop(?:s)? bag(?:s)?\b",
    r"\btop(?:s)? sunglasses\b",
    r"\btop(?:s)? glasses\b",
]

# =========================================================
# Shared matching helper
# =========================================================

def hit(patterns, text):
    if not text:
        return False
    return any(re.search(p, text, flags=re.I) for p in patterns)

# =========================================================
# Detail-category inference
# =========================================================

def infer_detail_category(rec):
    f = build_search_fields(rec)

    brand = f["brand"]
    name_text = f["name_text"]
    description_text = f["description_text"]
    category_tags = f["category_tags"]

    category_text = " ".join(category_tags)

    # H&M: use more specific category tags first
    if brand == "hm":
        category_tag_texts = list(reversed(category_tags))
    else:
        category_tag_texts = category_tags[:]

    # -----------------------------------------------------
    # Stage 0: early exclusion of out-of-scope
    # use only category/name, not description
    # -----------------------------------------------------
    scope_texts = category_tag_texts + [name_text]

    for text in scope_texts:
        if hit(PAT_FOOTWEAR, text) and not hit(PAT_FOOTWEAR_EXCLUDE, text):
            return {
                "detail_category": "footwear",
                "detail_rule_source": "category_or_name_scope",
                "detail_rule_hit": "footwear",
            }

        if hit(PAT_ACCESSORIES, text) and not hit(PAT_ACCESSORIES_EXCLUDE, text):
            return {
                "detail_category": "accessories",
                "detail_rule_source": "category_or_name_scope",
                "detail_rule_hit": "accessories",
            }


    # -----------------------------------------------------
    # Stage 1: child-category mapping
    # H&M: category -> name -> description
    # Uniqlo: name -> category -> description
    # -----------------------------------------------------
    if brand == "hm":
        texts = [(t, "category_tags") for t in category_tag_texts] + [
            (name_text, "name_text"),
            (description_text, "description_text"),
        ]
    else:
        texts = [
            (name_text, "name_text"),
            (category_text, "category_tags"),
            (description_text, "description_text"),
        ]

    def decide_from_text(text, source_label):
        if not text:
            return None

        # underwear / swim / sleep / hosiery
        if hit(PAT_SWIMWEAR, text) and not hit(PAT_SWIMWEAR_EXCLUDE, text):
            return ("swimwear", source_label, "swimwear")

        if hit(PAT_SLEEPWEAR, text):
            return ("sleepwear_homewear", source_label, "sleepwear_homewear")


        if hit(PAT_BRAS, text):
            return ("bras_lingerie", source_label, "bras_lingerie")

        if hit(PAT_UNDERWEAR, text) and not hit(PAT_UNDERWEAR_EXCLUDE, text):
            return ("underwear_bottoms", source_label, "underwear_bottoms")

        if hit(PAT_BODYSUIT_UNDERWEAR, text) and not hit(PAT_UNDERWEAR_EXCLUDE, text):
            return ("underwear_bottoms", source_label, "underwear_bottoms")

        if hit(PAT_SOCKS_HOSIERY, text):
            return ("socks_hosiery", source_label, "socks_hosiery")

        # overall

        if hit(PAT_JUMPSUIT, text):
            return ("jumpsuits_overalls", source_label, "jumpsuits_overalls")

        if hit(PAT_DRESS, text) and not hit(PAT_DRESS_EXCLUDE, text):
            return ("dresses", source_label, "dresses")

        if hit(PAT_SET, text):
            return ("set", source_label, "set")

        # bottoms
        if hit(PAT_BOTTOMS_JEANS, text):
            return ("jeans", source_label, "jeans")

        if hit(PAT_BOTTOMS_LEGGINGS, text):
            return ("leggings", source_label, "leggings")

        if hit(PAT_BOTTOMS_JOGGERS, text):
            return ("joggers", source_label, "joggers")

        if hit(PAT_SKIRT, text):
            return ("skirts", source_label, "skirts")

        if hit(PAT_BOTTOMS_SHORTS, text):
            return ("shorts", source_label, "shorts")

        if hit(PAT_BOTTOMS_TROUSERS, text):
            return ("trousers", source_label, "trousers")

        # tops: check specific before broad
        if hit(PAT_OUTERWEAR_GILET, text):
            return ("outerwear_gilet", source_label, "outerwear_gilet")

        if hit(PAT_OUTERWEAR_JACKET, text):
            return ("outerwear_jacket", source_label, "outerwear_jacket")

        if hit(PAT_OUTERWEAR_COAT, text):
            return ("outerwear_coat", source_label, "outerwear_coat")

        if hit(PAT_SWEATSHIRT_HOODIE, text):
            return ("sweatshirt_hoodie", source_label, "sweatshirt_hoodie")

        if hit(PAT_SWEATER_CARDIGAN, text) and not hit(PAT_SWEATER_CARDIGAN_EXCLUDE, text):
            return ("sweater_cardigan", source_label, "sweater_cardigan")

        if hit(PAT_TOPS_TANK, text):
            return ("tank_camisole_vest", source_label, "tank_camisole_vest")

        if hit(PAT_TOPS_TSHIRT, text):
            return ("tshirt_polo", source_label, "tshirt_polo")

        if hit(PAT_TOPS_SHIRT, text) and not hit(PAT_TOPS_SHIRT_EXCLUDE, text):
            return ("shirt_blouse", source_label, "shirt_blouse")

        if hit(PAT_TOPS_GENERIC, text) and not hit(PAT_TOPS_GENERIC_EXCLUDE, text):
            return ("top_generic", source_label, "top_generic")

        return None

    for text, source_label in texts:
        decision = decide_from_text(text, source_label)
        if decision is not None:
            detail_category, detail_rule_source, detail_rule_hit = decision
            return {
                "detail_category": detail_category,
                "detail_rule_source": detail_rule_source,
                "detail_rule_hit": detail_rule_hit,
            }

    # Final fallback: keep unresolved visible
    return {
        "detail_category": None,
        "detail_rule_source": None,
        "detail_rule_hit": None,
    }

# =========================================================
# Main
# =========================================================

line_count = 0
written_count = 0
bad_json = 0
dropped_scope_count = 0

brand_input_counter = Counter()
brand_kept_counter = Counter()
detail_counter = Counter()
parent_counter = Counter()
detail_source_counter = Counter()
dropped_scope_counter = Counter()

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

        brand_input_counter[str(rec.get("brand"))] += 1

        out = dict(rec)

        detail_info = infer_detail_category(rec)
        detail_category = detail_info["detail_category"]

        if detail_category is None:
            parent_category = None
        else:
            parent_category = DETAIL_TO_PARENT.get(detail_category)
        
        # -------------------------------------------------
        # Drop out-of-scope rows for current analysis
        # - accessories
        # - footwear
        # - unallocated rows (detail_category is None)
        # -------------------------------------------------
        if detail_category in {"accessories", "footwear"} or detail_category is None:
            dropped_scope_count += 1

            if detail_category is None:
                dropped_scope_counter["unallocated_None"] += 1
            else:
                dropped_scope_counter[detail_category] += 1

            continue
        
        brand_kept_counter[str(rec.get("brand"))] += 1

        out = dict(rec)
        out["detail_category"] = detail_category
        out["detail_rule_source"] = detail_info["detail_rule_source"]
        out["detail_rule_hit"] = detail_info["detail_rule_hit"]
        out["parent_category"] = parent_category

        detail_counter[str(detail_category)] += 1
        parent_counter[str(parent_category)] += 1
        detail_source_counter[str(out["detail_rule_source"])] += 1

        fout.write(json.dumps(out, ensure_ascii=False) + "\n")
        written_count += 1

# =========================================================
# Export regex table (simple inline export)
# =========================================================
def pretty_pattern_compact(pat: re.Pattern | str) -> str:
    raw = pat.pattern if hasattr(pat, "pattern") else str(pat)
    text = raw

    text = text.replace(r"\b", "")
    text = text.replace(r"\s+", " ")
    text = text.replace(r"\s*", " ")
    text = text.replace("[- ]", "-")
    
    text = re.sub(
        r"\(\?: \[\\w-\]\+\)\{0,2\}",
        " [up to 2 extra words] ",
        text
    )

    text = re.sub(r"\(\?:s\)\?", "(s)", text)
    text = re.sub(r"\(\?:es\)\?", "(es)", text)
    text = re.sub(r"\(\?:s\|ves\)", "(s/ves)", text)
    text = re.sub(r"\(\?:y\|ies\)", "(y/ies)", text)
    text = re.sub(r"(?<!\))s\?", "(s)", text)

    text = re.sub(r"\(\?:([^()]+)\)\?", r"[\1]", text)

    def expand_suffix_group(m):
        prefix = m.group(1)
        inner = m.group(2)
        opts = inner.split("|")
        return " / ".join(prefix + opt for opt in opts)

    text = re.sub(r"([A-Za-z]+)\(\?:([^()]+)\)", expand_suffix_group, text)

    def expand_prefix_group(m):
        inner = m.group(1)
        suffix = m.group(2)
        opts = inner.split("|")
        return " / ".join(opt + suffix for opt in opts)

    text = re.sub(r"\(\?:([^()]+)\)([A-Za-z][A-Za-z -]*)", expand_prefix_group, text)
    text = re.sub(r"\(\?:([^()]+)\)", lambda m: m.group(1).replace("|", " / "), text)

    text = text.replace("|", " / ")
    text = text.replace(r"\\", "")
    text = text.replace("\\", "")
    text = re.sub(r"\(([^()]*)\)", r"\1", text)

    text = re.sub(r"\s*/\s*", " / ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("[ ", "[").replace(" ]", "]")

    return text

# ---------------------------------------
# collect your inventories in one dict
# values can be raw strings or compiled patterns
# ---------------------------------------
regex_lists = {
    # stage-0 scope filters
    "PAT_ACCESSORIES": PAT_ACCESSORIES,
    "PAT_ACCESSORIES_EXCLUDE": PAT_ACCESSORIES_EXCLUDE,
    "PAT_FOOTWEAR": PAT_FOOTWEAR,
    "PAT_FOOTWEAR_EXCLUDE": PAT_FOOTWEAR_EXCLUDE,

    # underwear / swim / sleep / hosiery
    "PAT_SWIMWEAR": PAT_SWIMWEAR,
    "PAT_SWIMWEAR_EXCLUDE": PAT_SWIMWEAR_EXCLUDE,
    "PAT_SLEEPWEAR": PAT_SLEEPWEAR,
    "PAT_BRAS": PAT_BRAS,
    "PAT_UNDERWEAR": PAT_UNDERWEAR,
    "PAT_UNDERWEAR_EXCLUDE": PAT_UNDERWEAR_EXCLUDE,
    "PAT_BODYSUIT_UNDERWEAR": PAT_BODYSUIT_UNDERWEAR,
    "PAT_SOCKS_HOSIERY": PAT_SOCKS_HOSIERY,

    # overall
    "PAT_JUMPSUIT": PAT_JUMPSUIT,
    "PAT_DRESS": PAT_DRESS,
    "PAT_DRESS_EXCLUDE": PAT_DRESS_EXCLUDE,
    "PAT_SET": PAT_SET,

    # bottoms
    "PAT_BOTTOMS_JEANS": PAT_BOTTOMS_JEANS,
    "PAT_BOTTOMS_LEGGINGS": PAT_BOTTOMS_LEGGINGS,
    "PAT_BOTTOMS_JOGGERS": PAT_BOTTOMS_JOGGERS,
    "PAT_SKIRT": PAT_SKIRT,
    "PAT_BOTTOMS_SHORTS": PAT_BOTTOMS_SHORTS,
    "PAT_BOTTOMS_TROUSERS": PAT_BOTTOMS_TROUSERS,

    # tops
    "PAT_OUTERWEAR_GILET": PAT_OUTERWEAR_GILET,
    "PAT_OUTERWEAR_JACKET": PAT_OUTERWEAR_JACKET,
    "PAT_OUTERWEAR_COAT": PAT_OUTERWEAR_COAT,
    "PAT_SWEATSHIRT_HOODIE": PAT_SWEATSHIRT_HOODIE,
    "PAT_SWEATER_CARDIGAN": PAT_SWEATER_CARDIGAN,
    "PAT_SWEATER_CARDIGAN_EXCLUDE": PAT_SWEATER_CARDIGAN_EXCLUDE,
    "PAT_TOPS_TANK": PAT_TOPS_TANK,
    "PAT_TOPS_TSHIRT": PAT_TOPS_TSHIRT,
    "PAT_TOPS_SHIRT": PAT_TOPS_SHIRT,
    "PAT_TOPS_SHIRT_EXCLUDE": PAT_TOPS_SHIRT_EXCLUDE,
    "PAT_TOPS_GENERIC": PAT_TOPS_GENERIC,
    "PAT_TOPS_GENERIC_EXCLUDE": PAT_TOPS_GENERIC_EXCLUDE,
}

# =========================================================
# Export category mapping table for documentation
# =========================================================

category_mapping_table_file = r"5_category_mapping_table.csv"

CATEGORY_RULE_TABLE = [
    # stage, detail_category, parent_category, include_group, exclude_group, main_source
    (0, "accessories", "accessories", "PAT_ACCESSORIES", "PAT_ACCESSORIES_EXCLUDE", "category_or_name_scope"),
    (0, "footwear", "footwear", "PAT_FOOTWEAR", "PAT_FOOTWEAR_EXCLUDE", "category_or_name_scope"),

    (1, "swimwear", "underwear", "PAT_SWIMWEAR", "PAT_SWIMWEAR_EXCLUDE", "category/name/description"),
    (1, "sleepwear_homewear", "overall", "PAT_SLEEPWEAR", "", "category/name/description"),
    (1, "bras_lingerie", "underwear", "PAT_BRAS", "", "category/name/description"),
    (1, "underwear_bottoms", "underwear", "PAT_UNDERWEAR; PAT_BODYSUIT_UNDERWEAR", "PAT_UNDERWEAR_EXCLUDE", "category/name/description"),
    (1, "socks_hosiery", "underwear", "PAT_SOCKS_HOSIERY", "", "category/name/description"),

    (1, "jumpsuits_overalls", "overall", "PAT_JUMPSUIT", "", "category/name/description"),
    (1, "dresses", "overall", "PAT_DRESS", "PAT_DRESS_EXCLUDE", "category/name/description"),
    (1, "set", "overall", "PAT_SET", "", "category/name/description"),

    (1, "jeans", "bottoms", "PAT_BOTTOMS_JEANS", "", "category/name/description"),
    (1, "leggings", "bottoms", "PAT_BOTTOMS_LEGGINGS", "", "category/name/description"),
    (1, "joggers", "bottoms", "PAT_BOTTOMS_JOGGERS", "", "category/name/description"),
    (1, "skirts", "bottoms", "PAT_SKIRT", "", "category/name/description"),
    (1, "shorts", "bottoms", "PAT_BOTTOMS_SHORTS", "", "category/name/description"),
    (1, "trousers", "bottoms", "PAT_BOTTOMS_TROUSERS", "", "category/name/description"),

    (1, "outerwear_gilet", "tops", "PAT_OUTERWEAR_GILET", "", "category/name/description"),
    (1, "outerwear_jacket", "tops", "PAT_OUTERWEAR_JACKET", "", "category/name/description"),
    (1, "outerwear_coat", "tops", "PAT_OUTERWEAR_COAT", "", "category/name/description"),
    (1, "sweatshirt_hoodie", "tops", "PAT_SWEATSHIRT_HOODIE", "", "category/name/description"),
    (1, "sweater_cardigan", "tops", "PAT_SWEATER_CARDIGAN", "PAT_SWEATER_CARDIGAN_EXCLUDE", "category/name/description"),
    (1, "tank_camisole_vest", "tops", "PAT_TOPS_TANK", "", "category/name/description"),
    (1, "tshirt_polo", "tops", "PAT_TOPS_TSHIRT", "", "category/name/description"),
    (1, "shirt_blouse", "tops", "PAT_TOPS_SHIRT", "PAT_TOPS_SHIRT_EXCLUDE", "category/name/description"),
    (1, "top_generic", "tops", "PAT_TOPS_GENERIC", "PAT_TOPS_GENERIC_EXCLUDE", "category/name/description"),
]

category_mapping_rows = []

for rule_order, (stage, detail_category, parent_category, include_group, exclude_group, main_source) in enumerate(CATEGORY_RULE_TABLE, start=1):
    include_pretty = []
    include_raw = []

    for g in [x.strip() for x in include_group.split(";") if x.strip()]:
        patterns = regex_lists.get(g, [])
        include_pretty.extend([pretty_pattern_compact(p) for p in patterns])
        include_raw.extend([p.pattern if hasattr(p, "pattern") else str(p) for p in patterns])

    exclude_pretty = []
    exclude_raw = []

    for g in [x.strip() for x in exclude_group.split(";") if x.strip()]:
        patterns = regex_lists.get(g, [])
        exclude_pretty.extend([pretty_pattern_compact(p) for p in patterns])
        exclude_raw.extend([p.pattern if hasattr(p, "pattern") else str(p) for p in patterns])

    category_mapping_rows.append({
        "rule_order": rule_order,
        "stage": stage,
        "detail_category": detail_category,
        "parent_category": parent_category,
        "include_group": include_group,
        "exclude_group": exclude_group,
        "main_source": main_source,
        "n_include_patterns": len(include_pretty),
        "n_exclude_patterns": len(exclude_pretty),
        "include_patterns_readable": " ; ".join(include_pretty),
        "exclude_patterns_readable": " ; ".join(exclude_pretty),
        "include_patterns_raw": " ; ".join(include_raw),
        "exclude_patterns_raw": " ; ".join(exclude_raw),
    })

df_category_mapping = pd.DataFrame(category_mapping_rows)
df_category_mapping.to_csv(category_mapping_table_file, index=False, encoding="utf-8-sig")

rows = []

for group_name, patterns in regex_lists.items():
    rule_type = "exclude" if group_name.endswith("_EXCLUDE") else "include"

    pretty_items = [pretty_pattern_compact(p) for p in patterns]
    raw_items = [p.pattern if hasattr(p, "pattern") else str(p) for p in patterns]

    rows.append({
        "group_name": group_name,
        "rule_type": rule_type,
        "n_patterns": len(patterns),
        "pretty_patterns_joined": " ; ".join(pretty_items),
        "raw_patterns_joined": " ; ".join(raw_items),
    })

df_regex = pd.DataFrame(rows)
df_regex.to_csv(regex_table_file, index=False, encoding="utf-8")

# =========================================================
# Summary
# =========================================================

with open(summary_file, "w", encoding="utf-8") as fsum:
    fsum.write("JSONL category normalization summary\n\n")
    fsum.write(f"Input file: {input_file}\n")
    fsum.write(f"Output file: {output_file}\n")
    fsum.write(f"Category mapping table file: {category_mapping_table_file}\n")
    fsum.write(f"Regex table file: {regex_table_file}\n\n")

    fsum.write("Row processing summary\n")
    fsum.write("=" * 60 + "\n")
    fsum.write(f"Processed non-empty lines: {line_count}\n")
    fsum.write(f"Bad JSON lines skipped: {bad_json}\n")
    fsum.write(f"Dropped JSON lines (accessories + footwear + unallocated): {dropped_scope_count}\n")
    fsum.write(f"Written JSON lines after dropping: {written_count}\n")
    fsum.write(f"Consistency check (expected written lines): {line_count - bad_json - dropped_scope_count}\n\n")

    fsum.write("Dropped scope-category counts\n")
    fsum.write("=" * 60 + "\n")
    for k, v in dropped_scope_counter.most_common():
        fsum.write(f"{k}: {v}\n")

    fsum.write("\nBrand counts before scope filtering\n")
    fsum.write("=" * 60 + "\n")
    for k in sorted(brand_input_counter):
        fsum.write(f"{k}: {brand_input_counter[k]}\n")

    fsum.write("\nBrand counts after scope filtering (kept rows only)\n")
    fsum.write("=" * 60 + "\n")
    for k in sorted(brand_kept_counter):
        fsum.write(f"{k}: {brand_kept_counter[k]}\n")

    fsum.write("\nParent category counts (kept rows only)\n")
    fsum.write("=" * 60 + "\n")
    for k, v in parent_counter.most_common():
        fsum.write(f"{k}: {v}\n")

    fsum.write("\nDetail category counts (kept rows only)\n")
    fsum.write("=" * 60 + "\n")
    for k, v in detail_counter.most_common():
        fsum.write(f"{k}: {v}\n")

    fsum.write("\nDetail rule source counts (kept rows only)\n")
    fsum.write("=" * 60 + "\n")
    for k, v in detail_source_counter.most_common():
        fsum.write(f"{k}: {v}\n")

    fsum.write("\nNotes\n")
    fsum.write("=" * 60 + "\n")
    fsum.write("- This step assigns both detail_category and parent_category.\n")
    fsum.write("- parent_category is derived from detail_category.\n")
    fsum.write("- Rows classified as accessories or footwear are dropped from the exported JSONL.\n")
    fsum.write("- Rows with unallocated category (detail_category=None / parent_category=None) are also dropped.\n")
    fsum.write("- Category mapping table and regex inventory are exported as CSV files.\n")

print("Done.")
print(f"Output file: {output_file}")
print(f"Summary file: {summary_file}")
print(f"Category mapping table file: {category_mapping_table_file}")
print(f"Regex table file: {regex_table_file}")
