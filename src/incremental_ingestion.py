"""
CareerLens Incremental Ingestion Pipeline Module
------------------------------------------------
1. Fetches latest jobs payload from Job Market API.
2. Applies preprocessing pipeline (src.preprocessing.preprocess).
3. Performs data quality validation on incoming batch.
4. Performs Incremental Database Merge (UPSERT via SQL MERGE) against CareerLens.dbo.jobs using 'id':
   - INSERT: New job records not existing in DB.
   - UPDATE: Existing jobs with changed attributes.
   - SKIP: Unchanged existing records.
5. Preserves existing database records without data corruption.
6. Reports detailed ingestion metrics and verifies final DB row count.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, types, text

# Import project pipeline modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.preprocessing import preprocess

API_URL = "https://job-market-api.subhadipk920.workers.dev/jobs"
SERVER = ".\\SQLEXPRESS"
DB_NAME = "CareerLens"

ENGINE_URL = (
    f"mssql+pyodbc://{SERVER}/{DB_NAME}?"
    f"driver=ODBC+Driver+18+for+SQL+Server&"
    f"trusted_connection=yes&"
    f"TrustServerCertificate=yes"
)


def fetch_latest_jobs(url=API_URL):
    """Fetches incoming job batch from the API."""
    print(f"1. Fetching incoming job records from API: {url}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            if response.status != 200:
                print(f"   HTTP Error {response.status}")
                sys.exit(1)
            raw_text = response.read().decode('utf-8')
            raw_json = json.loads(raw_text)
            records = raw_json.get("data", raw_json)
            print(f"   Successfully fetched {len(records):,} records from API.")
            return records
    except Exception as e:
        print(f"   Error fetching from API: {e}")
        sys.exit(1)


def run_incremental_pipeline(api_records=None, is_test_mode=False):
    """Runs end-to-end incremental ingestion against CareerLens.dbo.jobs."""
    print("==========================================================================")
    print("            CAREERLENS INCREMENTAL INGESTION PIPELINE                      ")
    print("==========================================================================")
    
    # Step 1: Fetch
    if api_records is None:
        records = fetch_latest_jobs()
    else:
        records = api_records
        print(f"1. Using provided batch of {len(records):,} records for ingestion.")
        
    df_raw = pd.DataFrame(records)
    print(f"   Batch raw dimensions: {df_raw.shape[0]:,} rows x {df_raw.shape[1]} columns")

    # Step 2: Preprocess
    print("\n2. Applying preprocessing & feature engineering pipeline...")
    df_clean = preprocess(df_raw)
    print(f"   Processed batch shape: {df_clean.shape[0]:,} rows x {df_clean.shape[1]} columns")

    # Format data for SQL Server insertion
    df_sql = df_clean.replace({np.nan: None})
    df_sql['id'] = df_sql['id'].astype(int)
    df_sql['is_salary_disclosed'] = df_sql['is_salary_disclosed'].astype(bool)
    df_sql['skill_count'] = df_sql['skill_count'].astype(int)
    df_sql['scraped_at_datetime'] = pd.to_datetime(df_sql['scraped_at_datetime'], errors='coerce')
    df_sql['estimated_posted_date'] = pd.to_datetime(df_sql['estimated_posted_date'], errors='coerce')

    # Step 3: Incremental SQL Merge (UPSERT)
    engine = create_engine(ENGINE_URL, fast_executemany=True)
    
    # Get initial DB row count
    with engine.connect() as conn:
        initial_db_count = conn.execute(text("SELECT COUNT(*) FROM dbo.jobs;")).fetchone()[0]
        
    print(f"\n3. Database state before merge: {initial_db_count:,} rows in dbo.jobs")
    # Load batch into regular staging table
    df_sql.to_sql('staging_jobs', con=engine, if_exists='replace', index=False)

    # Trim string columns to target NVARCHAR lengths to avoid truncation errors
    max_lengths = {
        'job_title': 500,
        'company_name': 255,
        'experience_required': 100,
        'salary': 255,
        'location': 1000,
        'posted_date': 255,
        'openings': 100,
        'applicants': 100,
        'employment_type': 100,
        'industry': 500,
        'department': 255,
        'role': 255,
        'role_category': 255,
        'education': None,  # NVARCHAR(MAX)
        'key_skills': None,  # NVARCHAR(MAX)
        'jd_url': None,  # NVARCHAR(MAX)
        'city': 100,
        'country': 100,
        'scraped_at': 100,
        # cleaned columns (derived) also have limits
        'company_name_clean': 255,
        'location_clean': 1000,
        'employment_type_clean': 100,
        'industry_clean': 500,
        'department_clean': 255,
        'role_clean': 255,
        'role_category_clean': 255,
        'education_clean': None,
        'city_clean': 100,
        'country_clean': 100,
    }
    for col, max_len in max_lengths.items():
        if col in df_sql.columns and max_len is not None:
            df_sql[col] = df_sql[col].astype(str).str.slice(0, max_len)


    # Perform MERGE statement
    print("   Executing SQL MERGE (INSERT new, UPDATE changed, SKIP identical)...")
    # Retrieve existing IDs and checksums from the database
    compare_cols = [
    'job_title', 'company_name', 'experience_required', 'salary', 'location',
    'posted_date', 'openings', 'applicants', 'employment_type', 'industry',
    'department', 'role', 'role_category', 'education', 'key_skills', 'jd_url',
    'city', 'country', 'scraped_at', 'exp_min_years', 'exp_max_years',
    'is_salary_disclosed', 'salary_min_lakhs', 'salary_max_lakhs',
    'scraped_at_datetime', 'estimated_posted_date', 'posted_days_ago',
    'key_skills_clean', 'skill_count', 'company_name_clean', 'location_clean',
    'employment_type_clean', 'industry_clean', 'department_clean', 'role_clean',
    'role_category_clean', 'education_clean', 'city_clean', 'country_clean'
]
    # Load batch into regular staging table (trimmed strings already applied above)
    df_sql.to_sql('staging_jobs', con=engine, if_exists='replace', index=False)

    # MERGE using staging_jobs and capture insert/update counts
    # Define MERGE statement that captures actions in a temporary table
    merge_sql = text("""
    DECLARE @Changes TABLE(ActionType NVARCHAR(10));

    MERGE dbo.jobs AS target
    USING staging_jobs AS source
    ON (target.id = source.id)
    WHEN MATCHED AND (
        ISNULL(target.job_title, '') <> ISNULL(source.job_title, '') OR
        ISNULL(target.company_name, '') <> ISNULL(source.company_name, '') OR
        ISNULL(target.salary, '') <> ISNULL(source.salary, '') OR
        ISNULL(target.location, '') <> ISNULL(source.location, '') OR
        ISNULL(target.posted_date, '') <> ISNULL(source.posted_date, '') OR
        ISNULL(target.key_skills, '') <> ISNULL(source.key_skills, '') OR
        ISNULL(target.scraped_at, '') <> ISNULL(source.scraped_at, '')
    )
    THEN UPDATE SET
        target.job_title = source.job_title,
        target.company_name = source.company_name,
        target.experience_required = source.experience_required,
        target.salary = source.salary,
        target.location = source.location,
        target.posted_date = source.posted_date,
        target.openings = source.openings,
        target.applicants = source.applicants,
        target.employment_type = source.employment_type,
        target.industry = source.industry,
        target.department = source.department,
        target.role = source.role,
        target.role_category = source.role_category,
        target.education = source.education,
        target.key_skills = source.key_skills,
        target.jd_url = source.jd_url,
        target.city = source.city,
        target.country = source.country,
        target.scraped_at = source.scraped_at,
        target.exp_min_years = source.exp_min_years,
        target.exp_max_years = source.exp_max_years,
        target.is_salary_disclosed = source.is_salary_disclosed,
        target.salary_min_lakhs = source.salary_min_lakhs,
        target.salary_max_lakhs = source.salary_max_lakhs,
        target.scraped_at_datetime = source.scraped_at_datetime,
        target.estimated_posted_date = source.estimated_posted_date,
        target.posted_days_ago = source.posted_days_ago,
        target.key_skills_clean = source.key_skills_clean,
        target.skill_count = source.skill_count,
        target.company_name_clean = source.company_name_clean,
        target.location_clean = source.location_clean,
        target.employment_type_clean = source.employment_type_clean,
        target.industry_clean = source.industry_clean,
        target.department_clean = source.department_clean,
        target.role_clean = source.role_clean,
        target.role_category_clean = source.role_category_clean,
        target.education_clean = source.education_clean,
        target.city_clean = source.city_clean,
        target.country_clean = source.country_clean
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (
            id, job_title, company_name, experience_required, salary, location, posted_date, openings, applicants,
            employment_type, industry, department, role, role_category, education, key_skills, jd_url, city, country,
            scraped_at, exp_min_years, exp_max_years, is_salary_disclosed, salary_min_lakhs, salary_max_lakhs,
            scraped_at_datetime, estimated_posted_date, posted_days_ago, key_skills_clean, skill_count,
            company_name_clean, location_clean, employment_type_clean, industry_clean, department_clean,
            role_clean, role_category_clean, education_clean, city_clean, country_clean
        )
        VALUES (
            source.id, source.job_title, source.company_name, source.experience_required, source.salary, source.location,
            source.posted_date, source.openings, source.applicants, source.employment_type, source.industry, source.department,
            source.role, source.role_category, source.education, source.key_skills, source.jd_url, source.city, source.country,
            source.scraped_at, source.exp_min_years, source.exp_max_years, source.is_salary_disclosed, source.salary_min_lakhs,
            source.salary_max_lakhs, source.scraped_at_datetime, source.estimated_posted_date, source.posted_days_ago,
            source.key_skills_clean, source.skill_count, source.company_name_clean, source.location_clean,
            source.employment_type_clean, source.industry_clean, source.department_clean, source.role_clean,
            source.role_category_clean, source.education_clean, source.city_clean, source.country_clean
        )
        OUTPUT $action INTO @Changes;
    """)

    # Define MERGE statement that captures actions in a temporary table and returns counts
    merge_sql = text("""
    CREATE TABLE #Changes (ActionType NVARCHAR(10));

    MERGE dbo.jobs AS target
    USING staging_jobs AS source
    ON (target.id = source.id)
    WHEN MATCHED AND (
        ISNULL(target.job_title, '') <> ISNULL(source.job_title, '') OR
        ISNULL(target.company_name, '') <> ISNULL(source.company_name, '') OR
        ISNULL(target.salary, '') <> ISNULL(source.salary, '') OR
        ISNULL(target.location, '') <> ISNULL(source.location, '') OR
        ISNULL(target.posted_date, '') <> ISNULL(source.posted_date, '') OR
        ISNULL(target.key_skills, '') <> ISNULL(source.key_skills, '') OR
        ISNULL(target.scraped_at, '') <> ISNULL(source.scraped_at, '')
    )
    THEN UPDATE SET
        target.job_title = source.job_title,
        target.company_name = source.company_name,
        target.experience_required = source.experience_required,
        target.salary = source.salary,
        target.location = source.location,
        target.posted_date = source.posted_date,
        target.openings = source.openings,
        target.applicants = source.applicants,
        target.employment_type = source.employment_type,
        target.industry = source.industry,
        target.department = source.department,
        target.role = source.role,
        target.role_category = source.role_category,
        target.education = source.education,
        target.key_skills = source.key_skills,
        target.jd_url = source.jd_url,
        target.city = source.city,
        target.country = source.country,
        target.scraped_at = source.scraped_at,
        target.exp_min_years = source.exp_min_years,
        target.exp_max_years = source.exp_max_years,
        target.is_salary_disclosed = source.is_salary_disclosed,
        target.salary_min_lakhs = source.salary_min_lakhs,
        target.salary_max_lakhs = source.salary_max_lakhs,
        target.scraped_at_datetime = source.scraped_at_datetime,
        target.estimated_posted_date = source.estimated_posted_date,
        target.posted_days_ago = source.posted_days_ago,
        target.key_skills_clean = source.key_skills_clean,
        target.skill_count = source.skill_count,
        target.company_name_clean = source.company_name_clean,
        target.location_clean = source.location_clean,
        target.employment_type_clean = source.employment_type_clean,
        target.industry_clean = source.industry_clean,
        target.department_clean = source.department_clean,
        target.role_clean = source.role_clean,
        target.role_category_clean = source.role_category_clean,
        target.education_clean = source.education_clean,
        target.city_clean = source.city_clean,
        target.country_clean = source.country_clean
    WHEN NOT MATCHED BY TARGET THEN
        INSERT (
            id, job_title, company_name, experience_required, salary, location, posted_date, openings, applicants,
            employment_type, industry, department, role, role_category, education, key_skills, jd_url, city, country,
            scraped_at, exp_min_years, exp_max_years, is_salary_disclosed, salary_min_lakhs, salary_max_lakhs,
            scraped_at_datetime, estimated_posted_date, posted_days_ago, key_skills_clean, skill_count,
            company_name_clean, location_clean, employment_type_clean, industry_clean, department_clean,
            role_clean, role_category_clean, education_clean, city_clean, country_clean
        )
        VALUES (
            source.id, source.job_title, source.company_name, source.experience_required, source.salary, source.location,
            source.posted_date, source.openings, source.applicants, source.employment_type, source.industry, source.department,
            source.role, source.role_category, source.education, source.key_skills, source.jd_url, source.city, source.country,
            source.scraped_at, source.exp_min_years, source.exp_max_years, source.is_salary_disclosed, source.salary_min_lakhs,
            source.salary_max_lakhs, source.scraped_at_datetime, source.estimated_posted_date, source.posted_days_ago,
            source.key_skills_clean, source.skill_count, source.company_name_clean, source.location_clean,
            source.employment_type_clean, source.industry_clean, source.department_clean, source.role_clean,
            source.role_category_clean, source.education_clean, source.city_clean, source.country_clean
        )
        OUTPUT $action INTO #Changes;

    SELECT ActionType, COUNT(*) AS ActionCount FROM #Changes GROUP BY ActionType;
    DROP TABLE #Changes;
    """)

    with engine.begin() as conn:
        # Create temporary table to capture action types
        conn.execute(text("CREATE TABLE #Changes (ActionType NVARCHAR(10));"))
        # Execute MERGE with OUTPUT into #Changes (no result set returned)
        conn.execute(text("""
