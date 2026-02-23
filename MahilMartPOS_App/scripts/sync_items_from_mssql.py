import os
import django
import pyodbc
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MahilMartPOS.settings")
django.setup()

from MahilMartPOS_App.models import Item
from django.db import transaction
import logging

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("item-sync")

# ---------------------------
# MSSQL CONFIG
# ---------------------------
MSSQL_CONFIG = {
    "DRIVER": "ODBC Driver 17 for SQL Server",
    "SERVER": "192.168.0.113,1433",
    "DATABASE": "MahilMart-Analytics",
    "UID": "mahilmartuser",
    "PWD": "Admin@123",
}

def connect_mssql():
    conn_str = (
        f"DRIVER={{{MSSQL_CONFIG['DRIVER']}}};"
        f"SERVER={MSSQL_CONFIG['SERVER']};"
        f"DATABASE={MSSQL_CONFIG['DATABASE']};"
        f"UID={MSSQL_CONFIG['UID']};"
        f"PWD={MSSQL_CONFIG['PWD']};"
        f"TrustServerCertificate=yes;"
    )
    log.info("🔗 Connecting to MSSQL...")
    conn = pyodbc.connect(conn_str)
    log.info("✅ MSSQL connected")
    return conn


# ----------------------------------------------------
# MSSQL ITEM TABLE QUERY
# ----------------------------------------------------
ITEM_QUERY = """
SELECT 
    Item_No,
    Item_Name,
    ISNULL(Barcode, ''),
    ISNULL(Item_HSNSAC, ''),
    ISNULL(Item_Brand, ''),
    ISNULL(Item_Group, ''),
    ISNULL(Item_Unit, '')
FROM Item_Table
"""


# ----------------------------------------------------
# SANITIZE BARCODE
# ----------------------------------------------------
def normalize_barcode(bc):
    if not bc:
        return ""
    bc = str(bc).strip()
    bc = bc.replace("`", "").replace(";", "").replace(",", "").replace(" ", "")
    return bc


# ----------------------------------------------------
# MAIN SYNC FUNCTION
# ----------------------------------------------------
def sync_items():
    conn = connect_mssql()
    cursor = conn.cursor()

    log.info("📥 Fetching MSSQL items...")
    cursor.execute(ITEM_QUERY)
    rows = cursor.fetchall()

    log.info(f"📦 Total items in MSSQL: {len(rows)}")

    created = 0
    updated = 0
    skipped = 0

    with transaction.atomic():
        for r in rows:
            item_no = r[0]
            name = (r[1] or "").strip()
            barcode = normalize_barcode(r[2])
            hsn = (r[3] or "").strip()
            brand = (r[4] or "").strip()
            group = (r[5] or "").strip()
            unit = (r[6] or "").strip()

            if not barcode:
                skipped += 1
                continue

            item = Item.objects.filter(code=barcode).first()

            if item:
                # Update existing item
                item.name = name
                item.hsn = hsn
                item.brand = brand
                item.group = group
                item.unit = unit
                item.save()
                updated += 1
            else:
                # Create new item
                Item.objects.create(
                    code=barcode,
                    name=name,
                    hsn=hsn,
                    brand=brand,
                    group=group,
                    unit=unit
                )
                created += 1

    log.info("---------------------------------------------------")
    log.info(f"✅ ITEMS SYNC COMPLETED")
    log.info(f"🆕 Created: {created}")
    log.info(f"✏ Updated: {updated}")
    log.info(f"⛔ Skipped (no barcode): {skipped}")
    log.info("---------------------------------------------------")


# Run script
def run():
    sync_items()
