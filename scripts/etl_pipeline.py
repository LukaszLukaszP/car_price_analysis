import pandas as pd
import pyodbc
import sys
import math
from scripts.connect_sql import get_connection  # Import the SQL connection module

# Establish the SQL connection
conn = get_connection()
cursor = conn.cursor()

# Load data from the CSV file into a DataFrame
df = pd.read_csv("data/cleaned_otomoto_data.csv")

# Replace empty strings with None
df.replace("", None, inplace=True)

# Ensure that all NaN values in the DataFrame are replaced with None
df = df.where(pd.notnull(df), None)

# Define the SQL INSERT query for the 'cars' table
query = (
    "INSERT INTO cars (Make, Model, Engine_capacity, Power_HP, Mileage_in_km, Fuel_Type, "
    "Gearbox, Year, City, Province, Seller_Type, Price, Currency, Otomoto_ID, Otomoto_Indicator, "
    "Title, Link, Description, Scraping_Date) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

# Iterate over each row in the DataFrame
for index, row in df.iterrows():
    # Ensure that the 'Description' field is a string
    description = (row["Description"] or "") + ""
    
    # Convert numeric values: if a value is NaN, replace it with None
    engine_capacity = None if (isinstance(row["Engine capacity"], float) and math.isnan(row["Engine capacity"])) else row["Engine capacity"]
    power = None if (isinstance(row["Power"], float) and math.isnan(row["Power"])) else row["Power"]
    mileage = None if (isinstance(row["Mileage in km"], float) and math.isnan(row["Mileage in km"])) else row["Mileage in km"]
    price = None if (isinstance(row["Price"], float) and math.isnan(row["Price"])) else row["Price"]
    
    # Prepare the list of parameters; text fields remain unchanged
    params = [
        row["Make"],
        row["Model"],
        engine_capacity,
        power,
        mileage,
        row["Fuel Type"] if row["Fuel Type"] is not None else None,
        row["Gearbox"],
        row["Year"],
        row["City"],
        row["Province"],
        row["Seller Type"],
        price,
        row["Currency"],
        row["ID"],
        row["Otomoto Indicator"] if row["Otomoto Indicator"] is not None else None,
        row["Title"],
        row["Link"],
        description,
        row["Scraping Date"]
    ]
    
    # Uncomment the following block to log parameters for debugging purposes
    '''
    print(f"Record {index} parameters:")
    for i, p in enumerate(params, start=1):
        print(f"  Parameter {i}: {p!r}")
    '''
    
    try:
        cursor.execute(query, *params)
        conn.commit()
        print(f"✅ Record inserted at index: {index}\n")
    except Exception as e:
        print(f"❌ Error inserting record at index {index}: {e}")
        print("Record data:")
        print(row.to_dict())
        sys.exit(1)

# Close the SQL connection
conn.close()