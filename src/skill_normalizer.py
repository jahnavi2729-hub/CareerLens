"""
CareerLens Skill Normalization Layer
------------------------------------
Deterministic normalization layer for market skill intelligence and candidate benchmark comparisons.

Responsibilities:
1. Filters out job-title / domain-label terms (e.g., 'data engineer', 'data engineering')
   from technical skill benchmarking.
2. Canonicalizes alias variants (e.g., 'data pipelines' -> 'data pipeline',
   'microsoft azure' -> 'azure', 'google cloud' -> 'gcp', 'amazon web services' -> 'aws').
3. Unifies technology families (e.g., 'pyspark' -> 'spark', 'azure databricks' / 'data bricks' -> 'databricks')
   to prevent per-posting double counting.
"""

from typing import List, Set, Optional, Any
import pandas as pd

# Job-title / domain terms to exclude from technical skill benchmarking
JOB_TITLE_NON_SKILLS: Set[str] = {
    "data engineer",
    "data engineering",
    "senior data engineer",
    "lead data engineer",
    "principal data engineer",
    "software engineer",
    "software engineering",
    "data scientist",
    "data science",
    "business analyst",
    "data analyst",
    "systems engineer",
    "cloud engineer",
    "devops engineer",
}

# Alias & Variant Canonicalization Dictionary
CANONICAL_ALIAS_MAP: dict[str, str] = {
    # Spark family (unifies Spark & PySpark without double counting)
    "pyspark": "spark",
    "apache spark": "spark",
    
    # Databricks variants
    "azure databricks": "databricks",
    "data bricks": "databricks",
    "databricks": "databricks",
    
    # Cloud Platform Providers
    "microsoft azure": "azure",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "amazon web services": "aws",
    
    # Plural & Minor Syntactic Variants
    "data pipelines": "data pipeline",
    "data analytics": "analytics",
    "business intelligence": "bi",
    
    # Database & Storage Aliases
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mongo": "mongodb",
}


def normalize_skill_token(token: Any) -> Optional[str]:
    """
    Normalizes a single skill string token.
    Returns canonical skill string or None if token is a non-skill job title term.
    """
    if pd.isna(token) or not str(token).strip():
        return None
    
    cleaned = str(token).strip().lower()
    if not cleaned:
        return None

    # Exclude job-title terms
    if cleaned in JOB_TITLE_NON_SKILLS:
        return None

    # Apply canonical mapping if present
    return CANONICAL_ALIAS_MAP.get(cleaned, cleaned)


def normalize_skill_list(raw_skills: List[str]) -> List[str]:
    """
    Normalizes a list of skill tokens, removing duplicates while maintaining order.
    """
    normalized = []
    seen = set()
    for s in raw_skills:
        norm = normalize_skill_token(s)
        if norm and norm not in seen:
            seen.add(norm)
            normalized.append(norm)
    return normalized
