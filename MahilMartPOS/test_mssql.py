import pyodbc

conn_str = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=192.168.0.113,1433;"
    "Database=MahilMart-Analytics;"
    "Uid=mahilmartuser;"
    "Pwd=Admin@123;"   # replace this
    "Trusted_Connection=no;"
)

try:
    print("Connecting...")
    conn = pyodbc.connect(conn_str, timeout=5)
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 name FROM sys.tables")
    row = cursor.fetchone()
    print("SUCCESS! Connected.")
    print("First table:", row[0] if row else "No tables found")
    conn.close()

except Exception as e:
    print("ERROR:", e)
