'''company_hiring_intelligence.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Analysis module that computes hiring volume per company and skill demand
percentages for Data Engineer‑related postings.

The implementation mirrors the validated tokenisation logic from
`skill_demand_intelligence.py`:
* split on commas, semicolons or pipes
* lower‑case and strip whitespace
* deduplicate **per posting**

For each company we report:
* `postings` – number of Data Engineer postings belonging to the company
* `skill_distribution` – list of skills with `count` (unique postings that mention
  the skill) and `percentage` (count / postings * 100)
* `top_skills` – the same list ordered by count (the full list is returned; callers
  can slice as needed)

The script can be executed directly:

```bash
python -m src.company_hiring_intelligence
```

It prints a JSON document to STDOUT.
''' 

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration – adjust only if re‑using the module for another role
# ---------------------------------------------------------------------------
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "jobs_clean.csv"
ROLE_FILTER = "Data Engineer"  # inclusive substring filter (case‑insensitive)

# ---------------------------------------------------------------------------
# Helper functions – identical to the validated implementation
# ---------------------------------------------------------------------------
def load_dataframe(csv_path: Path) -> pd.DataFrame:
    """Load the CSV into a DataFrame, exiting with a JSON error on failure."""
    if not csv_path.is_file():
        sys.exit(json.dumps({"error": f"CSV not found at {csv_path}"}))
    return pd.read_csv(csv_path)

def filter_role(df: pd.DataFrame, phrase: str) -> pd.DataFrame:
    """Return rows where `role_clean` contains *phrase* (case‑insensitive)."""
    if "role_clean" not in df.columns:
        sys.exit(json.dumps({"error": "Missing column 'role_clean' in CSV"}))
    return df[df["role_clean"].str.contains(phrase, case=False, na=False)]

def tokenise_skills(skills_raw: str) -> list:
    """Split a raw `key_skills_clean` string into a cleaned list of tokens.

    * primary delimiter is a comma; fall back to semicolon or pipe
    * strip whitespace, lower‑case
    * discard empty tokens
    """
    if pd.isna(skills_raw):
        return []
    for delim in [",", ";", "|"]:
        if delim in skills_raw:
            parts = [p.strip().lower() for p in skills_raw.split(delim)]
            return [p for p in parts if p]
    skill = skills_raw.strip().lower()
    return [skill] if skill else []

# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------
def compute_company_stats(df: pd.DataFrame) -> dict:
    """Return a dict keyed by company with hiring volume and skill percentages.

    The function assumes `df` is already filtered to the target role.
    """
    # Group by company name (cleaned if available, otherwise raw)
    company_col = "company_name_clean" if "company_name_clean" in df.columns else "company_name"
    df = df.copy()
    df["company"] = df[company_col]

    # Overall posting count per company
    postings_per_company = df.groupby("company").size().to_dict()

    # Initialise a Counter for each company
    company_counters: dict[str, Counter] = {comp: Counter() for comp in postings_per_company}

    # Iterate through rows, update per‑company counters with deduplicated skill sets
    for company, skills_raw in df[["company", "key_skills_clean"]].itertuples(index=False):
        skills = set(tokenise_skills(skills_raw))  # per‑posting deduplication
        company_counters[company].update(skills)

    # Build the output structure
    result = {}
    for company, postings in postings_per_company.items():
        counter = company_counters[company]
        skill_stats = [
            {
                "skill": skill,
                "count": count,
                "percentage": round(count / postings * 100, 2) if postings else 0,
            }
            for skill, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        result[company] = {
            "postings": postings,
            "skill_distribution": skill_stats,
        }
    return result

# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df = load_dataframe(CSV_PATH)
    filtered = filter_role(df, ROLE_FILTER)
    stats = compute_company_stats(filtered)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
