# MahilMartPOS_App/utils/sync_inventory_from_stock.py

import psycopg2
from decimal import Decimal

POSTGRES_PARAMS = {
    "host": "localhost",
    "user": "postgres",
    "password": "Praveen",
    "dbname": "mmpos",
}


def d(val):
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


def fetch_dict(cur, sql, key_idx=0, val_idx=1):
    cur.execute(sql)
    rows = cur.fetchall()
    data = {}
    for r in rows:
        key = r[key_idx]
        if key is None or str(key).strip() == "":
            continue
        data[str(key).strip()] = d(r[val_idx])
    return data


def compute_stock(cur):
    # PURCHASE
    purchase_sql = """
        SELECT
            i.code,
            COALESCE(SUM(pi.quantity), 0) AS purchased_qty
        FROM "MahilMartPOS_App_purchaseitem" pi
        JOIN "MahilMartPOS_App_item" i ON pi.item_id = i.id
        GROUP BY i.code
    """
    purchase_data = fetch_dict(cur, purchase_sql)

    # SALES
    sales_sql = """
        SELECT
            code,
            COALESCE(SUM(qty), 0) AS sold_qty
        FROM "MahilMartPOS_App_billingitem"
        GROUP BY code
    """
    sales_data = fetch_dict(cur, sales_sql)

    # SALE RETURNS
    sale_return_sql = """
        SELECT
            code,
            COALESCE(SUM(qty), 0) AS return_qty
        FROM "MahilMartPOS_App_salereturnitem"
        GROUP BY code
    """
    sale_return_data = fetch_dict(cur, sale_return_sql)

    all_codes = [
        c
        for c in (set(purchase_data.keys()) |
                  set(sales_data.keys()) |
                  set(sale_return_data.keys()))
        if c is not None and str(c).strip() != ""
    ]

    stock_result = {}

    for code in all_codes:
        purchased = purchase_data.get(code, Decimal("0"))
        sold = sales_data.get(code, Decimal("0"))
        returned = sale_return_data.get(code, Decimal("0"))

        stock = purchased - sold + returned

        stock_result[code] = stock

    return stock_result


def sync_inventory():
    print("🔗 Connecting to PostgreSQL...")
    conn = psycopg2.connect(**POSTGRES_PARAMS)
    cur = conn.cursor()

    print("📊 Computing stock (purchase - sales + returns)...")
    stock_map = compute_stock(cur)

    # Cache item.code -> id
    print("📥 Loading item id map...")
    cur.execute("""
        SELECT id, code
        FROM "MahilMartPOS_App_item"
    """)
    rows = cur.fetchall()
    code_to_id = {}
    for item_id, code in rows:
        if code is None or str(code).strip() == "":
            continue
        code_to_id[str(code).strip()] = item_id

    updated = 0
    skipped = 0

    print("📤 Writing stock into MahilMartPOS_App_inventory...")

    for code, stock in stock_map.items():
        item_id = code_to_id.get(code)
        if not item_id:
            skipped += 1
            continue

        try:
            cur.execute(
                """
                INSERT INTO "MahilMartPOS_App_inventory" (item_id, quantity)
                VALUES (%s, %s)
                ON CONFLICT (item_id)
                DO UPDATE SET
                    quantity = EXCLUDED.quantity
                """,
                (item_id, stock),
            )
            updated += 1
        except Exception as e:
            print(f"❌ Inventory upsert failed for code {code} (item_id={item_id}): {e}")

    conn.commit()

    print("\n==============================")
    print("   INVENTORY SYNC SUMMARY")
    print("==============================")
    print(f"Items updated in inventory : {updated}")
    print(f"Items skipped (no item_id) : {skipped}")
    print("==============================")
    print("Done.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    sync_inventory()
