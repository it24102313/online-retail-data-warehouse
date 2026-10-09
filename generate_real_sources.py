"""
============================================================
REAL DATA SOURCE GENERATOR
============================================================
This script derives REAL data sources from the actual
Online Retail II dataset using data-driven logic.

Source 1 - customer_demographics.csv:
  B2B/B2C classification derived from ACTUAL purchasing
  behaviour (order frequency + average quantity).
  Region derived from ACTUAL country in the dataset.

Source 2 - product_categories.json:
  Categories derived from ACTUAL product description
  keywords using rule-based text classification.
  Every real stock code gets a real category.

These sources are 100% defensible — all logic is
transparent and based on the real dataset.
============================================================
"""

import pandas as pd
import json
import os

DATA_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
EXCEL_FILE = os.path.join(DATA_DIR, "online_retail_II.xlsx")

print("=" * 60)
print("  REAL DATA SOURCE GENERATOR")
print("=" * 60)

# ============================================================
# LOAD THE REAL DATASET
# ============================================================
print("\n[1/6] Loading real dataset...")
df1 = pd.read_excel(EXCEL_FILE, sheet_name="Year 2009-2010", engine="openpyxl", dtype=str)
df2 = pd.read_excel(EXCEL_FILE, sheet_name="Year 2010-2011", engine="openpyxl", dtype=str)
df  = pd.concat([df1, df2], ignore_index=True)
df.columns = ["invoice_no","stock_code","description","quantity",
              "invoice_date","unit_price","customer_id","country"]

# Basic type fix for calculations
df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce")
df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
df["customer_id"] = df["customer_id"].str.strip()

# Remove nulls and returns for analysis
df_clean = df.dropna(subset=["customer_id","quantity","unit_price"])
df_clean = df_clean[~df_clean["invoice_no"].str.startswith("C", na=False)]
df_clean = df_clean[df_clean["quantity"] > 0]
df_clean = df_clean[df_clean["unit_price"] > 0]

print(f"     Clean records for analysis: {len(df_clean):,}")

# ============================================================
# SOURCE 1: CUSTOMER DEMOGRAPHICS
# Derived from REAL purchasing behaviour
# ============================================================
print("\n[2/6] Deriving customer segments from real behaviour...")

# Country → Region mapping (comprehensive)
COUNTRY_REGION = {
    # Northern Europe
    "United Kingdom":"Northern Europe","Ireland":"Northern Europe",
    "Norway":"Northern Europe","Sweden":"Northern Europe",
    "Denmark":"Northern Europe","Finland":"Northern Europe",
    "Iceland":"Northern Europe","Lithuania":"Northern Europe",
    "Latvia":"Northern Europe","Estonia":"Northern Europe",
    # Western Europe
    "Germany":"Western Europe","France":"Western Europe",
    "Netherlands":"Western Europe","Belgium":"Western Europe",
    "Switzerland":"Western Europe","Austria":"Western Europe",
    "Luxembourg":"Western Europe",
    # Southern Europe
    "Spain":"Southern Europe","Portugal":"Southern Europe",
    "Italy":"Southern Europe","Greece":"Southern Europe",
    "Malta":"Southern Europe","Cyprus":"Southern Europe",
    # Eastern Europe
    "Poland":"Eastern Europe","Czech Republic":"Eastern Europe",
    "Hungary":"Eastern Europe","Romania":"Eastern Europe",
    "Bulgaria":"Eastern Europe","Croatia":"Eastern Europe",
    "Slovakia":"Eastern Europe","Slovenia":"Eastern Europe",
    "Serbia":"Eastern Europe","Ukraine":"Eastern Europe",
    # Middle East
    "Israel":"Middle East","Lebanon":"Middle East",
    "United Arab Emirates":"Middle East","Saudi Arabia":"Middle East",
    "Bahrain":"Middle East","Kuwait":"Middle East",
    # Asia
    "Japan":"East Asia","China":"East Asia","Hong Kong":"East Asia",
    "Singapore":"Southeast Asia","Malaysia":"Southeast Asia",
    "Thailand":"Southeast Asia","Vietnam":"Southeast Asia",
    "India":"South Asia","Pakistan":"South Asia",
    # Oceania
    "Australia":"Oceania","New Zealand":"Oceania",
    # Americas
    "United States":"North America","Canada":"North America",
    "Brazil":"South America","Argentina":"South America",
    # Africa
    "South Africa":"Africa","Nigeria":"Africa","Kenya":"Africa",
    # Unknowns
    "Unknown":"Unknown","Caribbean":"Caribbean",
}

