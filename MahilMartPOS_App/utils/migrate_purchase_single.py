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

MSSQL_SCHEMA = "dbo"
MSSQL_TABLE = "ItemTrn_Table"   # ✅ REAL TRANSACTION TABLE

# ======================================================
# POSTGRES CONFIG
# ======================================================
PG_DB = "mmpos"
PG_USER = "postgres"
PG_PASSWORD = "Praveen"
PG_HOST = "localhost"
PG_PORT = "5432"

PG_TABLE = "item_transactions"

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
# CONNECT TO POSTGRES
# ======================================================
print("🔗 Connecting to PostgreSQL...")

pg_url = URL.create(
    drivername="postgresql+psycopg2",
    username=PG_USER,
    password=PG_PASSWORD,
    host=PG_HOST,
    port=PG_PORT,
    database=PG_DB,
)

pg_engine = create_engine(pg_url)

# ======================================================
# VERIFY TABLE EXISTS
# ======================================================
print("🔍 Verifying MSSQL table exists...")

check_query = f"""
SELECT COUNT(*) AS cnt
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = '{MSSQL_SCHEMA}'
AND TABLE_NAME = '{MSSQL_TABLE}'
"""

check_df = pd.read_sql(check_query, mssql_engine)

if check_df.iloc[0]["cnt"] == 0:
    print(f"❌ Table '{MSSQL_SCHEMA}.{MSSQL_TABLE}' NOT FOUND")
    sys.exit(1)

print(f"✅ Table found: {MSSQL_SCHEMA}.{MSSQL_TABLE}")

# ======================================================
# EXTRACT
# ======================================================
print("📤 Extracting data from MSSQL...")

query = f"""
SELECT *
FROM {MSSQL_SCHEMA}.{MSSQL_TABLE}
"""

df = pd.read_sql(query, mssql_engine)

print(f"📊 Rows fetched: {len(df)}")

if df.empty:
    print("⚠️ No transaction data found")
    sys.exit(0)

# ======================================================
# TRANSFORM
# ======================================================
print("🛠 Transforming data...")

# Normalize column names
df.columns = df.columns.str.lower()

# Handle NULL values safely
df.fillna(0, inplace=True)

# Convert date/time columns automatically
for col in df.columns:
    if "date" in col or "time" in col:
        try:
            df[col] = pd.to_datetime(df[col])
        except Exception:
            pass

# ======================================================
# LOAD
# ======================================================
print("📥 Loading data into PostgreSQL...")

df.to_sql(
    name=PG_TABLE,
    con=pg_engine,
    if_exists="replace",   # 🔴 FIRST RUN ONLY
    index=False,
    method="multi",
    chunksize=1000,
)

print("✅ Item transactions migrated successfully")

# ======================================================
# CLEANUP
# ======================================================
mssql_engine.dispose()
pg_engine.dispose()

print("🔒 Connections closed")
