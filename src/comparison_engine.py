"""
CareerLens Market-vs-Resume Comparison Engine
---------------------------------------------
Evaluates candidate resume profile alignment against role-specific job market demand.

Methodology:
1. Filters market job postings in `jobs_clean.csv` matching `target_role`.
2. Applies skill normalization (removes job title terms, unifies aliases like Spark/PySpark, Azure/Microsoft Azure, Databricks).
3. Computes market skill demand (% of postings containing each skill, 1 vote per posting).
4. Selects evaluated skills appearing in >= 5.0% of role postings.
5. Computes Market Fit % as market-demand-weighted skill coverage:
   (sum of demand % for candidate-present skills / sum of demand % for evaluated skills) * 100
6. Ranks missing skills by priority (descending demand %, ascending skill name).
7. Evaluates experience alignment against market experience range & median.
8. Pure deterministic mathematical calculations; zero LLM calls or arbitrary weights.
"""

import sys
import json
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Optional, Union

import pandas as pd

# Import local resume processor & normalizer
try:
    from src.resume_processor import process_resume
    from src.skill_normalizer import normalize_skill_token, normalize_skill_list
    from src.skill_demand_intelligence import assign_experience_bucket
except ImportError:
    from resume_processor import process_resume
    from skill_normalizer import normalize_skill_token, normalize_skill_list
    from skill_demand_intelligence import assign_experience_bucket

# Default CSV Path relative to project root
DEFAULT_CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "jobs_clean.csv"


