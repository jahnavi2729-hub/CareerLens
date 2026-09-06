import os
import sys
import pyodbc
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, types, text

CSV_PATH = "data/processed/jobs_clean.csv"
SERVER = ".\\SQLEXPRESS"
DB_NAME = "CareerLens"

CONN_STR_MASTER = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server={SERVER};"
    f"Database=master;"
    f"Trusted_Connection=yes;"
    f"TrustServerCertificate=yes;"
)

def create_database():
    print(f"Connecting to SQL Server ({SERVER}) to check/create database '{DB_NAME}'...")
    conn = pyodbc.connect(CONN_STR_MASTER, autocommit=True)
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{DB_NAME}'")
    if not cursor.fetchone():
        print(f"Creating database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE [{DB_NAME}]")
        print(f"Database '{DB_NAME}' created successfully.")
    else:
        print(f"Database '{DB_NAME}' already exists.")
    conn.close()

def create_table_and_load_data():
    print(f"Reading processed dataset from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    total_rows, total_cols = df.shape
    print(f"Loaded CSV data: {total_rows:,} rows x {total_cols} columns")

    # SQLAlchemy engine for SQL Server
    connection_url = f"mssql+pyodbc://{SERVER}/{DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes"
    engine = create_engine(connection_url, fast_executemany=True)

    # Convert datetimes
    df['scraped_at_datetime'] = pd.to_datetime(df['scraped_at_datetime'], errors='coerce')
    df['estimated_posted_date'] = pd.to_datetime(df['estimated_posted_date'], errors='coerce')

    # Explicit SQLAlchemy Dtype Mapping
    dtype_dict = {
        'id': types.BigInteger(),
        'job_title': types.NVARCHAR(500),
        'company_name': types.NVARCHAR(255),
        'experience_required': types.NVARCHAR(100),
        'salary': types.NVARCHAR(255),
        'location': types.NVARCHAR(1000),
        'posted_date': types.NVARCHAR(255),
        'openings': types.NVARCHAR(100),
        'applicants': types.NVARCHAR(100),
        'employment_type': types.NVARCHAR(100),
        'industry': types.NVARCHAR(500),
        'department': types.NVARCHAR(255),
        'role': types.NVARCHAR(255),
        'role_category': types.NVARCHAR(255),
        'education': types.NVARCHAR(length=None),  # NVARCHAR(MAX)
        'key_skills': types.NVARCHAR(length=None),
        'jd_url': types.NVARCHAR(length=None),
        'city': types.NVARCHAR(100),
        'country': types.NVARCHAR(100),
        'scraped_at': types.NVARCHAR(100),
        'exp_min_years': types.Float(),
        'exp_max_years': types.Float(),
        'is_salary_disclosed': types.Boolean(),
        'salary_min_lakhs': types.Float(),
        'salary_max_lakhs': types.Float(),
        'scraped_at_datetime': types.DateTime(),
        'estimated_posted_date': types.DateTime(),
        'posted_days_ago': types.Float(),
        'key_skills_clean': types.NVARCHAR(length=None),
        'skill_count': types.Integer(),
        'company_name_clean': types.NVARCHAR(255),
        'location_clean': types.NVARCHAR(1000),
        'employment_type_clean': types.NVARCHAR(100),
        'industry_clean': types.NVARCHAR(500),
        'department_clean': types.NVARCHAR(255),
        'role_clean': types.NVARCHAR(255),
        'role_category_clean': types.NVARCHAR(255),
        'education_clean': types.NVARCHAR(length=None),
        'city_clean': types.NVARCHAR(100),
        'country_clean': types.NVARCHAR(100)
    }

    print("Loading data into SQL Server using SQLAlchemy fast_executemany...")
    df.to_sql('jobs', con=engine, schema='dbo', if_exists='replace', index=False, dtype=dtype_dict, chunksize=5000)
    print(f"All {total_rows:,} records successfully loaded into dbo.jobs.")

    # Create Primary Key constraint on id
    print("Creating PRIMARY KEY constraint on 'id'...")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE dbo.jobs ALTER COLUMN id BIGINT NOT NULL;"))
        conn.execute(text("ALTER TABLE dbo.jobs ADD CONSTRAINT PK_jobs_id PRIMARY KEY CLUSTERED (id);"))
        conn.commit()
    print("PRIMARY KEY CLUSTERED INDEX constraint created successfully on 'id'.")

def verify_sql_database():
    print("\n==========================================================================")
    print("                  SQL SERVER VERIFICATION & AUDIT                         ")
    print("==========================================================================")
    
    connection_url = f"mssql+pyodbc://{SERVER}/{DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes"
    engine = create_engine(connection_url)

    with engine.connect() as conn:
        # 1. Database & Table Check
        res = conn.execute(text("SELECT DB_NAME() AS current_db, OBJECT_ID('dbo.jobs', 'U') AS table_id;")).fetchone()
        print(f"1. Current Database    : {res[0]}")
        print(f"   Table Object ID    : {res[1]} (Table exists: {res[1] is not None})")

        # 2. Row Count Query
        res_count = conn.execute(text("SELECT COUNT(*) FROM dbo.jobs;")).fetchone()[0]
        print(f"2. Total Row Count    : {res_count:,} (Expected: 40,847)")

        # 3. Key Uniqueness Query
        res_keys = conn.execute(text("SELECT COUNT(id) AS total_keys, COUNT(DISTINCT id) AS unique_keys FROM dbo.jobs;")).fetchone()
        print(f"3. Key Uniqueness     : Total Keys = {res_keys[0]:,}, Unique Keys = {res_keys[1]:,}")
        print(f"   Is Primary Key Unique: {res_keys[0] == res_keys[1]}")

        # 4. Primary Key & Index Verification
        indexes = conn.execute(text("""
            SELECT i.name AS index_name, i.type_desc, i.is_unique, i.is_primary_key
            FROM sys.indexes i
            WHERE i.object_id = OBJECT_ID('dbo.jobs') AND i.type > 0;
        """)).fetchall()
        print("\n4. Indexes on dbo.jobs Table:")
        for idx in indexes:
            print(f"   - Name: {idx[0]}, Type: {idx[1]}, IsUnique: {idx[2]}, IsPrimaryKey: {idx[3]}")

        # 5. Schema Columns Verification
        cols = conn.execute(text("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'jobs';
        """)).fetchall()
        print(f"\n5. Table Schema Column Count: {len(cols)}")
        print("   Sample Columns (First 8):")
        for c in cols[:8]:
            max_len_str = "MAX" if c[2] == -1 else str(c[2])
            print(f"   - {c[0]:<22} | Type: {c[1]:<12} | MaxLen: {max_len_str:<6} | Nullable: {c[3]}")

    print("--------------------------------------------------------------------------")
    if res_count == 40847 and res_keys[0] == res_keys[1]:
        print("OVERALL SQL VERIFICATION STATUS: SUCCESS")
    else:
        print("OVERALL SQL VERIFICATION STATUS: FAILED")
    print("==========================================================================")

if __name__ == "__main__":
    create_database()
    create_table_and_load_data()
    verify_sql_database()
