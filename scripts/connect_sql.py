# connect_sql.py
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="database.env")

def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    
    conn = pyodbc.connect(
        f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    )
    return conn

# Jeżeli chcesz przetestować połączenie:
if __name__ == '__main__':
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION;")
    print(cursor.fetchone())
    conn.close()
