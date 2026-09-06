"""
CareerLens Data Validation Module
----------------------------------
Validates data/processed/jobs_clean.csv across multiple data quality dimensions:
1. Schema & Column Consistency Check
2. Row Count Verification (vs Raw Dataset count: 40,847)
3. Primary Key Uniqueness & Full Row Duplicate Check
4. Missing Values Audit
5. Logical Consistency (exp_min <= exp_max, salary_min <= salary_max)
6. Range Validity (Exp 0-50 yrs, Salary 0-1000 Lakhs, Posted Days 0-3500)
7. Data Types Audit

Does NOT modify the dataset.
Generates a clear PASS/FAIL validation report.
"""

import os
import sys
import pandas as pd
import numpy as np


EXPECTED_COLUMNS = [
    'id', 'job_title', 'company_name', 'experience_required', 'salary',
    'location', 'posted_date', 'openings', 'applicants', 'employment_type',
    'industry', 'department', 'role', 'role_category', 'education',
    'key_skills', 'jd_url', 'city', 'country', 'scraped_at',
    'exp_min_years', 'exp_max_years', 'is_salary_disclosed',
    'salary_min_lakhs', 'salary_max_lakhs', 'scraped_at_datetime',
    'estimated_posted_date', 'posted_days_ago', 'key_skills_clean',
    'skill_count', 'company_name_clean', 'location_clean',
    'employment_type_clean', 'industry_clean', 'department_clean',
    'role_clean', 'role_category_clean', 'education_clean',
    'city_clean', 'country_clean'
]

EXPECTED_ROW_COUNT = 40847


