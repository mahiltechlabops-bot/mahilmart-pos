# MahilMartPOS_App/utils/bulk_migrate.py

import pyodbc
import psycopg2

# ---------------------------------------
# DB SETTINGS (adjust if needed)
# ---------------------------------------
MSSQL_CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=192.168.0.113;"
    "Database=MahilMart-Analytics;"
    "Uid=mahilmartuser;"
    "Pwd=Admin@123;"
    "Trusted_Connection=no;"
    "TrustServerCertificate=yes;"
)

POSTGRES_PARAMS = {
    "host": "localhost",
    "user": "postgres",
    "password": "Praveen",
    "dbname": "mmpos",
}

# MSSQL tables we do NOT touch here (handled specially elsewhere)
SKIP_MSSQL_TABLES = {
    "Ledger_Table",   # used by supplier_migrate.py
    "Supplier_Table", # empty, we already checked
}

# =====================================================
# SPECIAL COLUMN MAPPINGS
# =====================================================
# mssql_table -> { mssql_column : pg_column }
#
# These are for tables where the column names are different
# between MSSQL and PostgreSQL.
SPECIAL_COLUMN_MAPPINGS = {
    "Brand_Table": {
        # MSSQL -> PG
        # Brand_No goes into PG id (auto) so we ignore it.
        "Brand_Name": "brand_name",
        "Brand_Alias": "alias_name",
        "Brand_Under": "under",
        "Brand_PrintName": "print_name",
    },
    "Category_Table": {
        "Category_Name": "name",
    },
    "Counter_Table": {
        # Counter_No = our logical counter_id
        "Counter_No": "counter_id",
        "Counter_Name": "counter_name",
    },
    "Item_Table": {
        # Item_No -> PG id (auto), so we ignore it.
        "Item_Code": "code",
        "Item_Name": "item_name",
        "Print_Name": "print_name",
        "Item_Active": "status",
        "Item_Unit": "unit",
        "Item_SUnit": "P_unit",
        "Item_Group": "group",
        "Item_Brand": "brand",
        "Item_Tax": "tax",
        "Item_HSNSAC": "HSN_SAC",
        "Item_PurRate": "P_rate",
        "Item_CostRate": "cost_rate",
        "Item_MrspRate": "MRSP",
        "Item_SalRate1": "sale_rate",
        "Item_SalRate2": "whole_rate",
        "Item_SalRate3": "whole_rate_2",
        "Item_Point": "points",
        "Item_CessPerQty": "cess_per_qty",
        "Item_Picture": "picture",
        # extra stock-related mappings
        "Item_MinStk": "min_stock",
        "Item_StkItem": "stock_item",
        # if MSSQL really has these, they will be used;
        # otherwise they are ignored and defaults will kick in:
        "Item_CarryOver": "carry_over",
        "Item_Manual": "manual",
        "Item_UseMRP": "use_MRP",
        "Item_UseMrp": "use_MRP",  # in case of different casing
    },
    "Tax_Table": {
        "Tax_Name": "tax_name",
        "Tax_PrintName": "print_name",
        "Tax_TypeNo": "tax_type",
        "Tax_FromDate": "effect_form",
        "Tax_Round": "rounded",
        "Tax_GSTType": "gst_type",
        "Tax_CessPer": "cess_percent",
        "Tax_SGSTPer": "sgst_percent",
        "Tax_CGSTPer": "cgst_percent",
        "Tax_RoundType": "round_type",
        # Rough but usable mapping for the account columns:
        "Tax_SGSTSalLedgerNo": "sgst_sales_account_1",
        "Tax_SGSTSalCLedgerNo": "sgst_sales_account_2",
        "Tax_SGSTSalRevLedgerNo": "sgst_sales_return_1",
        "Tax_SGSTSalRevCLedgerNo": "sgst_sales_return_2",
        "Tax_SGSTPurLedgerNo": "sgst_purchase_account_1",
        "Tax_SGSTPurCLedgerNo": "sgst_purchase_account_2",
        "Tax_SGSTPurRevLedgerNo": "sgst_purchase_return_1",
        "Tax_SGSTPurRevCLedgerNo": "sgst_purchase_return_2",

        "Tax_CGSTSalLedgerNo": "cgst_sales_account_1",
        "Tax_CGSTSalCLedgerNo": "cgst_sales_account_2",
        "Tax_CGSTSalRevLedgerNo": "cgst_sales_return_1",
        "Tax_CGSTSalRevCLedgerNo": "cgst_sales_return_2",
        "Tax_CGSTPurLedgerNo": "cgst_purchase_account_1",
        "Tax_CGSTPurCLedgerNo": "cgst_purchase_account_2",
        "Tax_CGSTPurRevLedgerNo": "cgst_purchase_return_1",
        "Tax_CGSTPurRevCLedgerNo": "cgst_purchase_return_2",
    },
    "Unit_Table": {
        "Unit_Name": "unit_name",
        "Unit_PrintName": "print_name",
        "Unit_Decimal": "decimals",
        "Unit_UQC": "UQC",
    },
}

