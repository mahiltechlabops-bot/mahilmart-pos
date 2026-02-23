# MahilMartPOS_App/utils/calculate_stock_v2.py

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


def calculate_stock():
    print("🔗 Connecting to PostgreSQL...")
    conn = psycopg2.connect(**POSTGRES_PARAMS)
    cur = conn.cursor()

    # -------------------------------------------------
    # PURCHASED QTY  (by item.code)
    # -------------------------------------------------
    print("📥 Fetching purchase quantities...")
    purchase_sql = """
        SELECT
            i.code,
            COALESCE(SUM(pi.quantity), 0) AS purchased_qty
        FROM "MahilMartPOS_App_purchaseitem" pi
        JOIN "MahilMartPOS_App_item" i ON pi.item_id = i.id
        GROUP BY i.code
    """
    purchase_data = fetch_dict(cur, purchase_sql)

    # -------------------------------------------------
    # SOLD QTY  (BillingItem.qty)
    # -------------------------------------------------
    print("📤 Fetching sales quantities...")
    sales_sql = """
        SELECT
            code,
            COALESCE(SUM(qty), 0) AS sold_qty
        FROM "MahilMartPOS_App_billingitem"
        GROUP BY code
    """
    sales_data = fetch_dict(cur, sales_sql)

    # -------------------------------------------------
    # SALE RETURN QTY  (SaleReturnItem.qty)
    # -------------------------------------------------
    print("📥 Fetching sale return quantities...")
    sale_return_sql = """
        SELECT
            code,
            COALESCE(SUM(qty), 0) AS return_qty
        FROM "MahilMartPOS_App_salereturnitem"
        GROUP BY code
    """
    sale_return_data = fetch_dict(cur, sale_return_sql)

    # -------------------------------------------------
    # COMBINE: stock = purchase - sales + sale_returns
    # -------------------------------------------------
    all_codes = sorted(
        c for c in (set(purchase_data.keys()) |
                    set(sales_data.keys()) |
                    set(sale_return_data.keys()))
        if c is not None and str(c).strip() != ""
    )

    print("\n==============================")
    print("        FULL STOCK REPORT")
    print("==============================")

    stock_result = {}

    for code in all_codes:
        purchased = purchase_data.get(code, Decimal("0"))
        sold = sales_data.get(code, Decimal("0"))
        returned = sale_return_data.get(code, Decimal("0"))

        # If you really want: purchase - sales - returns, change the line below
        stock = purchased - sold + returned

        stock_result[code] = {
            "purchased": purchased,
            "sold": sold,
            "returned": returned,
            "stock": stock,
        }

        print(
            f"Item: {code:<15} "
            f"Purchased: {purchased}  Sold: {sold}  "
            f"Returns: {returned}  Stock: {stock}"
        )

    print("==============================")
    print("Done.")

    cur.close()
    conn.close()

    return stock_result


if __name__ == "__main__":
    calculate_stock()
