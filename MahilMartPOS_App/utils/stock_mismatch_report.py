# MahilMartPOS_App/utils/stock_mismatch_report.py

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


def stock_mismatch_report():
    print("🔗 Connecting to PostgreSQL...")
    conn = psycopg2.connect(**POSTGRES_PARAMS)
    cur = conn.cursor()

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

    print("\n==============================")
    print("      STOCK MISMATCH REPORT")
    print("==============================")

    neg_stock = []
    sold_without_purchase = []

    for code in sorted(all_codes):
        purchased = purchase_data.get(code, Decimal("0"))
        sold = sales_data.get(code, Decimal("0"))
        returned = sale_return_data.get(code, Decimal("0"))

        stock = purchased - sold + returned

        if stock < 0:
            neg_stock.append((code, purchased, sold, returned, stock))

        if purchased == 0 and (sold > 0 or returned > 0):
            sold_without_purchase.append((code, purchased, sold, returned, stock))

    print("\n🔻 NEGATIVE STOCK (stock < 0)")
    if not neg_stock:
        print("  None ✅")
    else:
        for code, p, s, r, st in neg_stock:
            print(
                f"  Item: {code:<15} "
                f"Purchased: {p}  Sold: {s}  Returns: {r}  Stock: {st}"
            )

    print("\n⚠️ SOLD / RETURNED BUT NEVER PURCHASED (purchase == 0)")
    if not sold_without_purchase:
        print("  None ✅")
    else:
        for code, p, s, r, st in sold_without_purchase:
            print(
                f"  Item: {code:<15} "
                f"Purchased: {p}  Sold: {s}  Returns: {r}  Stock: {st}"
            )

    print("\n==============================")
    print("Report complete.")
    print("==============================")

    cur.close()
    conn.close()


if __name__ == "__main__":
    stock_mismatch_report()
