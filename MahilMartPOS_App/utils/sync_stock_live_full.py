import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import sys

# ======================================================
# MSSQL CONFIG
# ======================================================
MSSQL_SERVER = "192.168.0.110"
MSSQL_PORT = 1433
MSSQL_DB = "MahilMart-Analytics"
MSSQL_USER = "mahilmartuser"
MSSQL_PASSWORD = "Admin@123"
MSSQL_DRIVER = "ODBC Driver 17 for SQL Server"

# ======================================================
# POSTGRES CONFIG
# ======================================================
PG_DB = "mmpos"
PG_USER = "postgres"
PG_PASSWORD = "Praveen"
PG_HOST = "localhost"
PG_PORT = "5432"

# ======================================================
# CONNECT TO MSSQL
# ======================================================
print("🔗 Connecting to MSSQL...")

mssql_url = URL.create(
    drivername="mssql+pyodbc",
    username=MSSQL_USER,
    password=MSSQL_PASSWORD,
    host=MSSQL_SERVER,
    port=MSSQL_PORT,
    database=MSSQL_DB,
    query={
        "driver": MSSQL_DRIVER,
        "TrustServerCertificate": "yes",
    },
)

mssql_engine = create_engine(mssql_url)

# ======================================================
# DISCOVER TABLES (IMPORTANT PART)
# ======================================================
print("🔍 Discovering possible tables...")

tables_query = """
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME
"""

tables_df = pd.read_sql(tables_query, mssql_engine)

# Filter useful tables
sales_tables = tables_df[tables_df["TABLE_NAME"].str.contains("sale|bill", case=False, regex=True)]
purchase_tables = tables_df[tables_df["TABLE_NAME"].str.contains("purch", case=False)]
item_tables = tables_df[tables_df["TABLE_NAME"].str.contains("item|prod|stock", case=False, regex=True)]

print("\n🔹 POSSIBLE SALES TABLES:")
print(sales_tables)

print("\n🔹 POSSIBLE PURCHASE TABLES:")
print(purchase_tables)

print("\n🔹 POSSIBLE ITEM / STOCK TABLES:")
print(item_tables)

print("\n✅ COPY ONE EXACT TABLE NAME FROM ABOVE")
print("👉 Then set it in the script and rerun")

mssql_engine.dispose()
sys.exit(0)
