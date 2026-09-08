'''skill_demand_intelligence.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reusable analysis module that computes skill demand for any role (or role filter) using the
CareerLens `jobs_clean.csv` dataset.

The current configuration (as requested) analyses all postings whose `role_clean`
contains the phrase "Data Engineer" (case‑insensitive).  It produces:

* overall skill frequency and percentage (relative to the total filtered postings)
* skill frequency and percentage broken down by experience groups:
    - **Early**  : 0 ≤ exp_min_years < 3 years
    - **Mid**    : 3 ≤ exp_min_years < 10 years
    - **Senior** : exp_min_years ≥ 10 years
* denominators (number of postings) for each aggregation level

The script is **stand‑alone** – run it from the project root or any working directory:

```
python -m src.skill_demand_intelligence
```

It prints a JSON document to STDOUT that can be consumed by downstream code or a UI.
''' 

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration – adjust only if you want to reuse the module for another role
# ---------------------------------------------------------------------------
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "jobs_clean.csv"
ROLE_FILTER = "Data Engineer"  # inclusive substring filter (case‑insensitive)

# Experience bucket definitions (in years)
EXP_BUCKETS = {
    "Early": (0, 3),   # 0 ≤ exp < 3
    "Mid": (3, 10),   # 3 ≤ exp < 10
    "Senior": (10, None),  # exp ≥ 10
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def load_dataframe(csv_path: Path) -> pd.DataFrame:
    """Load the CSV into a DataFrame, raising a clear error if it fails."""
    if not csv_path.is_file():
        sys.exit(json.dumps({"error": f"CSV not found at {csv_path}"}))
    return pd.read_csv(csv_path)

def filter_role(df: pd.DataFrame, phrase: str) -> pd.DataFrame:
    """Return rows where `role_clean` contains *phrase* (case‑insensitive)."""
    if "role_clean" not in df.columns:
        sys.exit(json.dumps({"error": "Missing column 'role_clean' in CSV"}))
    return df[df["role_clean"].str.contains(phrase, case=False, na=False)]

def tokenise_skills(skills_raw: str) -> list:
    """Split a raw `key_skills_clean` string into a list of cleaned skill tokens.

    The dataset uses commas as the primary delimiter.  We also strip whitespace
    and normalise to lower‑case.  Empty tokens are discarded.
    """
    if pd.isna(skills_raw):
        return []
    # Primary delimiter is a comma; fall back to semicolon/pipe if needed.
    for delim in [",", ";", "|"]:
        if delim in skills_raw:
            parts = [p.strip().lower() for p in skills_raw.split(delim)]
            return [p for p in parts if p]
    # No delimiter found – treat the whole string as a single skill token.
    skill = skills_raw.strip().lower()
    return [skill] if skill else []

def assign_experience_bucket(exp_min) -> str:
    """Map a numeric `exp_min_years` value to one of the experience buckets.
    Returns "Unknown" if the value is missing or cannot be cast to a number.
    """
    if pd.isna(exp_min):
        return "Unknown"
    try:
        years = float(exp_min)
    except (ValueError, TypeError):
        return "Unknown"
    for bucket, (low, high) in EXP_BUCKETS.items():
        if high is None:
            if years >= low:
                return bucket
        elif low <= years < high:
            return bucket
    return "Unknown"

def compute_skill_stats(df: pd.DataFrame) -> dict:
    """Core computation – returns a dictionary ready for JSON serialisation.
    The function assumes `df` has already been filtered to the target role.
    """
    total_posts = len(df)

    # Overall skill aggregation
    overall_counter = Counter()
    for raw in df["key_skills_clean"].fillna(""):
        skills = set(tokenise_skills(raw))  # per‑posting deduplication
        overall_counter.update(skills)
    overall_stats = [
        {
            "skill": skill,
            "count": count,
            "percentage": round(count / total_posts * 100, 2) if total_posts else 0,
        }
        for skill, count in overall_counter.most_common()
    ]

    # Experience‑bucketed aggregation
    df = df.copy()
    df["exp_bucket"] = df["exp_min_years"].apply(assign_experience_bucket)
    bucket_stats = {}
    for bucket in EXP_BUCKETS.keys():
        bucket_df = df[df["exp_bucket"] == bucket]
        bucket_total = len(bucket_df)
        counter = Counter()
        for raw in bucket_df["key_skills_clean"].fillna(""):
            skills = set(tokenise_skills(raw))
            counter.update(skills)
        bucket_stats[bucket] = {
            "postings": bucket_total,
            "skill_counts": [
                {
                    "skill": skill,
                    "count": cnt,
                    "percentage": round(cnt / bucket_total * 100, 2) if bucket_total else 0,
                }
                for skill, cnt in counter.most_common()
            ],
        }
    return {
        "role_filter": ROLE_FILTER,
        "total_postings": total_posts,
        "overall_skill_distribution": overall_stats,
        "experience_groups": bucket_stats,
    }

if __name__ == "__main__":
    df = load_dataframe(CSV_PATH)
    filtered = filter_role(df, ROLE_FILTER)
    result = compute_skill_stats(filtered)
    print(json.dumps(result, indent=2, ensure_ascii=False))