# =====================================================
# SPECIAL CONSTANT VALUES FOR PG COLUMNS
# =====================================================
# When MSSQL doesn't have a source column, or the value is NULL/empty,
# we can still satisfy NOT NULL constraints by using these defaults.
#
# Keys: MSSQL table name  ->  { pg_column : default_value }
SPECIAL_CONSTANTS = {
    # ---- BRAND ----
    "Brand_Table": {
        # alias_name & print_name are NOT NULL in PG but in MSSQL
        # they are often just ' ' (single space). clean_value() will
        # turn that into None, so we supply safe defaults.
        "alias_name": "",
        "print_name": "",
    },

    # ---- ITEM ----
    "Item_Table": {
        # NOT NULL flags in PG, but MSSQL may not have matching columns
        "use_MRP": False,      # default: do not use MRP
        "min_stock": 0,        # safe minimum stock
        "stock_item": True,    # most items are stock items
        "carry_over": False,
        "manual": False,
        # If for some rows picture / barcode / other come as NULL,
        # we'll replace with empty strings instead of NULL.
        "picture": "",
        "barcode": "",
        "other": "",
    },
    # you can add more table-specific defaults here if needed
}

# =====================================================
# UTILS
# =====================================================
def clean_value(value):
    """Normalize MSSQL values for PostgreSQL."""
    if value in ["", None, " "]:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def get_mssql_tables(conn):
    """Return list of all user tables in MSSQL."""
    cur = conn.cursor()
    cur.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    return [r[0] for r in cur.fetchall()]


def get_mssql_columns(cur, table_name):
    cur.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
    """, (table_name,))
    return [r[0] for r in cur.fetchall()]


def get_pg_columns(cur, table_name):
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name=%s
        ORDER BY ordinal_position
    """, [table_name])
    return [r[0] for r in cur.fetchall()]


