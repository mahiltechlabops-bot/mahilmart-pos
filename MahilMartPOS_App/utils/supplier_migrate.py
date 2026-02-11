import pyodbc
import psycopg2
from psycopg2 import errors
from django.conf import settings


# -----------------------------------------------
# Clean helper
# -----------------------------------------------
def clean(v):
    if v is None:
        return None
    v = str(v).strip()
    if v in ("", ".", "None"):
        return None
    return v


# -----------------------------------------------
# MAIN MIGRATION FUNCTION
# -----------------------------------------------
def migrate_suppliers():
    print("🚀 Starting Supplier Migration from Ledger_Table")

    # ---------------------------
    # MSSQL connection
    # ---------------------------
    mssql_conn = pyodbc.connect(
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=192.168.0.113,1433;"
        "Database=MahilMart-Analytics;"
        "Uid=mahilmartuser;"
        "Pwd=Admin@123;"
        "Trusted_Connection=no;"
        "TrustServerCertificate=yes;"
    )
    mssql_cur = mssql_conn.cursor()

    # ---------------------------
    # PostgreSQL connection
    # ---------------------------
    pg_params = settings.DATABASES["default"]
    pg_conn = psycopg2.connect(
        host=pg_params["HOST"],
        user=pg_params["USER"],
        password=pg_params["PASSWORD"],
        dbname=pg_params["NAME"],
        port=pg_params.get("PORT", 5432),
    )
    pg_cur = pg_conn.cursor()

    # -----------------------------------------------
    # LOAD real supplier rows
    # -----------------------------------------------
    mssql_cur.execute("""
        SELECT
            Ledger_No,          -- supplier_id
            Ledger_Name,        -- name
            Ledger_Ph,          -- phone
            Ledger_EMail,       -- email
            Ledger_Add1,        -- address
            Ledger_GST,         -- gst_number
            Ledger_FSSAI,       -- fssai_number
            Ledger_PANNo,       -- pan_number
            Ledger_Remarks      -- notes
        FROM Ledger_Table
        WHERE Ledger_Under = 32
          AND Ledger_Name NOT LIKE '%Cash%'
    """)

    rows = mssql_cur.fetchall()
    print(f"📦 Found {len(rows)} suppliers")

    if not rows:
        print("⚠ No supplier data found! Nothing to migrate.")
        return 0

    # -----------------------------------------------
    # PG INSERT
    # -----------------------------------------------
    insert_sql = """
        INSERT INTO "MahilMartPOS_App_supplier"
        (supplier_id, name, phone, email, address, gst_number,
         fssai_number, pan_number, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    inserted = 0

    for row in rows:
        supplier_id = clean(row[0])
        name = clean(row[1])
        phone = clean(row[2])
        email = clean(row[3])
        address = clean(row[4])
        gst = clean(row[5])
        fssai = clean(row[6])
        pan = clean(row[7])
        notes = clean(row[8])

        if not name:
            name = "Unknown Supplier"

        try:
            pg_cur.execute(insert_sql, [
                supplier_id, name, phone, email, address,
                gst, fssai, pan, notes
            ])
            inserted += 1

        except errors.UniqueViolation:
            print(f"⚠ Duplicate supplier skipped: {supplier_id}")
            pg_conn.rollback()
            continue

        except Exception as e:
            print("❌ Insert error:", e)
            pg_conn.rollback()
            continue

    pg_conn.commit()
    print(f"✅ Successfully inserted {inserted} suppliers")

    pg_conn.close()
    mssql_conn.close()
    return inserted
