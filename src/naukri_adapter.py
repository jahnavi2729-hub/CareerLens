"""
CareerLens Naukri Adapter Module
--------------------------------
Converts raw Naukri.com Apify scraper JSON records into the standardized
CareerLens DataFrame/schema with precise semantic mapping:
- descriptionText -> job_description / job_description_clean
- education -> education / education_clean (only if actual education field exists)
- employmentType -> employment_type / employment_type_clean (only if genuine employment type)
- workMode -> preserved as work_mode
"""

import json
import re
from pathlib import Path
import pandas as pd
import numpy as np


def extract_city(loc_str):
    """Extracts primary city from location string."""
    if not loc_str or not isinstance(loc_str, str):
        return "Bangalore"
    loc_lower = loc_str.lower()
    if "bengaluru" in loc_lower or "bangalore" in loc_lower:
        return "Bangalore"
    elif "pune" in loc_lower:
        return "Pune"
    elif "mumbai" in loc_lower:
        return "Mumbai"
    elif "delhi" in loc_lower or "noida" in loc_lower or "gurgaon" in loc_lower or "gurugram" in loc_lower:
        return "NCR"
    elif "hyderabad" in loc_lower:
        return "Hyderabad"
    elif "chennai" in loc_lower:
        return "Chennai"
    clean = re.split(r'[\(,\)]', loc_str)[0].strip()
    return clean if clean else "Bangalore"


def convert_naukri_to_careerlens(raw_records):
    """
    Converts a list of raw Naukri JSON records to a Pandas DataFrame matching
    the CareerLens schema with exact semantic mappings.
    """
    processed = []

    for item in raw_records:
        raw_id = item.get("id")
        try:
            job_id = int(raw_id)
        except (ValueError, TypeError):
            job_id = None

        title = str(item.get("title", "")).strip()
        company = str(item.get("company", "")).strip()
        exp_text = str(item.get("experienceText", "")).strip()
        salary_text = str(item.get("salaryText") or "").strip()
        salary_hidden = bool(item.get("salaryHidden", True))
        if not salary_text:
            salary_text = "Not Disclosed" if salary_hidden else "N/A"

        location = str(item.get("location", "")).strip()
        posted_date = str(item.get("postedLabel") or item.get("publishDate", "")).strip()
        
        # Description mapping
        job_description = str(item.get("descriptionText", "")).strip()
        job_description_clean = job_description.lower() if job_description else None

        # Education mapping (only if actual education field exists in raw item)
        education_raw = item.get("education")
        if education_raw and str(education_raw).strip() not in ["None", "N/A", ""]:
            education = str(education_raw).strip()
            education_clean = education.lower()
        else:
            education = None
            education_clean = None

        # Employment Type mapping (only if genuine employmentType field exists)
        emp_type_raw = item.get("employmentType")
        if emp_type_raw and str(emp_type_raw).strip() not in ["None", "N/A", ""]:
            employment_type = str(emp_type_raw).strip()
            employment_type_clean = employment_type.lower()
        else:
            employment_type = None
            employment_type_clean = None

        work_mode = str(item.get("workMode", "")).strip() if item.get("workMode") else None

        # Skills handling
        skills_raw = item.get("skills", [])
        if isinstance(skills_raw, list):
            skills_list = [str(s).strip() for s in skills_raw if s]
            key_skills = ", ".join(skills_list)
        else:
            key_skills = str(skills_raw).strip()
            skills_list = [s.strip() for s in key_skills.split(",") if s.strip()]

        jd_url = str(item.get("url", "")).strip()
        country = str(item.get("country", "IN")).strip()
        scraped_at = str(item.get("scrapedAt", "")).strip()
        city = extract_city(location)

        # Experience numeric
        try:
            exp_min = float(item["experienceMin"]) if item.get("experienceMin") is not None else np.nan
        except (ValueError, TypeError):
            exp_min = np.nan

        try:
            exp_max = float(item["experienceMax"]) if item.get("experienceMax") is not None else np.nan
        except (ValueError, TypeError):
            exp_max = np.nan

        # Salary numeric (in Lakhs P.A.)
        is_salary_disclosed = not salary_hidden
        try:
            sal_min_val = float(item["salaryMin"]) if item.get("salaryMin") is not None else np.nan
            sal_min_lakhs = sal_min_val / 100000.0 if pd.notnull(sal_min_val) else np.nan
        except (ValueError, TypeError):
            sal_min_lakhs = np.nan

        try:
            sal_max_val = float(item["salaryMax"]) if item.get("salaryMax") is not None else np.nan
            sal_max_lakhs = sal_max_val / 100000.0 if pd.notnull(sal_max_val) else np.nan
        except (ValueError, TypeError):
            sal_max_lakhs = np.nan

        # Dates & timestamps
        scraped_dt = pd.to_datetime(scraped_at, errors="coerce")
        publish_dt = pd.to_datetime(item.get("publishDateISO"), errors="coerce")

        if pd.notnull(scraped_dt) and pd.notnull(publish_dt):
            posted_days_ago = max(0.0, float((scraped_dt.date() - publish_dt.date()).days))
        else:
            posted_days_ago = np.nan

        rec = {
            "id": job_id,
            "job_title": title,
            "company_name": company,
            "experience_required": exp_text,
            "salary": salary_text,
            "location": location,
            "posted_date": posted_date,
            "openings": None,
            "applicants": None,
            "employment_type": employment_type,
            "work_mode": work_mode,
            "industry": None,
            "department": None,
            "role": None,
            "role_category": None,
            "education": education,
            "job_description": job_description,
            "key_skills": key_skills,
            "jd_url": jd_url,
            "city": city,
            "country": country,
            "scraped_at": scraped_at,
            "exp_min_years": exp_min,
            "exp_max_years": exp_max,
            "is_salary_disclosed": is_salary_disclosed,
            "salary_min_lakhs": sal_min_lakhs,
            "salary_max_lakhs": sal_max_lakhs,
            "scraped_at_datetime": scraped_dt,
            "estimated_posted_date": publish_dt,
            "posted_days_ago": posted_days_ago,
            "key_skills_clean": key_skills.lower() if key_skills else None,
            "skill_count": len(skills_list),
            "company_name_clean": company.lower() if company else None,
            "location_clean": location.lower() if location else None,
            "employment_type_clean": employment_type_clean,
            "industry_clean": None,
            "department_clean": None,
            "role_clean": None,
            "role_category_clean": None,
            "education_clean": education_clean,
            "job_description_clean": job_description_clean,
            "city_clean": city.lower() if city else None,
            "country_clean": country.lower() if country else None,
        }
        processed.append(rec)

    df = pd.DataFrame(processed)
    return df


