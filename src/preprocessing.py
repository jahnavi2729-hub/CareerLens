"""
CareerLens Data Preprocessing Module
------------------------------------
Cleans raw job market API dataset (data/raw/jobs_raw.json) and performs feature engineering:
- Sentinel value replacement ('N/A', 'Not Disclosed' -> np.nan)
- Numeric experience extraction (exp_min_years, exp_max_years)
- Smart numeric salary extraction in Lakhs P.A. (is_salary_disclosed, salary_min_lakhs, salary_max_lakhs)
  Handles Lakhs, Crores, monthly PM salaries, and Rupee amounts seamlessly.
- Date normalization and estimation (scraped_at_datetime, posted_days_ago, estimated_posted_date)
- Key skills normalization and counting (key_skills_clean, skill_count)
- Preserves all original raw fields alongside engineered clean features.
- Saves processed output to data/processed/jobs_clean.csv
"""

import json
import os
import re
import sys
import pandas as pd
import numpy as np


def parse_experience(val):
    """Parses experience string into min and max years."""
    s = str(val).strip()
    if s in ['N/A', '', 'None', 'nan']:
        return np.nan, np.nan
    nums = re.findall(r'\d+', s)
    if len(nums) >= 2:
        val_min, val_max = float(nums[0]), float(nums[1])
        if val_min > val_max:
            val_min, val_max = val_max, val_min
        return val_min, val_max
    elif len(nums) == 1:
        return float(nums[0]), float(nums[0])
    return np.nan, np.nan


def parse_salary_smart(val):
    """
    Parses salary string into disclosure flag, min lakhs, and max lakhs P.A.
    Handles Lacs, Crores (Cr), monthly salaries (P.M), and raw Rupees.
    """
    s = str(val).strip()
    if s in ['N/A', 'Not Disclosed', 'Not disclosed', '', 'None', 'nan']:
        return False, np.nan, np.nan
    if 'Unpaid' in s or 'unpaid' in s:
        return True, 0.0, 0.0
    
    is_pm = ('P.M' in s or 'p.m' in s or 'per month' in s.lower())
    parts = re.split(r'[-–to]+', s)
    lakh_values = []
    
    for part in parts:
        part_str = part.strip()
        is_cr = ('Cr' in part_str or 'cr' in part_str or 'Crore' in part_str or 'crore' in part_str)
        clean_num_str = part_str.replace(',', '')
        nums = re.findall(r'\d+(?:\.\d+)?', clean_num_str)
        if nums:
            val_num = float(nums[0])
            if is_cr:
                val_lakhs = val_num * 100.0
            elif is_pm:
                val_lakhs = (val_num * 12.0) / 100000.0 if val_num >= 100 else val_num
            elif val_num >= 1000:  # raw rupees e.g. 50,000 -> 0.5 Lacs
                val_lakhs = val_num / 100000.0
            else:
                val_lakhs = val_num
            lakh_values.append(val_lakhs)
            
    if len(lakh_values) >= 2:
        val_min, val_max = lakh_values[0], lakh_values[1]
        if val_min > val_max:
            val_min, val_max = val_max, val_min
        return True, val_min, val_max
    elif len(lakh_values) == 1:
        return True, lakh_values[0], lakh_values[0]
        
    return True, np.nan, np.nan


def parse_posted_date(row):
    """Extracts posted_days_ago and computes estimated_posted_date from scraped_at."""
    p_str = str(row['posted_date']).strip()
    s_dt = pd.to_datetime(row['scraped_at'], errors='coerce')
    
    if p_str in ['N/A', '', 'None', 'nan']:
        return s_dt, np.nan
    
    match_iso = re.search(r'\d{4}-\d{2}-\d{2}', p_str)
    if match_iso:
        dt_iso = pd.to_datetime(match_iso.group(0), errors='coerce')
        if pd.notnull(dt_iso) and pd.notnull(s_dt):
            days_ago = max(0.0, float((s_dt.date() - dt_iso.date()).days))
            return dt_iso, days_ago
        elif pd.notnull(dt_iso):
            return dt_iso, np.nan

    p_lower = p_str.lower()
    days_ago = 0.0
    if any(k in p_lower for k in ['just now', 'few hours ago', 'today']):
        days_ago = 0.0
    elif 'yesterday' in p_lower or '1 day ago' in p_lower:
        days_ago = 1.0
    elif 'day' in p_lower:
        match_days = re.search(r'(\d+)\s+day', p_lower)
        if match_days:
            days_ago = float(match_days.group(1))
    elif 'week' in p_lower:
        match_weeks = re.search(r'(\d+)\s+week', p_lower)
        days_ago = float(match_weeks.group(1)) * 7.0 if match_weeks else 7.0
    elif 'month' in p_lower:
        match_months = re.search(r'(\d+)\s+month', p_lower)
        days_ago = float(match_months.group(1)) * 30.0 if match_months else 30.0

    if pd.notnull(s_dt):
        est_date = s_dt - pd.Timedelta(days=days_ago)
        return est_date, days_ago
    return pd.NaT, days_ago