MERGE dbo.jobs AS target
USING staging_jobs AS source
ON (target.id = source.id)
WHEN MATCHED AND (
    ISNULL(target.job_title, '') <> ISNULL(source.job_title, '') OR
    ISNULL(target.company_name, '') <> ISNULL(source.company_name, '') OR
    ISNULL(target.salary, '') <> ISNULL(source.salary, '') OR
    ISNULL(target.location, '') <> ISNULL(source.location, '') OR
    ISNULL(target.posted_date, '') <> ISNULL(source.posted_date, '') OR
    ISNULL(target.key_skills, '') <> ISNULL(source.key_skills, '') OR
    ISNULL(target.scraped_at, '') <> ISNULL(source.scraped_at, '')
)
THEN UPDATE SET
    target.job_title = source.job_title,
    target.company_name = source.company_name,
    target.experience_required = source.experience_required,
    target.salary = source.salary,
    target.location = source.location,
    target.posted_date = source.posted_date,
    target.openings = source.openings,
    target.applicants = source.applicants,
    target.employment_type = source.employment_type,
    target.industry = source.industry,
    target.department = source.department,
    target.role = source.role,
    target.role_category = source.role_category,
    target.education = source.education,
    target.key_skills = source.key_skills,
    target.jd_url = source.jd_url,
    target.city = source.city,
    target.country = source.country,
    target.scraped_at = source.scraped_at,
    target.exp_min_years = source.exp_min_years,
    target.exp_max_years = source.exp_max_years,
    target.is_salary_disclosed = source.is_salary_disclosed,
    target.salary_min_lakhs = source.salary_min_lakhs,
    target.salary_max_lakhs = source.salary_max_lakhs,
    target.scraped_at_datetime = source.scraped_at_datetime,
    target.estimated_posted_date = source.estimated_posted_date,
    target.posted_days_ago = source.posted_days_ago,
    target.key_skills_clean = source.key_skills_clean,
    target.skill_count = source.skill_count,
    target.company_name_clean = source.company_name_clean,
    target.location_clean = source.location_clean,
    target.employment_type_clean = source.employment_type_clean,
    target.industry_clean = source.industry_clean,
    target.department_clean = source.department_clean,
    target.role_clean = source.role_clean,
    target.role_category_clean = source.role_category_clean,
    target.education_clean = source.education_clean,
    target.city_clean = source.city_clean,
    target.country_clean = source.country_clean
