from agents import function_tool
import pyodbc

Check_Init = None

conn_str = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=192.168.1.36,8433;"
    "Database=BEST_DB;"
    "UID=sa;"
    "PWD=!ok*L9bicP;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=5;"
)


@function_tool
def Show_Tables():
    "Show all tables in the database"
    print("Connecting to database to show tables...")

    conn = pyodbc.connect(conn_str, timeout=5)
    cur = conn.cursor()

    cur.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """)

    Result = []
    rows = cur.fetchall()
    for schema, table in rows:
        # print(f"{schema}.{table}")
        Result.append(f"{schema}.{table}")
    
    cur.close()
    conn.close()
    return Result

@function_tool
def Query_SQL(Sql:str):
    "Execute a SQL query and return the results as a list of dictionaries"
    print("Connecting to database to execute SQL query...")
    conn = pyodbc.connect(conn_str, timeout=5)
    cur = conn.cursor()

    cur.execute(Sql)
    columns = [column[0] for column in cur.description]
    rows = cur.fetchall()

    Result = []
    for row in rows:
        row_dict = {columns[i]: row[i] for i in range(len(columns))}
        Result.append(row_dict)

    cur.close()
    conn.close()
    return Result

if __name__ == "__main__":
    print("=== Show Tables ===")
    tables = Show_Tables()
    for t in tables:
        print(t)

    print("\n=== Query SQL ===")
    sample_sql = "SELECT TOP 5 * FROM dbo.Equipment_Usage_Cost"  # 請替換為你的表名
    results = Query_SQL(sample_sql)
    for r in results:
        print(r)