def clean_skills(val):
    """Normalizes key_skills string (lowercasing, trimming) and counts skills."""
    s = str(val).strip()
    if s in ['N/A', '', 'None', 'nan']:
        return "", 0
    skills = [sk.strip().lower() for sk in s.split(',') if sk.strip() != '']
    return ", ".join(skills), len(skills)


def preprocess(df):
    """Applies complete preprocessing and feature engineering pipeline on DataFrame."""
    df_clean = df.copy()
    
    # 1. Experience Features
    exp_parsed = df_clean['experience_required'].apply(parse_experience)
    df_clean['exp_min_years'] = [x[0] for x in exp_parsed]
    df_clean['exp_max_years'] = [x[1] for x in exp_parsed]
    
    # 2. Salary Features (Smart Extractor)
    sal_parsed = df_clean['salary'].apply(parse_salary_smart)
    df_clean['is_salary_disclosed'] = [x[0] for x in sal_parsed]
    df_clean['salary_min_lakhs'] = [x[1] for x in sal_parsed]
    df_clean['salary_max_lakhs'] = [x[2] for x in sal_parsed]
    
    # 3. Date Features
    dates_parsed = df_clean.apply(parse_posted_date, axis=1)
    df_clean['scraped_at_datetime'] = pd.to_datetime(df_clean['scraped_at'], errors='coerce')
    df_clean['estimated_posted_date'] = [x[0] for x in dates_parsed]
    df_clean['posted_days_ago'] = [x[1] for x in dates_parsed]
    
    # 4. Skills Normalization
    skills_parsed = df_clean['key_skills'].apply(clean_skills)
    df_clean['key_skills_clean'] = [x[0] for x in skills_parsed]
    df_clean['skill_count'] = [x[1] for x in skills_parsed]
    
    # 5. Clean text sentinels in string columns
    text_cols = ['company_name', 'location', 'employment_type', 'industry', 
                 'department', 'role', 'role_category', 'education', 'city', 'country']
    for col in text_cols:
        if col in df_clean.columns:
            df_clean[col + '_clean'] = df_clean[col].apply(
                lambda v: np.nan if str(v).strip() in ['N/A', '', 'None'] else str(v).strip()
            )
            
    return df_clean


def run_preprocessing(input_path="data/raw/jobs_raw.json", output_path="data/processed/jobs_clean.csv"):
    """Main execution function for data preprocessing pipeline."""
    print(f"Reading raw dataset from {input_path}...")
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} not found.")
        sys.exit(1)
        
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        
    records = raw_data.get("data", raw_data)
    df_raw = pd.DataFrame(records)
    raw_rows, raw_cols = df_raw.shape
    print(f"Loaded raw data: {raw_rows:,} rows x {raw_cols} columns")
    
    # Preprocess
    print("Executing feature engineering and smart data cleaning...")
    df_processed = preprocess(df_raw)
    proc_rows, proc_cols = df_processed.shape
    
    # Save output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_processed.to_csv(output_path, index=False, encoding='utf-8-sig')
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    
    print("\n=== PREPROCESSING QUALITY VERIFICATION ===")
    print(f"Input Raw Rows       : {raw_rows:,}")
    print(f"Processed Rows       : {proc_rows:,}")
    print(f"Row Count Match      : {raw_rows == proc_rows}")
    print(f"Original Columns     : {raw_cols}")
    print(f"Engineered Columns   : {proc_cols - raw_cols}")
    print(f"Total Processed Cols : {proc_cols}")
    print(f"Output File Path     : {output_path}")
    print(f"Output File Size     : {file_size_mb:.2f} MB")
    
    # Quality Checks
    print("\n=== DATA QUALITY METRICS ===")
    print(f"Exp Min Years Parsed  : {df_processed['exp_min_years'].notnull().sum():,} / {proc_rows:,} ({df_processed['exp_min_years'].notnull().mean()*100:.2f}%)")
    print(f"Salaries Disclosed    : {df_processed['is_salary_disclosed'].sum():,} / {proc_rows:,} ({df_processed['is_salary_disclosed'].mean()*100:.2f}%)")
    print(f"Skills Cleaned & Counted: {(df_processed['skill_count'] > 0).sum():,} / {proc_rows:,} ({(df_processed['skill_count'] > 0).mean()*100:.2f}%)")
    print(f"Estimated Dates Parsed: {df_processed['estimated_posted_date'].notnull().sum():,} / {proc_rows:,} ({df_processed['estimated_posted_date'].notnull().mean()*100:.2f}%)")
    
    if raw_rows == proc_rows:
        print("\nSUCCESS: Preprocessing pipeline completed successfully.")
    else:
        print("\nERROR: Row count mismatch detected!")
        sys.exit(1)


if __name__ == "__main__":
    run_preprocessing()
