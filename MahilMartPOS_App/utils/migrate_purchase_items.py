import pyodbc
import psycopg2
from decimal import Decimal
from datetime import datetime

# ---------------------------------------------
# MSSQL & POSTGRES CONNECTIONS
# ---------------------------------------------
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

# -----------------------------------------------------
# HELPERS
# -----------------------------------------------------
def d(val):
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val))
    except:
        return Decimal("0")

def clean_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


# -----------------------------------------------------
# MAIN MIGRATION
# -----------------------------------------------------
def migrate_purchase_items():
    print("Connecting to MSSQL & PostgreSQL...")

    m_conn = pyodbc.connect(MSSQL_CONN_STR)
    p_conn = psycopg2.connect(**POSTGRES_PARAMS)

    m_cur = m_conn.cursor()
    p_cur = p_conn.cursor()

    # ==========================================================
    # 1) Load HEADER MAP
    # ==========================================================
    print("Loading header map...")

    p_cur.execute('SELECT id FROM "MahilMartPOS_App_purchase" ORDER BY id')
    purchase_ids = [r[0] for r in p_cur.fetchall()]

    m_cur.execute("SELECT PurMas_SNo FROM PurMas_Table WHERE PurMas_Cancel=0 ORDER BY PurMas_SNo")
    pur_snos = [r[0] for r in m_cur.fetchall()]

    if len(pur_snos) != len(purchase_ids):
        print("ERROR: Header mismatch")
        return

    header_map = dict(zip(pur_snos, purchase_ids))
    print(f"Loaded {len(header_map)} header mappings.")

    # -------------------------------------------------
    # 2) READ ItemTrn purchase rows
    # -------------------------------------------------
    print("Reading purchase ITEM rows...")

    m_cur.execute("""
        SELECT
            Mas_SNo, Item_No,
            Qty, Rate, Amount,
            Dis_Amt, Tax_Amt, NetAmt,
            Mrsp, Prd_Rate, Prd_Amt,
            ItemTrn_Batch, LRDate
        FROM ItemTrn_Table
        WHERE Type = 0
        ORDER BY SNo
    """)

    rows = m_cur.fetchall()
    print(f"Found {len(rows)} item rows")

    # -------------------------------------------------
    # 3) Missing PostgreSQL Items Detection
    # -------------------------------------------------
    p_cur.execute('SELECT id FROM "MahilMartPOS_App_item"')
    pg_items = {r[0] for r in p_cur.fetchall()}

    mssql_item_ids = {r[1] for r in rows}
    missing_items = mssql_item_ids - pg_items

    print(f"Missing Item IDs in PostgreSQL: {len(missing_items)}")

    # -------------------------------------------------
    # 4) CREATE placeholder items (FULL 27 columns)
    # -------------------------------------------------
    if missing_items:
        print("Creating placeholder items...")

        for item_id in missing_items:
            try:
                p_cur.execute(
                    '''
                    INSERT INTO "MahilMartPOS_App_item"
                    (
                        id, code, item_name, print_name, status,
                        unit, "P_unit", "group", brand,
                        tax, "HSN_SAC",
                        "P_rate", cost_rate, "MRSP",
                        sale_rate, whole_rate, whole_rate_2,
                        use_MRP, min_stock, stock_item,
                        carry_over, manual,
                        points, cess_per_qty,
                        picture, barcode, other
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s,
                        NULL, NULL, NULL, NULL,
                        0, 0,
                        0, 0, 0,
                        0, 0, 0,
                        '', '0', '0',
                        '0', '0',
                        0, 0,
                        '', '', ''
                    )
                    ''',
                    (
                        item_id,
                        f"UNK-{item_id}",
                        f"UNKNOWN-{item_id}",
                        "",
                        "active",
                    )
                )
                p_conn.commit()

            except Exception as e:
                print(f"Failed to create item {item_id}: {e}")
                p_conn.rollback()

        print("Placeholder items created.\n")

    # Refresh PG items
    p_cur.execute('SELECT id FROM "MahilMartPOS_App_item"')
    pg_items = {r[0] for r in p_cur.fetchall()}

    # -------------------------------------------------
    # 5) INSERT purchase items
    # -------------------------------------------------
    inserted = 0
    missing_headers = 0
    skipped_missing_item = 0

    for r in rows:
        (
            mas_sno, item_no, qty, rate, amount,
            dis_amt, tax_amt, net_amt, mrp,
            cost_rate, cost_amount,
            batch_no_raw, expiry_raw
        ) = r

        purchase_id = header_map.get(mas_sno)
        if not purchase_id:
            missing_headers += 1
            continue

        if item_no not in pg_items:
            skipped_missing_item += 1
            continue

        batch_no = clean_str(batch_no_raw)
        expiry = expiry_raw.date() if expiry_raw else None

        taxable_price = d(amount) - d(dis_amt)
        if taxable_price < 0:
            taxable_price = Decimal("0")

        try:
            p_cur.execute(
                """
                INSERT INTO "MahilMartPOS_App_purchaseitem"
                (
                    purchase_id, item_id,
                    quantity, unit_price, total_price,
                    discount, tax, taxable_price, net_price,
                    cost_price, mrp_price,
                    previous_qty, total_qty,
                    purchased_at,
                    batch_no, expiry_date,
                    hsn, "group", brand, unit,
                    supplier_id, code, item_name,
                    unit_qty, split_unit, split_unit_price,
                    whole_price, whole_price_2, sale_price,
                    status
                )
                VALUES
                (
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    0, %s,
                    %s,
                    %s, %s,
                    NULL, NULL, NULL, NULL,
                    NULL, NULL, NULL,
                    0, 0, 0,
                    0, 0, 0,
                    'in_stock'
                )
                """,
                (
                    purchase_id,
                    item_no,
                    d(qty), d(rate), d(amount),
                    d(dis_amt), d(tax_amt), taxable_price, d(net_amt),
                    d(cost_rate), d(mrp),
                    d(qty),
                    datetime.now().date(),
                    batch_no,
                    expiry
                )
            )
            inserted += 1

        except Exception as e:
            print(f"Insert error for item {item_no}: {e}")

        p_conn.commit()

    # -------------------------------------------------
    # SUMMARY
    # -------------------------------------------------
    print("\n==============================")
    print("ITEM MIGRATION SUMMARY")
    print("==============================")
    print(f"Items inserted       : {inserted}")
    print(f"Missing headers      : {missing_headers}")
    print(f"Missing items        : {skipped_missing_item}")
    print("==============================")
    print("Done.")

    m_conn.close()
    p_conn.close()


if __name__ == "__main__":
    migrate_purchase_items()
