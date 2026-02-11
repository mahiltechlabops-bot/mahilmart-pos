import pyodbc
import psycopg2
from psycopg2.extras import execute_batch
import time

print("🔗 Connecting to MSSQL...")

# -----------------------------
# MSSQL CONNECTION
# -----------------------------
try:
    mssql_conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=192.168.0.113,1433;"
        "DATABASE=MahilMart-Analytics;"
        "UID=mahilmartuser;"
        "PWD=Admin@123;"
        "TrustServerCertificate=yes;"
    )
    mssql_cur = mssql_conn.cursor()
    print("✅ MSSQL connected successfully.")
except Exception as e:
    print(f"❌ MSSQL connection failed: {e}")
    exit()

print("🔗 Connecting to PostgreSQL...")

# -----------------------------
# POSTGRES CONNECTION
# -----------------------------
try:
    pg_conn = psycopg2.connect(
        host="localhost",
        user="postgres",
        password="Praveen",
        dbname="mmpos"
    )
    pg_cur = pg_conn.cursor()
    print("✅ PostgreSQL connected successfully.")
except Exception as e:
    print(f"❌ PostgreSQL connection failed: {e}")
    exit()

print("📥 Fetching latest purchase records...")

# -----------------------------
# FETCH LATEST PURCHASE PER ITEM
# -----------------------------
mssql_query = """
WITH LatestPurchase AS (
    SELECT
        p.Item_No,
        p.Purchase_Qty,
        p.Purchase_Rate,
        p.Invoice_No,
        p.Supplier_No,
        p.Purchase_Date,
        ROW_NUMBER() OVER(
            PARTITION BY p.Item_No
            ORDER BY p.Purchase_Date DESC
        ) AS rn
    FROM [MahilMart-Analytics].[dbo].[Purchase_Table] p
    WHERE p.Purchase_Qty > 0
)
SELECT
    lp.Item_No,
    lp.Purchase_Qty,
    lp.Purchase_Rate,
    lp.Invoice_No,
    lp.Supplier_No,
    lp.Purchase_Date
FROM LatestPurchase lp
WHERE lp.rn = 1;
"""

try:
    mssql_cur.execute(mssql_query)
    purchase_rows = mssql_cur.fetchall()
    print(f"📦 Total purchase items fetched: {len(purchase_rows)}")
except Exception as e:
    print(f"❌ Error fetching purchase data: {e}")
    exit()

# -----------------------------
# UPSERT INTO POSTGRES TABLE
# -----------------------------
print("📤 Writing purchase data into pos_purchase table...")

insert_sql = """
INSERT INTO pos_purchase (
    item_no,
    purchase_qty,
    purchase_rate,
    invoice_no,
    supplier_no,
    purchase_date
)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (item_no)
DO UPDATE SET
    purchase_qty = EXCLUDED.purchase_qty,
    purchase_rate = EXCLUDED.purchase_rate,
    invoice_no = EXCLUDED.invoice_no,
    supplier_no = EXCLUDED.supplier_no,
    purchase_date = EXCLUDED.purchase_date;
"""

try:
    execute_batch(pg_cur, insert_sql, purchase_rows, page_size=500)
    pg_conn.commit()
    print("✅ Purchase transfer completed successfully.")
except Exception as e:
    print(f"❌ Error inserting purchase data: {e}")
    pg_conn.rollback()

print("🎉 Done.")
