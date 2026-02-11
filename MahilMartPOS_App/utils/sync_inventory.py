import pyodbc
import psycopg2
from psycopg2.extras import execute_batch
import datetime

print("🔗 Connecting to MSSQL...")

# -----------------------------
# MSSQL CONNECT
# -----------------------------
try:
    mssql = pyodbc.connect(
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=192.168.0.113,1433;"
        "Database=MahilMart-Analytics;"
        "Uid=mahilmartuser;"
        "Pwd=Admin@123;"
        "Trusted_Connection=no;"
        "TrustServerCertificate=yes;"
    )
    m_cursor = mssql.cursor()
    print("✅ MSSQL Connected")
except Exception as e:
    print("❌ MSSQL Connection Failed:", e)
    exit()


print("🔗 Connecting to PostgreSQL...")

# -----------------------------
# POSTGRES CONNECT
# -----------------------------
try:
    pg = psycopg2.connect(
        host="localhost",
        database="mmpos",
        user="postgres",
        password="Praveen"
    )
    p_cursor = pg.cursor()
    print("✅ PostgreSQL Connected")
except Exception as e:
    print("❌ PostgreSQL Connection Failed:", e)
    exit()


# -----------------------------
# FETCH LATEST STOCK FROM MSSQL
# -----------------------------
print("📥 Fetching latest inventory from MSSQL...")

mssql_query = """
WITH LatestStock AS (
    SELECT 
        stk.Item_No,
        stk.CloseQ,
        ROW_NUMBER() OVER(
            PARTITION BY stk.Item_No ORDER BY stk.curYear DESC
        ) AS rn
    FROM [MahilMart-Analytics].[dbo].[StkItem_Table] stk
    WHERE stk.CloseQ > 0
)
SELECT 
    Item_No,
    CloseQ
FROM LatestStock
WHERE rn = 1;
"""

try:
    m_cursor.execute(mssql_query)
    rows = m_cursor.fetchall()
    print(f"📦 Total items fetched: {len(rows)}")
except Exception as e:
    print("❌ MSSQL Error:", e)
    exit()


# -----------------------------
# UPSERT INTO POSTGRES
# -----------------------------
print("📤 Syncing inventory into PostgreSQL...")

upsert_sql = """
INSERT INTO pos_inventory (item_no, close_qty, updated_at)
VALUES (%s, %s, NOW())
ON CONFLICT (item_no)
DO UPDATE SET 
    close_qty = EXCLUDED.close_qty,
    updated_at = NOW();
"""

try:
    execute_batch(p_cursor, upsert_sql, rows, page_size=500)
    pg.commit()
    print("✅ Inventory sync completed successfully.")

except Exception as e:
    pg.rollback()
    print("❌ PostgreSQL Sync Error:", e)


print("🎉 Live Inventory Sync Done.")