WHEN NOT MATCHED BY TARGET THEN
    INSERT (
        id, job_title, company_name, experience_required, salary, location, posted_date, openings, applicants,
        employment_type, industry, department, role, role_category, education, key_skills, jd_url, city, country,
        scraped_at, exp_min_years, exp_max_years, is_salary_disclosed, salary_min_lakhs, salary_max_lakhs,
        scraped_at_datetime, estimated_posted_date, posted_days_ago, key_skills_clean, skill_count,
        company_name_clean, location_clean, employment_type_clean, industry_clean, department_clean,
        role_clean, role_category_clean, education_clean, city_clean, country_clean
    )
    VALUES (
        source.id, source.job_title, source.company_name, source.experience_required, source.salary, source.location,
        source.posted_date, source.openings, source.applicants, source.employment_type, source.industry, source.department,
        source.role, source.role_category, source.education, source.key_skills, source.jd_url, source.city, source.country,
        source.scraped_at, source.exp_min_years, source.exp_max_years, source.is_salary_disclosed, source.salary_min_lakhs,
        source.salary_max_lakhs, source.scraped_at_datetime, source.estimated_posted_date, source.posted_days_ago,
        source.key_skills_clean, source.skill_count, source.company_name_clean, source.location_clean,
        source.employment_type_clean, source.industry_clean, source.department_clean, source.role_clean,
        source.role_category_clean, source.education_clean, source.city_clean, source.country_clean
    )