if __name__ == "__main__":
    import sys
    raw_file = Path(r"C:/Users/Admin/Desktop/datascience term1 notes/term 3/MLOPS PROJECT/CareerLens/data/raw/naukri_bangalore_20_raw.json")
    if not raw_file.exists():
        print(f"Error: {raw_file} does not exist.")
        sys.exit(1)

    raw_data = json.loads(raw_file.read_text(encoding="utf-8"))
    print(f"Loaded {len(raw_data)} raw Naukri records.")

    df_converted = convert_naukri_to_careerlens(raw_data)
    print(f"\n--- ADAPTER LOCAL TEST RESULT ---")
    print(f"Converted DataFrame shape: {df_converted.shape[0]} rows x {df_converted.shape[1]} columns")
    print("\nColumns & Data Types:")
    for col, dtype in df_converted.dtypes.items():
        non_null = df_converted[col].count()
        print(f"  {col:<25} : {str(dtype):<15} (Non-null: {non_null}/{len(df_converted)})")

    print("\nSample Record Key Mappings (First row):")
    sample = df_converted.iloc[0].to_dict()
    key_checks = ["id", "job_title", "company_name", "job_description", "education", "employment_type", "work_mode", "key_skills"]
    for k in key_checks:
        val_str = str(sample.get(k))
        if len(val_str) > 80:
            val_str = val_str[:80] + "..."
        print(f"  {k:<25} = {val_str}")