def load_jobs_data(csv_path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """Load cleaned jobs dataset from CSV."""
    path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Jobs CSV dataset not found at: {path}")
    return pd.read_csv(path, low_memory=False)


def get_available_roles(csv_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """
    Return unique target roles supported by the market dataset,
    sorted by posting count descending.
    """
    df = load_jobs_data(csv_path)
    if "role_clean" not in df.columns:
        return []
    role_counts = df["role_clean"].dropna().value_counts()
    return [
        {"role": role, "posting_count": int(count)}
        for role, count in role_counts.items()
    ]


def get_market_intelligence(
    target_role: str,
    csv_path: Optional[Union[str, Path]] = None,
    min_demand_threshold: float = 5.0
) -> Dict[str, Any]:
    """
    Computes market demand intelligence for a target role using normalized skills
    and experience distributions.
    """
    df_all = load_jobs_data(csv_path)
    if "role_clean" not in df_all.columns:
        raise KeyError("Column 'role_clean' not found in jobs dataset.")

    df_role = df_all[df_all["role_clean"].str.contains(target_role, case=False, na=False)].copy()
    total_postings = len(df_role)

    if total_postings == 0:
        return {
            "target_role": target_role,
            "posting_denominator": 0,
            "evaluated_skill_count": 0,
            "evaluated_skills": [],
            "all_skills": [],
            "experience_distribution": {
                "min_exp_years": 0.0,
                "median_min_exp_years": 0.0,
                "avg_min_exp_years": 0.0,
                "max_exp_years": 0.0,
                "buckets": {}
            }
        }

    # Market skill demand with per-posting deduplication and normalization
    market_demand = compute_market_skill_demand(df_role)
    all_skill_stats = market_demand["skill_stats"]

    # All skills sorted by demand_pct DESC, skill ASC
    sorted_all_skills = [
        {
            "skill": skill,
            "posting_count": info["count"],
            "demand_pct": info["demand_pct"]
        }
        for skill, info in sorted(all_skill_stats.items(), key=lambda x: (-x[1]["demand_pct"], x[0]))
    ]

    # Evaluated skills (demand_pct >= min_demand_threshold)
    evaluated_skills = [s for s in sorted_all_skills if s["demand_pct"] >= min_demand_threshold]

    # Experience metrics
    exp_min_series = df_role["exp_min_years"].dropna().astype(float)
    exp_max_series = df_role["exp_max_years"].dropna().astype(float)

    market_min_exp = float(exp_min_series.min()) if not exp_min_series.empty else 0.0
    market_max_exp = float(exp_max_series.max()) if not exp_max_series.empty else 0.0
    market_median_min_exp = float(exp_min_series.median()) if not exp_min_series.empty else 0.0
    market_avg_min_exp = float(exp_min_series.mean()) if not exp_min_series.empty else 0.0

    # Experience bucket breakdown
    df_role["exp_bucket"] = df_role["exp_min_years"].apply(assign_experience_bucket)
    bucket_counts = df_role["exp_bucket"].value_counts().to_dict()

    experience_buckets = {}
    for bucket_name in ["Early", "Mid", "Senior", "Unknown"]:
        cnt = int(bucket_counts.get(bucket_name, 0))
        pct = round((cnt / total_postings) * 100, 2) if total_postings > 0 else 0.0
        experience_buckets[bucket_name] = {
            "postings": cnt,
            "percentage": pct
        }

    return {
        "target_role": target_role,
        "posting_denominator": total_postings,
        "evaluated_skill_count": len(evaluated_skills),
        "evaluated_skills": evaluated_skills,
        "all_skills": sorted_all_skills,
        "experience_distribution": {
            "min_exp_years": market_min_exp,
            "median_min_exp_years": round(market_median_min_exp, 1),
            "avg_min_exp_years": round(market_avg_min_exp, 1),
            "max_exp_years": market_max_exp,
            "buckets": experience_buckets
        }
    }




def tokenise_skills(skills_raw: Any) -> List[str]:
    """Split raw key_skills_clean into normalized lower-case skill tokens."""
    if pd.isna(skills_raw) or not str(skills_raw).strip():
        return []
    text = str(skills_raw)
    tokens = []
    for delim in [",", ";", "|"]:
        if delim in text:
            parts = [p.strip().lower() for p in text.split(delim)]
            tokens = [p for p in parts if p]
            break
    if not tokens:
        single = text.strip().lower()
        if single:
            tokens = [single]

    normalized = []
    for t in tokens:
        norm = normalize_skill_token(t)
        if norm:
            normalized.append(norm)
    return normalized


def compute_market_skill_demand(df_role: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes per-posting skill demand percentages for a filtered role dataframe.
    One vote per skill per posting (deduplicated per posting).
    """
    total_postings = len(df_role)
    if total_postings == 0:
        return {"total_postings": 0, "skill_stats": {}}

    counter = Counter()
    for raw in df_role["key_skills_clean"].fillna(""):
        skills = set(tokenise_skills(raw))  # Deduplicate per posting after normalization
        counter.update(skills)

    skill_stats = {}
    for skill, count in counter.items():
        pct = round((count / total_postings) * 100, 2)
        skill_stats[skill] = {
            "count": count,
            "demand_pct": pct
        }

    return {
        "total_postings": total_postings,
        "skill_stats": skill_stats
    }


def compare_resume_to_market(
    candidate_input: Union[str, Path, Dict[str, Any]],
    target_role: str = "Data Engineer",
    csv_path: Optional[Union[str, Path]] = None,
    min_demand_threshold: float = 5.0,
    is_file_path: bool = False
) -> Dict[str, Any]:
    """
    Compares candidate resume skills & experience against market demand for `target_role`.

    Parameters:
        candidate_input: Candidate profile dict OR resume text OR path to resume file.
        target_role: Role name to filter market job postings (case-insensitive substring).
        csv_path: Optional path to jobs_clean.csv dataset.
        min_demand_threshold: Minimum market demand % threshold (default 5.0%).
        is_file_path: Set True if candidate_input is a path to a PDF/DOCX/TXT file.

    Returns:
        Structured comparison payload containing:
        - target_role (str)
        - posting_denominator (int)
        - evaluated_skill_count (int)
        - market_fit_pct (float)
        - matched_skills (List[dict])
        - missing_skills (List[dict])
        - experience_alignment (dict)
        - candidate_profile_summary (dict)
    """
    # 1. Obtain candidate profile
    if isinstance(candidate_input, dict) and "skills" in candidate_input:
        profile = candidate_input
    else:
        profile = process_resume(candidate_input, is_file_path=is_file_path)

    # Candidate skill set (normalized using normalization layer for exact matching)
    raw_cand_skills = profile.get("skills", [])
    cand_skill_tokens = set()
    for s in raw_cand_skills:
        norm_s = normalize_skill_token(s)
        if norm_s:
            cand_skill_tokens.add(norm_s)
        for token in tokenise_skills(s):
            cand_skill_tokens.add(token)

    cand_exp_years = profile.get("experience_years", 0)

    # 2. Load jobs dataset and filter by target role
    df_all = load_jobs_data(csv_path)
    if "role_clean" not in df_all.columns:
        raise KeyError("Column 'role_clean' not found in jobs dataset.")

    df_role = df_all[df_all["role_clean"].str.contains(target_role, case=False, na=False)]
    total_postings = len(df_role)

    if total_postings == 0:
        # Fallback if no matching role postings
        return {
            "target_role": target_role,
            "posting_denominator": 0,
            "evaluated_skill_count": 0,
            "market_fit_pct": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "all_missing_skills": [],
            "experience_alignment": {
                "candidate_exp_years": cand_exp_years,
                "market_min_exp_years": None,
                "market_median_exp_years": None,
                "market_max_exp_years": None,
                "status": "No market postings found for target role"
            },
            "candidate_profile_summary": {
                "extracted_skills": raw_cand_skills,
                "extracted_education": profile.get("education", []),
                "extracted_job_titles": profile.get("job_titles", [])
            }
        }

    # 3. Calculate market skill demand with normalization
    market_demand = compute_market_skill_demand(df_role)
    all_skill_stats = market_demand["skill_stats"]

    # 4. Filter to evaluated skills (demand_pct >= min_demand_threshold)
    evaluated_skills = [
        (skill, info["count"], info["demand_pct"])
        for skill, info in all_skill_stats.items()
        if info["demand_pct"] >= min_demand_threshold
    ]

    # Sort evaluated skills deterministically: demand_pct DESC, skill ASC
    evaluated_skills.sort(key=lambda x: (-x[2], x[0]))

    total_evaluated_demand_weight = sum(item[2] for item in evaluated_skills)
    matched_demand_weight = 0.0

    matched_skills = []
    missing_skills = []

    priority_counter = 1
    for skill, count, pct in evaluated_skills:
        # Check if candidate has skill
        norm_skill = normalize_skill_token(skill) or skill
        has_skill = norm_skill in cand_skill_tokens

        skill_entry = {
            "skill": skill,
            "demand_pct": pct,
            "posting_count": count
        }

        if has_skill:
            matched_demand_weight += pct
            matched_skills.append(skill_entry)
        else:
            skill_entry["priority_rank"] = priority_counter
            priority_counter += 1
            missing_skills.append(skill_entry)

    # 5. Calculate Market Fit %
    if total_evaluated_demand_weight > 0:
        market_fit_pct = round((matched_demand_weight / total_evaluated_demand_weight) * 100, 2)
    else:
        market_fit_pct = 0.0

    # 6. Experience Alignment Calculation
    exp_min_series = df_role["exp_min_years"].dropna().astype(float)
    exp_max_series = df_role["exp_max_years"].dropna().astype(float)

    market_min_exp = float(exp_min_series.min()) if not exp_min_series.empty else 0.0
    market_max_exp = float(exp_max_series.max()) if not exp_max_series.empty else 0.0
    market_median_min_exp = float(exp_min_series.median()) if not exp_min_series.empty else 0.0
    market_avg_min_exp = float(exp_min_series.mean()) if not exp_min_series.empty else 0.0

    if cand_exp_years < market_median_min_exp:
        exp_status = "Below Market Median"
    elif market_median_min_exp <= cand_exp_years <= market_max_exp:
        exp_status = "Aligned with Market"
    else:
        exp_status = "Exceeds Market Average"

    experience_alignment = {
        "candidate_exp_years": cand_exp_years,
        "market_min_exp_years": market_min_exp,
        "market_median_min_exp_years": round(market_median_min_exp, 1),
        "market_avg_min_exp_years": round(market_avg_min_exp, 1),
        "market_max_exp_years": market_max_exp,
        "status": exp_status
    }

    return {
        "target_role": target_role,
        "posting_denominator": total_postings,
        "evaluated_skill_count": len(evaluated_skills),
        "market_fit_pct": market_fit_pct,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills[:3],
        "all_missing_skills": missing_skills,
        "experience_alignment": experience_alignment,
        "candidate_profile_summary": {
            "extracted_skills": raw_cand_skills,
            "extracted_education": profile.get("education", []),
            "extracted_job_titles": profile.get("job_titles", []),
            "experience_years": cand_exp_years
        }
    }


if __name__ == "__main__":
    sample_resume_text = """
    JOHN DOE
    Senior Data Engineer
    Experience: 8+ years building scalable ETL pipelines in Python, SQL, Spark, Airflow, and AWS.
    Education: B.Tech in Computer Science
    Skills: Python, SQL, PySpark, Airflow, AWS, Docker, Git, PostgreSQL, Linux
    """

    report = compare_resume_to_market(
        candidate_input=sample_resume_text,
        target_role="Data Engineer"
    )

    print("=== MARKET-VS-RESUME COMPARISON REPORT (NORMALIZED) ===")
    print(json.dumps(report, indent=2))
