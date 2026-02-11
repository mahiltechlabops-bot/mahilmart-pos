import psycopg2
from decimal import Decimal

POSTGRES_PARAMS = {
    "host": "localhost",
    "user": "postgres",
    "password": "Praveen",
    "dbname": "mmpos",
}

def update_stock():
    print("🔗 Connecting to PostgreSQL...")
    conn = psycopg2.connect(**POSTGRES_PARAMS)
    cur = conn.cursor()

    # -----------------------------------------------
    # 1) Get total purchased qty per item_id
    # -----------------------------------------------
    print("📦 Fetching purchase quantities...")

    cur.execute("""
        SELECT item_id, SUM(total_qty)
        FROM "MahilMartPOS_App_purchaseitem"
        GROUP BY item_id
        ORDER BY item_id
    """)

    results = cur.fetchall()
    print(f"📊 Found {len(results)} items with purchase quantities.")

    # -----------------------------------------------
    # 2) Update item table
    # -----------------------------------------------
    updated = 0

    for item_id, qty in results:
        qty = qty or 0

        try:
            cur.execute(
                '''
                UPDATE "MahilMartPOS_App_item"
                SET min_stock = %s
                WHERE id = %s
                ''',
                (str(qty), item_id)
            )
            updated += 1
        except Exception as e:
            print(f"❌ Failed to update item {item_id}: {e}")
            conn.rollback()
            continue

    conn.commit()

    # -----------------------------------------------
    # Summary
    # -----------------------------------------------
    print("\n==============================")
    print(" STOCK UPDATE SUMMARY")
    print("==============================")
    print(f"✓ Items updated : {updated}")
    print("==============================")
    print("🎉 Done.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    update_stock()