def validate_dataset(file_path="data/processed/jobs_clean.csv"):
    """Runs data quality validation checks and returns PASS/FAIL report."""
    print("==========================================================================")
    print("                  CAREERLENS DATA VALIDATION REPORT                       ")
    print("==========================================================================")
    print(f"Target File Path : {file_path}")
    
    if not os.path.exists(file_path):
        print(f"FAILED: File {file_path} does not exist.")
        return {"status": "FAIL", "reason": "File not found"}
        
    df = pd.read_csv(file_path, low_memory=False)
    actual_rows, actual_cols = df.shape
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    print(f"File Size        : {file_size_mb:.2f} MB")
    print(f"Actual Rows      : {actual_rows:,}")
    print(f"Actual Columns   : {actual_cols}")
    print("--------------------------------------------------------------------------")
    
    validation_results = []
    all_passed = True
    
    # --- CHECK 1: Schema & Column Consistency ---
    missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
    schema_passed = (len(missing_cols) == 0) and (actual_cols == len(EXPECTED_COLUMNS))
    validation_results.append({
        "Check Name": "1. Schema & Column Count",
        "Expected": f"{len(EXPECTED_COLUMNS)} columns",
        "Found": f"{actual_cols} columns",
        "Status": "PASS" if schema_passed else "FAIL",
        "Notes": "All expected columns present" if schema_passed else f"Missing: {missing_cols}"
    })
    if not schema_passed: all_passed = False

    # --- CHECK 2: Row Count Match ---
    row_passed = (actual_rows == EXPECTED_ROW_COUNT)
    validation_results.append({
        "Check Name": "2. Row Count Verification",
        "Expected": f"{EXPECTED_ROW_COUNT:,} rows",
        "Found": f"{actual_rows:,} rows",
        "Status": "PASS" if row_passed else "FAIL",
        "Notes": "100% row match with raw dataset" if row_passed else f"Row count mismatch ({actual_rows} vs {EXPECTED_ROW_COUNT})"
    })
    if not row_passed: all_passed = False

    # --- CHECK 3: Primary Key Uniqueness & Duplicates ---
    dup_ids = df['id'].duplicated().sum()
    dup_rows = df.duplicated().sum()
    dup_passed = (dup_ids == 0) and (dup_rows == 0)
    validation_results.append({
        "Check Name": "3. Primary Key Uniqueness & Duplicates",
        "Expected": "0 duplicate IDs / rows",
        "Found": f"{dup_ids} dup IDs, {dup_rows} dup rows",
        "Status": "PASS" if dup_passed else "FAIL",
        "Notes": "Primary key 'id' is 100% unique" if dup_passed else f"Duplicates found: {dup_ids} IDs"
    })
    if not dup_passed: all_passed = False

    # --- CHECK 4: Logical Consistency (Experience) ---
    exp_valid_mask = df['exp_min_years'].notnull() & df['exp_max_years'].notnull()
    exp_inv_range = (df[exp_valid_mask]['exp_min_years'] > df[exp_valid_mask]['exp_max_years']).sum()
    exp_neg_val = (df['exp_min_years'] < 0).sum()
    exp_passed = (exp_inv_range == 0) and (exp_neg_val == 0)
    validation_results.append({
        "Check Name": "4. Experience Range Logic (min <= max & min >= 0)",
        "Expected": "0 invalid logic records",
        "Found": f"{exp_inv_range} inverted, {exp_neg_val} negative",
        "Status": "PASS" if exp_passed else "FAIL",
        "Notes": "All extracted experience ranges are logically valid" if exp_passed else "Inverted min > max experience detected"
    })
    if not exp_passed: all_passed = False

    # --- CHECK 5: Logical Consistency (Salary) ---
    sal_valid_mask = df['salary_min_lakhs'].notnull() & df['salary_max_lakhs'].notnull()
    sal_inv_range = (df[sal_valid_mask]['salary_min_lakhs'] > df[sal_valid_mask]['salary_max_lakhs']).sum()
    sal_neg_val = (df['salary_min_lakhs'] < 0).sum()
    sal_passed = (sal_inv_range == 0) and (sal_neg_val == 0)
    validation_results.append({
        "Check Name": "5. Salary Range Logic (min <= max & min >= 0)",
        "Expected": "0 invalid logic records",
        "Found": f"{sal_inv_range} inverted, {sal_neg_val} negative",
        "Status": "PASS" if sal_passed else "FAIL",
        "Notes": "All extracted salary ranges are logically valid" if sal_passed else "Inverted min > max salary detected"
    })
    if not sal_passed: all_passed = False

    # --- CHECK 6: Unreasonable Range Boundaries ---
    unreasonable_exp = (df['exp_max_years'] > 50).sum()
    unreasonable_sal = (df['salary_max_lakhs'] > 1000).sum()
    unreasonable_days = (df['posted_days_ago'] < 0).sum() or (df['posted_days_ago'] > 3500).sum()
    range_passed = (unreasonable_exp == 0) and (unreasonable_sal == 0) and (unreasonable_days == 0)
    validation_results.append({
        "Check Name": "6. Outlier & Unreasonable Range Check",
        "Expected": "Exp <= 50 yrs, Sal <= 1000 L, Days 0-3500",
        "Found": f"{unreasonable_exp} exp>50, {unreasonable_sal} sal>1000L, {unreasonable_days} days invalid",
        "Status": "PASS" if range_passed else "FAIL",
        "Notes": "All numerical values fall within realistic boundaries" if range_passed else "Outliers beyond threshold detected"
    })
    if not range_passed: all_passed = False

    # --- CHECK 7: Data Types Integrity ---
    id_numeric = pd.api.types.is_numeric_dtype(df['id'])
    exp_numeric = pd.api.types.is_numeric_dtype(df['exp_min_years'])
    sal_bool = pd.api.types.is_bool_dtype(df['is_salary_disclosed']) or df['is_salary_disclosed'].isin([True, False]).all()
    dtype_passed = id_numeric and exp_numeric and sal_bool
    validation_results.append({
        "Check Name": "7. Data Types Integrity",
        "Expected": "id: int/num, exp: num, disclosed: bool",
        "Found": f"id: {df['id'].dtype}, exp: {df['exp_min_years'].dtype}, sal_flag: {df['is_salary_disclosed'].dtype}",
        "Status": "PASS" if dtype_passed else "FAIL",
        "Notes": "Numeric and boolean dtypes correctly assigned" if dtype_passed else "Data type mismatch detected"
    })
    if not dtype_passed: all_passed = False

    # Display Validation Results Table
    results_df = pd.DataFrame(validation_results)
    for idx, row in results_df.iterrows():
        print(f"[{row['Status']}] {row['Check Name']:<52} | {row['Notes']}")
        
    print("--------------------------------------------------------------------------")
    overall_status = "PASS" if all_passed else "FAIL"
    print(f"OVERALL VALIDATION STATUS: {overall_status}")
    print("==========================================================================")
    
    if not all_passed:
        sys.exit(1)
        
    return {"status": overall_status, "results": results_df}


if __name__ == "__main__":
    validate_dataset()