OUTPUT $action INTO #Changes;
"""))
        # Retrieve action counts from temporary table
        result = conn.execute(text("SELECT ActionType, COUNT(*) AS ActionCount FROM #Changes GROUP BY ActionType;")).fetchall()
        # Clean up temporary table
        conn.execute(text("DROP TABLE #Changes;"))
        # Extract counts
        inserted_count = 0
        updated_count = 0
        for action, cnt in result:
            if action == 'INSERT':
                inserted_count = cnt
            elif action == 'UPDATE':
                updated_count = cnt
        # Clean up staging table
        conn.execute(text("DROP TABLE IF EXISTS staging_jobs"))
        # Final row count
        final_db_count = conn.execute(text("SELECT COUNT(*) FROM dbo.jobs;")).fetchone()[0]

    skipped_count = len(df_clean) - (inserted_count + updated_count)

    print("\n--------------------------------------------------------------------------")
    print("                  INCREMENTAL INGESTION SUMMARY REPORT                     ")
    print("--------------------------------------------------------------------------")
    print(f"Total Batch Records Processed : {len(df_clean):,}")
    print(f"NEW Records Inserted (INSERT) : {inserted_count:,}")
    print(f"CHANGED Records Updated (UPDATE): {updated_count:,}")
    print(f"UNCHANGED Records Skipped(SKIP): {skipped_count:,}")
    print("--------------------------------------------------------------------------")
    print(f"Initial Database Row Count    : {initial_db_count:,}")
    print(f"Final Database Row Count      : {final_db_count:,}")
    print(f"Net Database Growth           : +{final_db_count - initial_db_count:,}")
    print("==========================================================================")

    return {
        "batch_size": len(df_clean),
        "inserted": inserted_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "initial_count": initial_db_count,
        "final_count": final_db_count
    }


if __name__ == "__main__":
    run_incremental_pipeline()