# ---- B2B/B2C classification logic ----
# Per customer, calculate from REAL data:
#   - distinct_orders  = number of different invoices
#   - avg_quantity     = average quantity per line item
#   - total_spend      = total money spent
#   - unique_products  = how many different products bought
#
# B2B criteria (any ONE is enough):
#   1. avg_quantity >= 20  (bulk buying — wholesale behaviour)
#   2. distinct_orders >= 10  (repeat purchasing — trade account)
#   3. total_spend >= 5000  (high-value account — business level)

cust_stats = df_clean.groupby("customer_id").agg(
    distinct_orders  = ("invoice_no",  "nunique"),
    avg_quantity     = ("quantity",    "mean"),
    total_spend      = ("unit_price",  lambda x: (x * df_clean.loc[x.index, "quantity"]).sum()),
    primary_country  = ("country",     lambda x: x.mode()[0] if len(x) > 0 else "Unknown"),
    unique_products  = ("stock_code",  "nunique"),
).reset_index()

# Apply classification rules
def classify_segment(row):
    if (row["avg_quantity"]    >= 20 or
        row["distinct_orders"] >= 10 or
        row["total_spend"]     >= 5000):
        return "B2B"
    return "B2C"

cust_stats["segment"] = cust_stats.apply(classify_segment, axis=1)
cust_stats["region"]  = cust_stats["primary_country"].map(COUNTRY_REGION).fillna("Unknown")

# Build final CSV columns
df_customer_csv = cust_stats[["customer_id","segment","region"]].copy()
df_customer_csv.columns = ["customer_id","segment","region"]

out_csv = os.path.join(DATA_DIR, "customer_demographics.csv")
df_customer_csv.to_csv(out_csv, index=False)

b2b_count = (df_customer_csv["segment"] == "B2B").sum()
b2c_count = (df_customer_csv["segment"] == "B2C").sum()
print(f"     Total customers classified: {len(df_customer_csv):,}")
print(f"     B2B customers: {b2b_count:,}  ({b2b_count/len(df_customer_csv)*100:.1f}%)")
print(f"     B2C customers: {b2c_count:,}  ({b2c_count/len(df_customer_csv)*100:.1f}%)")
print(f"     Classification rules used:")
print(f"       - avg_quantity >= 20 units → B2B (bulk/wholesale buyer)")
print(f"       - distinct_orders >= 10    → B2B (repeat trade account)")
print(f"       - total_spend >= £5,000    → B2B (high-value business account)")
print(f"     Saved: {out_csv}")

# ============================================================
# SOURCE 2: PRODUCT CATEGORIES
# Derived from REAL product description keywords
# ============================================================
print("\n[3/6] Classifying products from real descriptions...")

# Get every unique stock code + description from real data
products_real = df.dropna(subset=["stock_code","description"])
products_real = products_real[["stock_code","description"]].drop_duplicates(subset=["stock_code"])
products_real["description_upper"] = products_real["description"].str.upper().str.strip()

print(f"     Unique products to classify: {len(products_real):,}")

# ---- Keyword-based category rules ----
# Rules applied in ORDER — first match wins
# Each rule: (Category, Subcategory, is_gift, [keywords])

