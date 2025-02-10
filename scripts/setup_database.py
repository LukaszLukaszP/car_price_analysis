import pyodbc
from scripts.connect_sql import get_connection  # Import the SQL Server connection

# Read the SQL script from the file
with open("sql/create_tables.sql", "r") as file:
    sql_script = file.read()

# Create a cursor object to interact with the SQL Server
conn = get_connection()
cursor = conn.cursor()

# Execute the SQL script
for statement in sql_script.split("GO"):  # SQL Server uses "GO" as a batch separator
    if statement.strip():
        cursor.execute(statement)

conn.commit()
print("✅ Tables have been created in SQL Server!")

conn.close()

# Run this script with: python scripts/setup_database.py
