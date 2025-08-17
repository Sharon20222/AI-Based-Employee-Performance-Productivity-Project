# import_postgres.py
import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os

# Load database credentials from .env
load_dotenv()

# Connect to PostgreSQL
connection = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    port=os.getenv("DB_PORT", 5432)
)

cursor = connection.cursor()

# Read the CSV file
df = pd.read_csv('Extended_Employee_Performance_and_Productivity_Data.csv')

# Convert the 'Hire_Date' column to datetime
df['Hire_Date'] = pd.to_datetime(df['Hire_Date'], errors='coerce')

for index, row in df.iterrows():
    hire_date = row['Hire_Date'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['Hire_Date']) else None

    insert_values = (
        row['Department'], row['Gender'], row['Age'], row['Job_Title'],
        hire_date, row['Years_At_Company'], row['Education_Level'],
        row['Performance_Score'], row['Monthly_Salary'], row['Work_Hours_Per_Week'],
        row['Projects_Handled'], row['Overtime_Hours'], row['Sick_Days'],
        row['Remote_Work_Frequency'], row['Team_Size'], row['Training_Hours'],
        row['Promotions'], row['Employee_Satisfaction_Score'], row['Resigned'],
        row['Employee_ID']
    )

    cursor.execute("""
        UPDATE employees SET 
            Department = %s, Gender = %s, Age = %s, Job_Title = %s, Hire_Date = %s,
            Years_At_Company = %s, Education_Level = %s, Performance_Score = %s,
            Monthly_Salary = %s, Work_Hours_Per_Week = %s, Projects_Handled = %s,
            Overtime_Hours = %s, Sick_Days = %s, Remote_Work_Frequency = %s, Team_Size = %s,
            Training_Hours = %s, Promotions = %s, Employee_Satisfaction_Score = %s, Resigned = %s
        WHERE Employee_ID = %s
    """, insert_values)

connection.commit()
cursor.close()
connection.close()
print("Data updated successfully.")