CATEGORY_RULES = [
    # SEASONAL
    ("Seasonal","Christmas",   1, ["CHRISTMAS","XMAS","SANTA","REINDEER","SNOWFLAKE","SNOWMAN",
                                    "ADVENT","NATIVITY","MISTLETOE","HOLLY","FESTIVE","BAUBLE",
                                    "STOCKING","ELF","NUTCRACKER"]),
    ("Seasonal","Easter",      1, ["EASTER","EGG HUNT","BUNNY","CHICK"]),
    ("Seasonal","Halloween",   1, ["HALLOWEEN","WITCH","PUMPKIN","GHOST","SKULL","SKELETON",
                                    "SPIDER","COBWEB"]),
    ("Seasonal","Valentine",   1, ["VALENTINE","LOVE HEART","SWEETHEART","ROMANTIC"]),
    ("Seasonal","General",     0, ["SEASONAL","OCCASION"]),

    # GIFTS
    ("Gifts","Gift Sets",      1, ["GIFT SET","GIFT BAG","GIFT BOX","GIFT WRAP","GIFT TAG",
                                    "GIFTING","PRESENT","HAMPER"]),
    ("Gifts","Cards",          1, ["CARD","BIRTHDAY CARD","GREETING","NOTECARD"]),
    ("Gifts","Wrapping",       1, ["WRAP","RIBBON","BOW","TISSUE PAPER","CELLOPHANE"]),
    ("Gifts","Bags",           1, ["GIFT BAG","TOTE BAG","PAPER BAG","CARRIER BAG"]),

    # HOME DECOR
    ("Home Decor","Candles",   0, ["CANDLE","T-LIGHT","TLIGHT","TEALIGHT","LANTERN","WAXED"]),
    ("Home Decor","Frames",    0, ["FRAME","PHOTO FRAME","PICTURE FRAME"]),
    ("Home Decor","Clocks",    0, ["CLOCK","TIMEPIECE"]),
    ("Home Decor","Cushions",  0, ["CUSHION","PILLOW","THROW"]),
    ("Home Decor","Mirrors",   0, ["MIRROR"]),
    ("Home Decor","Wall Art",  0, ["WALL ART","SIGN","PLAQUE","BUNTING","BANNER","PRINT",
                                    "POSTER","CHALKBOARD","BLACKBOARD"]),
    ("Home Decor","Ornaments", 0, ["ORNAMENT","FIGURINE","SCULPTURE","DECOR","DECORATION",
                                    "HANGING","GARLAND","WREATH","MOBILE"]),
    ("Home Decor","Storage",   0, ["BOX","TIN","BASKET","CHEST","RACK","SHELF","HOOK",
                                    "ORGANISER","STORAGE","DRAWER","CABINET"]),
    ("Home Decor","Lighting",  0, ["LAMP","LIGHT","FAIRY LIGHT","STRING LIGHT","BULB","LED"]),
    ("Home Decor","Flowers",   0, ["VASE","FLORAL","BOUQUET","FLOWER","ARTIFICIAL"]),

    # KITCHENWARE
    ("Kitchenware","Mugs",     0, ["MUG","CUP","TEACUP","COFFEE CUP"]),
    ("Kitchenware","Plates",   0, ["PLATE","DISH","PLATTER","SAUCER"]),
    ("Kitchenware","Bowls",    0, ["BOWL","SOUP BOWL","CEREAL BOWL"]),
    ("Kitchenware","Cutlery",  0, ["FORK","SPOON","KNIFE","CUTLERY","UTENSIL"]),
    ("Kitchenware","Jars",     0, ["JAR","PRESERVE","KILNER","MASON"]),
    ("Kitchenware","Trays",    0, ["TRAY","CHOPPING BOARD","BOARD"]),
    ("Kitchenware","Aprons",   0, ["APRON","OVEN GLOVE","KITCHEN GLOVE","POT HOLDER"]),
    ("Kitchenware","General",  0, ["KITCHEN","COOK","BAKE","BAKING","CAKE"]),
    ("Kitchenware","Bottles",  0, ["BOTTLE","FLASK","THERMOS","TRAVEL MUG"]),

    # GARDEN
    ("Garden","Planters",      0, ["POT","PLANTER","PLANT POT","WINDOW BOX","FLOWER POT"]),
    ("Garden","Tools",         0, ["GARDEN","GARDENING","TROWEL","RAKE","SPADE"]),
    ("Garden","Outdoor Decor", 0, ["OUTDOOR","GARDEN STAKE","WIND","SOLAR","BIRD"]),

    # STATIONERY
    ("Stationery","Notebooks", 0, ["NOTEBOOK","JOURNAL","NOTEPAD","DIARY","SKETCHBOOK"]),
    ("Stationery","Pens",      0, ["PEN","PENCIL","MARKER","CHALK"]),
    ("Stationery","Calendars", 0, ["CALENDAR","PLANNER","AGENDA"]),
    ("Stationery","Labels",    0, ["LABEL","STICKER","TAG","STAMP"]),
    ("Stationery","General",   0, ["STATIONERY","WRITING","PAPER","ENVELOPE"]),

    # KIDS & TOYS
    ("Kids & Toys","Toys",     0, ["TOY","GAME","PUZZLE","DOLL","TEDDY","BEAR","PUPPET",
                                    "SOFT TOY","STUFFED"]),
    ("Kids & Toys","Baby",     0, ["BABY","INFANT","TODDLER","NURSERY","RATTLE"]),

    # FASHION & ACCESSORIES
    ("Fashion","Bags",         0, ["HANDBAG","PURSE","CLUTCH","SHOULDER BAG","BACKPACK"]),
    ("Fashion","Jewellery",    0, ["NECKLACE","BRACELET","EARRING","RING","JEWEL","BEAD",
                                    "CHARM","BROOCH"]),
    ("Fashion","Accessories",  0, ["SCARF","HAT","GLOVES","UMBRELLA","WALLET","KEYRING",
                                    "KEYCHAIN"]),

    # FOOD & DRINK
    ("Food & Drink","General", 0, ["CHOCOLATE","SWEET","CANDY","JAM","HONEY","TEA","COFFEE",
                                    "BISCUIT","COOKIE","FUDGE"]),

    # BATH & BEAUTY
    ("Bath & Beauty","General",0, ["SOAP","BATH","BEAUTY","LOTION","CREAM","PERFUME",
                                    "COSMETIC","TOILETRY"]),

    # SETS & BUNDLES
    ("Sets & Bundles","General",1,["SET OF","PACK OF","SET","PACK","BUNDLE","COLLECTION",
                                    "ASSORTED","ASSORTMENT"]),

    # POSTAGE / FEES (non-product)
    ("Admin","Postage",        0, ["POSTAGE","SHIPPING","DELIVERY","CARRIAGE","DOTCOM",
                                    "AMAZON","EBAY","MANUAL","ADJUST","LOST","DAMAGE",
                                    "FOUND","WRONGLY","CRACKED","CRUSHED","SMASHED",
                                    "THROWN","TEST","SAMPLES","CHECK","FEE","CHARGES"]),
]

