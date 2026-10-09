"""
Product category classification from REAL descriptions.
Runs the product JSON generation only (customer CSV already done).
"""
import pandas as pd
import json, os

DATA_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
EXCEL_FILE = os.path.join(DATA_DIR, "online_retail_II.xlsx")

print("Loading real dataset for product classification...")
df1 = pd.read_excel(EXCEL_FILE, sheet_name="Year 2009-2010", engine="openpyxl", dtype=str)
df2 = pd.read_excel(EXCEL_FILE, sheet_name="Year 2010-2011", engine="openpyxl", dtype=str)
df  = pd.concat([df1, df2], ignore_index=True)
df.columns = ["invoice_no","stock_code","description","quantity",
              "invoice_date","unit_price","customer_id","country"]

# Every unique real product
products_real = df.dropna(subset=["stock_code","description"])
products_real = products_real[["stock_code","description"]].drop_duplicates(subset=["stock_code"])
products_real["desc_upper"] = products_real["description"].str.upper().str.strip()
print(f"Unique products to classify: {len(products_real):,}")

# Keyword rules — (Category, Subcategory, is_gift, [keywords])
RULES = [
    ("Seasonal","Christmas",    1, ["CHRISTMAS","XMAS","SANTA","REINDEER","SNOWFLAKE",
                                     "SNOWMAN","ADVENT","NATIVITY","MISTLETOE","HOLLY",
                                     "FESTIVE","BAUBLE","STOCKING","ELF","NUTCRACKER"]),
    ("Seasonal","Easter",       1, ["EASTER","EGG HUNT","BUNNY","CHICK"]),
    ("Seasonal","Halloween",    1, ["HALLOWEEN","WITCH","PUMPKIN","GHOST","SKULL",
                                     "SKELETON","SPIDER","COBWEB"]),
    ("Seasonal","Valentine",    1, ["VALENTINE","LOVE HEART","SWEETHEART","ROMANTIC"]),
    ("Gifts","Gift Sets",       1, ["GIFT SET","GIFT BAG","GIFT BOX","GIFT WRAP",
                                     "GIFT TAG","GIFTING","HAMPER"]),
    ("Gifts","Cards",           1, ["BIRTHDAY CARD","GREETING CARD","NOTECARD"]),
    ("Gifts","Wrapping",        1, ["RIBBON","BOW","TISSUE PAPER","CELLOPHANE"]),
    ("Home Decor","Candles",    0, ["CANDLE","T-LIGHT","TLIGHT","TEALIGHT","LANTERN"]),
    ("Home Decor","Frames",     0, ["PHOTO FRAME","PICTURE FRAME"]),
    ("Home Decor","Clocks",     0, ["CLOCK","TIMEPIECE"]),
    ("Home Decor","Cushions",   0, ["CUSHION","PILLOW","THROW"]),
    ("Home Decor","Wall Art",   0, ["WALL ART","SIGN","PLAQUE","BUNTING","BANNER",
                                     "CHALKBOARD","BLACKBOARD"]),
    ("Home Decor","Ornaments",  0, ["ORNAMENT","FIGURINE","HANGING","GARLAND",
                                     "WREATH","MOBILE","DECORATION"]),
    ("Home Decor","Storage",    0, ["TRINKET BOX","STORAGE BOX","KEEPSAKE BOX",
                                     "CHEST","RACK","HOOK","ORGANISER","DRAWER"]),
    ("Home Decor","Lighting",   0, ["LAMP","FAIRY LIGHT","STRING LIGHT","LED"]),
    ("Home Decor","Flowers",    0, ["VASE","FLORAL","BOUQUET","ARTIFICIAL FLOWER"]),
    ("Kitchenware","Mugs",      0, ["MUG","TEACUP","COFFEE CUP"]),
    ("Kitchenware","Plates",    0, ["PLATE","PLATTER","SAUCER"]),
    ("Kitchenware","Bowls",     0, ["BOWL"]),
    ("Kitchenware","Cutlery",   0, ["FORK","SPOON","CUTLERY","UTENSIL"]),
    ("Kitchenware","Jars",      0, ["JAR","KILNER","MASON"]),
    ("Kitchenware","Trays",     0, ["TRAY","CHOPPING BOARD"]),
    ("Kitchenware","Aprons",    0, ["APRON","OVEN GLOVE","POT HOLDER"]),
    ("Kitchenware","Bottles",   0, ["BOTTLE","FLASK","THERMOS","TRAVEL MUG"]),
    ("Kitchenware","General",   0, ["KITCHEN","BAKING","CAKE TIN"]),
    ("Garden","Planters",       0, ["PLANT POT","WINDOW BOX","FLOWER POT","PLANTER"]),
    ("Garden","Tools",          0, ["GARDENING","TROWEL","RAKE"]),
    ("Garden","Outdoor",        0, ["OUTDOOR","GARDEN STAKE","SOLAR","BIRD FEEDER"]),
    ("Stationery","Notebooks",  0, ["NOTEBOOK","JOURNAL","NOTEPAD","DIARY","SKETCHBOOK"]),
    ("Stationery","Pens",       0, ["PENCIL","MARKER","CHALK"]),
    ("Stationery","Calendars",  0, ["CALENDAR","PLANNER","AGENDA"]),
    ("Stationery","Labels",     0, ["LABEL","STICKER","STAMP"]),
    ("Kids & Toys","Toys",      0, ["TOY","PUZZLE","DOLL","TEDDY","PUPPET","SOFT TOY"]),
    ("Kids & Toys","Baby",      0, ["BABY","INFANT","TODDLER","NURSERY","RATTLE"]),
    ("Fashion","Jewellery",     0, ["NECKLACE","BRACELET","EARRING","BROOCH","BEAD","CHARM"]),
    ("Fashion","Accessories",   0, ["SCARF","UMBRELLA","WALLET","KEYRING","KEYCHAIN"]),
    ("Bath & Beauty","General", 0, ["SOAP","BATH BOMB","LOTION","COSMETIC","TOILETRY"]),
    ("Sets & Bundles","General",1, ["SET OF","PACK OF","ASSORTED","ASSORTMENT","BUNDLE"]),
    ("Admin","Postage",         0, ["POSTAGE","SHIPPING","DOTCOM","AMAZON","MANUAL",
                                     "ADJUST","LOST","DAMAGE","FOUND","WRONGLY",
                                     "CRACKED","CRUSHED","TEST","SAMPLES","FEE"]),
]

def classify(desc):
    for cat, sub, gift, kws in RULES:
        for kw in kws:
            if kw in desc:
                return cat, sub, gift
    return "Home Decor", "General", 0

records = []
for _, row in products_real.iterrows():
    cat, sub, gift = classify(row["desc_upper"])
    records.append({
        "stock_code":  row["stock_code"],
        "description": row["description"],
        "category":    cat,
        "subcategory": sub,
        "is_gift":     gift
    })

df_out = pd.DataFrame(records)

print("\nCategory distribution (from REAL descriptions):")
for cat, cnt in df_out["category"].value_counts().items():
    pct = cnt/len(df_out)*100
    bar = "#" * int(pct/2)
    print(f"  {cat:<22} {cnt:>5}  ({pct:5.1f}%)  {bar}")

out = os.path.join(DATA_DIR, "product_categories.json")
df_out.to_json(out, orient="records", indent=2)
print(f"\nSaved: {out}")
print(f"Total products classified: {len(df_out):,}")
print("\nBoth real data sources are ready!")
print("Next step: run etl_pipeline.py to rebuild the database")