def build_pg_suffix_map(cur):
    """
    Map suffix -> full PG table name.
    Example: "supplier" -> "MahilMartPOS_App_supplier"
    """
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
    """)
    suffix_map = {}

    for (table_name,) in cur.fetchall():
        # Only care about your app tables
        if table_name.startswith("MahilMartPOS_App_"):
            suffix = table_name[len("MahilMartPOS_App_"):].lower()
            suffix_map[suffix] = table_name

    return suffix_map


def get_common_mapping(mssql_cur, pg_cur, m_table, pg_table):
    """
    Return mapping dict: mssql_col -> pg_col
    for columns that exist in both, ignoring 'id'.
    """
    m_cols = get_mssql_columns(mssql_cur, m_table)
    pg_cols = get_pg_columns(pg_cur, pg_table)

    m_lower = {c.lower(): c for c in m_cols}
    pg_lower = {c.lower(): c for c in pg_cols}

    mapping = {}

    # 1) default "same-name" mapping
    for name_lower, m_orig in m_lower.items():
        if name_lower == "id":
            continue
        if name_lower in pg_lower:
            pg_orig = pg_lower[name_lower]
            if pg_orig.lower() == "id":
                continue
            mapping[m_orig] = pg_orig

    # 2) apply SPECIAL_COLUMN_MAPPINGS overrides/additions
    special = SPECIAL_COLUMN_MAPPINGS.get(m_table)
    if special:
        print(f"  🔧 Using special column mapping for {m_table}")
        for m_col, pg_col in special.items():
            # Only add if BOTH:
            #   - MSSQL column exists
            #   - PG column exists
            if (m_col in m_cols) and (pg_col in pg_cols):
                mapping[m_col] = pg_col
            else:
                # helpful debug
                missing_side = []
                if m_col not in m_cols:
                    missing_side.append(f"MSSQL.{m_col}")
                if pg_col not in pg_cols:
                    missing_side.append(f"PG.{pg_col}")
                missing_str = " & ".join(missing_side)
                print(f"    ⚠️ Skipping mapping {m_col} → {pg_col} (missing: {missing_str})")

    return mapping


# =====================================================
# CORE MIGRATION FOR ONE TABLE
# =====================================================
def migrate_one_table(mssql_conn, pg_conn, m_table, pg_table, truncate_first=False):
    """
    Generic migration: MSSQL m_table -> PG pg_table
    Only common columns (by name or special mapping) are migrated.
    Also uses SPECIAL_CONSTANTS to fill some NOT NULL PG columns.
    Returns number of inserted rows.
    """

    print(f"\n🚀 MIGRATE TABLE: {m_table} → {pg_table}")

    m_cur = mssql_conn.cursor()
    p_cur = pg_conn.cursor()

    # Count MSSQL rows first
    try:
        m_cur.execute(f"SELECT COUNT(*) FROM [{m_table}]")
        total_rows = m_cur.fetchone()[0]
        print(f"  📦 MSSQL rows in {m_table}: {total_rows}")
    except Exception as e:
        print(f"  ❌ Failed to count rows for {m_table}: {e}")
        return 0

    if total_rows == 0:
        print(f"  ⚠️ MSSQL table {m_table} is empty. Skipping.")
        return 0

    # Determine column mapping
    mapping = get_common_mapping(m_cur, p_cur, m_table, pg_table)
    if not mapping:
        print(f"  ⚠️ No common / mapped columns between {m_table} and {pg_table}. Skipping.")
        return 0

    print("  🧩 Final column mapping (MSSQL → PG):")
    for m, p in mapping.items():
        print(f"    {m} → {p}")

    # Special per-table constants (for PG columns)
    table_constants = SPECIAL_CONSTANTS.get(m_table, {})

    pg_columns = list(mapping.values())
    # add constant-only PG columns that are not already in mapping
    for const_pg_col in table_constants.keys():
        if const_pg_col not in pg_columns:
            pg_columns.append(const_pg_col)

    # mapping PG col -> MSSQL col (only for mapped ones)
    src_for_dest = {pg_col: m_col for m_col, pg_col in mapping.items()}

    # Optionally truncate target table first
    if truncate_first:
        try:
            p_cur.execute(f'TRUNCATE TABLE "{pg_table}" RESTART IDENTITY CASCADE;')
            pg_conn.commit()
            print(f"  🧹 Truncated PG table {pg_table}")
        except Exception as e:
            print(f"  ❌ Failed to truncate {pg_table}: {e}")
            pg_conn.rollback()
            return 0

    # Build SELECT + INSERT
    m_select_cols = ",".join(f"[{c}]" for c in mapping.keys())
    p_col_str = ",".join(f'"{c}"' for c in pg_columns)
    placeholders = ",".join(["%s"] * len(pg_columns))

    # Fetch in chunks to avoid huge memory usage (if tables are big)
    batch_size = 500
    inserted = 0

    try:
        m_cur.execute(f"SELECT {m_select_cols} FROM [{m_table}]")

        while True:
            batch = m_cur.fetchmany(batch_size)
            if not batch:
                break

            for row in batch:
                # Build dict of MSSQL values keyed by MSSQL column names
                row_dict = {}
                for idx, m_col in enumerate(mapping.keys()):
                    row_dict[m_col] = row[idx]

                # Build PG values in correct column order
                values = []
                for pg_col in pg_columns:
                    if pg_col in src_for_dest:
                        # value comes from MSSQL column
                        m_col = src_for_dest[pg_col]
                        val = clean_value(row_dict.get(m_col))
                        # if cleaned value is None and we have a constant default, use it
                        if val is None and pg_col in table_constants:
                            val = table_constants[pg_col]
                        values.append(val)
                    elif pg_col in table_constants:
                        # pure constant column (no MSSQL source)
                        values.append(table_constants[pg_col])
                    else:
                        # nothing mapped and no constant – fall back to None
                        values.append(None)

                try:
                    p_cur.execute(
                        f'INSERT INTO "{pg_table}" ({p_col_str}) VALUES ({placeholders})',
                        values,
                    )
                    inserted += 1
                except Exception as e:
                    # Log and continue
                    print(f"    ❌ Insert error in {pg_table}: {e}")
                    pg_conn.rollback()
                    continue

            pg_conn.commit()
            print(f"  👉 Inserted so far into {pg_table}: {inserted} / {total_rows}")

    except Exception as e:
        print(f"  ❌ Failed reading/inserting for {m_table} → {pg_table}: {e}")
        pg_conn.rollback()
        return inserted

    print(f"  ✅ DONE: {inserted} rows inserted into {pg_table}")
    return inserted


# =====================================================
# MIGRATE ALL TABLES (ONE CLICK)
# =====================================================
def migrate_all_tables(truncate_first=False):
    """
    One-click bulk migration:
      - Connects to MSSQL + PG
      - Tries to match MSSQL tables to PG tables by suffix
      - Migrates using common-column intersection + SPECIAL_COLUMN_MAPPINGS
        and fills some NOT NULL PG columns with SPECIAL_CONSTANTS.
    Returns dict: {mssql_table: {"pg": pg_table, "rows": inserted}}
    """

    print("🔗 Connecting to MSSQL & PostgreSQL...")

    mssql_conn = pyodbc.connect(MSSQL_CONN_STR)
    pg_conn = psycopg2.connect(**POSTGRES_PARAMS)

    try:
        m_tables = get_mssql_tables(mssql_conn)
        print(f"📦 Found {len(m_tables)} MSSQL tables")

        p_cur = pg_conn.cursor()
        suffix_map = build_pg_suffix_map(p_cur)

        print("🧭 PG suffix map (for MahilMartPOS_App_* tables):")
        for suf, full_name in suffix_map.items():
            print(f"    {suf} → {full_name}")

        summary = {}

        for m_table in m_tables:
            if m_table in SKIP_MSSQL_TABLES:
                print(f"\n⏭ Skipping special table {m_table}")
                continue

            base = m_table.lower()
            if base.endswith("_table"):
                base = base[:-6]  # remove '_table'

            pg_table = suffix_map.get(base)

            if not pg_table:
                # No matching PG table (by suffix)
                print(f"\n⏭ No PG table mapped for MSSQL {m_table} (base: {base})")
                continue

            rows = migrate_one_table(
                mssql_conn,
                pg_conn,
                m_table,
                pg_table,
                truncate_first=truncate_first,
            )

            summary[m_table] = {"pg": pg_table, "rows": rows}

        print("\n🎉 BULK MIGRATION SUMMARY:")
        for m_table, info in summary.items():
            print(f"  {m_table} → {info['pg']}: {info['rows']} rows")

        return summary

    finally:
        try:
            mssql_conn.close()
        except Exception:
            pass
        try:
            pg_conn.close()
        except Exception:
            pass
