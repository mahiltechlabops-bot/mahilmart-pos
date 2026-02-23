import psycopg2
from decimal import Decimal

POSTGRES = {
    "host": "localhost",
    "user": "postgres",
    "password": "Praveen",
    "dbname": "mmpos"
}


def calculate_stock():
    print("🔗 Connecting to PostgreSQL...")
    conn = psycopg2.connect(**POSTGRES)
    cur = conn.cursor()

    # =====================================================
    # 1) PURCHASE QTY
    # =====================================================
    print("📥 Fetching purchase quantities...")

    cur.execute("""
        SELECT 
            code,
            COALESCE(SUM(quantity), 0) AS purchased_qty
        FROM "MahilMartPOS_App_purchaseitem"
        GROUP BY code
    """)

    purchase_data = {}
    for code, qty in cur.fetchall():
        if code is None:
            continue  # skip NULL codes
        purchase_data[code] = Decimal(qty)

    # =====================================================
    # 2) SALES QTY
    # =====================================================
    print("📤 Fetching sales quantities...")

    cur.execute("""
        SELECT 
            code,
            COALESCE(SUM(qty), 0) AS sold_qty
        FROM "MahilMartPOS_App_billingitem"
        GROUP BY code
    """)

    sales_data = {}
    for code, qty in cur.fetchall():
        if code is None:
            continue  # skip NULL codes
        sales_data[code] = Decimal(qty)

    # =====================================================
    # 3) MERGE STOCK DATA
    # =====================================================
    all_codes = sorted(set(purchase_data.keys()) | set(sales_data.keys()))

    print("\n==============================")
    print("        FULL STOCK REPORT")
    print("==============================")

    for code in all_codes:
        purchased = purchase_data.get(code, Decimal("0"))
        sold = sales_data.get(code, Decimal("0"))
        stock = purchased - sold

        print(f"Item: {code:<15} Purchased: {purchased}  Sold: {sold}  Stock: {stock}")

    print("==============================")
    print("Done.")

    conn.close()


if __name__ == "__main__":
    calculate_stock()