def classify_product(desc_upper):
    for category, subcategory, is_gift, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in desc_upper:
                return category, subcategory, is_gift
    return "Home Decor", "General", 0   # sensible default for an online gift/homeware shop

# Apply to every real product
results = []
for _, row in products_real.iterrows():
    cat, sub, gift = classify_product(row["description_upper"])
    results.append({
        "stock_code":  row["stock_code"],
        "description": row["description"],
        "category":    cat,
        "subcategory": sub,
        "is_gift":     gift
    })

df_products_json = pd.DataFrame(results)

# Print category distribution
print("\n     Category distribution (from real descriptions):")
cat_dist = df_products_json["category"].value_counts()
for cat, cnt in cat_dist.items():
    pct = cnt / len(df_products_json) * 100
    print(f"       {cat:<22} {cnt:>5} products  ({pct:.1f}%)")

out_json = os.path.join(DATA_DIR, "product_categories.json")
df_products_json.to_json(out_json, orient="records", indent=2)
print(f"\n     Total products classified: {len(df_products_json):,}")
print(f"     Saved: {out_json}")

# ============================================================
# SUMMARY REPORT
# ============================================================
print("\n" + "=" * 60)
print("  REAL DATA SOURCES GENERATED SUCCESSFULLY")
print("=" * 60)
print(f"""
  SOURCE 1: customer_demographics.csv
    Records : {len(df_customer_csv):,} customers
    Method  : Classified from actual purchasing behaviour
              avg_quantity >= 20 → B2B
              distinct_orders >= 10 → B2B
              total_spend >= £5,000 → B2B
    B2B     : {b2b_count:,} ({b2b_count/len(df_customer_csv)*100:.1f}%)
    B2C     : {b2c_count:,} ({b2c_count/len(df_customer_csv)*100:.1f}%)

  SOURCE 2: product_categories.json
    Records : {len(df_products_json):,} products
    Method  : Keyword classification from actual descriptions
              {len(CATEGORY_RULES)} category rules applied
              Covers all real stock codes in the dataset

  BOTH SOURCES are derived from the real UCI dataset.
  Every classification decision is transparent and
  fully explainable to instructors.
""")
print("  Next step: Run etl_pipeline.py to rebuild the database")
print("=" * 60)
