import pyodbc
import psycopg2
from psycopg2.extras import execute_batch

print("🔗 Connecting to MSSQL...")

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
    m_cur = mssql.cursor()
    print("✅ MSSQL Connected")
except Exception as e:
    print("❌ MSSQL Connection Failed:", e)
    exit()


print("🔗 Connecting to PostgreSQL...")

try:
    pg = psycopg2.connect(
        host="localhost",
        database="mmpos",
        user="postgres",
        password="Praveen"
    )
    p_cur = pg.cursor()
    print("✅ PostgreSQL Connected")
except Exception as e:
    print("❌ PostgreSQL Connection Failed:", e)
    exit()


print("📥 Fetching stock & item info from MSSQL...")

mssql_query = """
WITH LatestStock AS (
    SELECT 
        stk.Item_No,
        stk.CloseQ,
        ROW_NUMBER() OVER(
            PARTITION BY stk.Item_No ORDER BY stk.curYear DESC
        ) AS rn
    FROM [MahilMart-Analytics].[dbo].[StkItem_Table] stk
)
SELECT 
    s.Item_No,
    s.CloseQ,
    i.Item_Name,
    i.Item_Code,
    b.brand_Name,
    g.itemGroup_Name
FROM LatestStock s
LEFT JOIN [MahilMart-Analytics].[dbo].[Item_Table] i
    ON s.Item_No = i.Item_No
LEFT JOIN [MahilMart-Analytics].[dbo].[Brand_Table] b
    ON i.Item_Brand = b.Brand_No
LEFT JOIN [MahilMart-Analytics].[dbo].[ItemGroup_Table] g
    ON i.Item_Group = g.itemGroup_No
WHERE rn = 1;
"""

m_cur.execute(mssql_query)
rows = m_cur.fetchall()
print(f"📦 Items fetched: {len(rows)}")


print("📤 Syncing Inventory into PostgreSQL...")

for row in rows:
    item_no = str(row.Item_No)
    close_qty = row.CloseQ
    item_name = row.Item_Name
    brand_name = row.brand_Name
    group_name = row.itemGroup_Name
    code = row.Item_Code

    # 1️⃣ Check if the item exists in Inventory
    p_cur.execute("""
        SELECT id FROM "MahilMartPOS_App_inventory"
        WHERE code = %s
    """, (item_no,))  # mapping: Item_No → Inventory.code

    existing = p_cur.fetchone()

    # 2️⃣ If NOT exists → INSERT NEW ROW
    if not existing:
        p_cur.execute("""
            INSERT INTO "MahilMartPOS_App_inventory"
            (code, item_name, brand, "group", quantity)
            VALUES (%s, %s, %s, %s, %s)
        """, (item_no, item_name, brand_name, group_name, close_qty))

    # 3️⃣ Exists → UPDATE STOCK
    else:
        p_cur.execute("""
            UPDATE "MahilMartPOS_App_inventory"
            SET quantity = %s
            WHERE code = %s
        """, (close_qty, item_no))

pg.commit()
print("✅ Inventory Auto-Create + Stock Sync Completed Successfully!")

print("🎉 LIVE STOCK SYNC DONE.")
