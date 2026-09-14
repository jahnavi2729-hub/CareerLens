"""
CareerLens Career Mentor Module (Groq LLM Layer)
-------------------------------------------------
Humanized LLM-powered Career Mentor layer for CareerLens using Groq.
Receives ONLY deterministic comparison results and generates an encouraging, professional
explanation covering candidate strengths, current position, and top 3 actionable opportunities.

Maintains strict separation:
- ZERO score / percentage / skill recalculation by the LLM
- Deterministic comparison engine remains 100% source of truth
- Uses GROQ_API_KEY securely from environment variables / .env files
- Graceful deterministic fallback when no LLM API key is present
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Load environment variables from .env / groq.env if available
try:
    from dotenv import load_dotenv
    for env_name in [".env", "groq.env"]:
        if Path(env_name).exists():
            load_dotenv(env_name)
        if (Path.home() / env_name).exists():
            load_dotenv(Path.home() / env_name)
except ImportError:
    pass

SYSTEM_PROMPT = """You are CareerLens AI Mentor, an encouraging, executive-level career coach.
Your task is to provide a warm, humanized, and empowering career assessment for a candidate based STRICTLY on the deterministic market data provided.

STRICT CONSTRAINTS:
1. You MUST NOT calculate, change, or invent any numbers, scores, percentages, skills, or experience values.
2. The deterministic data provided is your ONLY source of truth.
3. Formulate your response in 3 structured, humanized sections:
   - STRENGTHS: Celebrate their matched skills and background.
   - MARKET POSITION: Provide encouraging context on their Market Skill Coverage (%) and experience alignment.
   - TOP OPPORTUNITIES: Offer actionable encouragement for their Top 3 missing skills.
4. Keep your tone professional, motivating, and concise (max 200 words).
"""


def generate_deterministic_fallback_mentor_summary(comparison: Dict[str, Any]) -> Dict[str, Any]:
    """Generates structured mentor feedback deterministically if LLM is unavailable."""
    target_role = comparison.get("target_role", "Target Role")
    fit_pct = comparison.get("market_fit_pct", 0.0)
    matched_skills = comparison.get("matched_skills", [])
    missing_skills = comparison.get("missing_skills", [])[:3]
    exp_align = comparison.get("experience_alignment", {})
    exp_years = exp_align.get("candidate_exp_years", 0)
    exp_status = exp_align.get("status", "Evaluating")

    matched_names = [s["skill"].title() for s in matched_skills]

    if matched_names:
        strengths_text = (
            f"You demonstrate strong core alignment for {target_role} roles. Your proficiency in "
            f"{', '.join(matched_names[:4])} directly satisfies active employer demand."
        )
    else:
        strengths_text = (
            f"Your foundational skill set provides a solid starting point for targeting {target_role} positions."
        )

    position_text = (
        f"Your current Market Skill Coverage is {fit_pct}%. With {exp_years} years of "
        f"recognized experience ({exp_status}), targeted learning in high-demand skills will unlock high-impact opportunities."
    )

    if missing_skills:
        opp_items = [
            f"• {s['skill'].title()} ({s['demand_pct']}% demand across {s['posting_count']} jobs): Build a practical project using {s['skill'].title()}."
            for s in missing_skills
        ]
        opportunities_text = "Prioritize these top 3 high-impact skill opportunities:\n" + "\n".join(opp_items)
    else:
        opportunities_text = "You match all evaluated core skills for this role!"

    full_summary = f"{strengths_text}\n\n{position_text}\n\n{opportunities_text}"

    return {
        "headline": f"Career Mentor Guidance for {target_role}",
        "strengths": strengths_text,
        "current_position": position_text,
        "top_opportunities": opportunities_text,
        "full_text": full_summary,
        "is_llm_generated": False,
        "llm_provider": "deterministic-fallback"
    }


def generate_career_mentor_feedback(comparison: Dict[str, Any]) -> Dict[str, Any]:
    """
    Integrates Groq LLM to generate personalized, humanized Career Mentor advice.
    Passes ONLY deterministic facts to the LLM.
    """
    target_role = comparison.get("target_role", "Target Role")
    fit_pct = comparison.get("market_fit_pct", 0.0)
    matched_skills = comparison.get("matched_skills", [])
    missing_skills = comparison.get("missing_skills", [])[:3]
    exp_align = comparison.get("experience_alignment", {})

    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not (groq_key or gemini_key or openai_key):
        return generate_deterministic_fallback_mentor_summary(comparison)

    # Payload with ONLY deterministic facts
    prompt_facts = {
        "target_role": target_role,
        "market_skill_coverage_pct": fit_pct,
        "matched_skills": [{"skill": s["skill"], "demand_pct": s["demand_pct"]} for s in matched_skills],
        "top_3_opportunity_skills": [{"skill": s["skill"], "demand_pct": s["demand_pct"], "posting_count": s["posting_count"]} for s in missing_skills],
        "candidate_experience_years": exp_align.get("candidate_exp_years", 0),
        "experience_alignment_status": exp_align.get("status", "")
    }

    user_prompt = f"""Humanize the following deterministic career comparison facts into encouraging mentor guidance:
{json.dumps(prompt_facts, indent=2)}

Format with 3 distinct paragraphs or sections:
STRENGTHS: <matched skills summary>
MARKET POSITION: <Market Skill Coverage % and experience status perspective>
TOP OPPORTUNITIES: <actionable encouragement for top 3 missing skills>
"""

    # 1. Groq Integration (Primary)
    if groq_key:
        try:
            import openai
            client = openai.OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            
            response = client.chat.completions.create(
                model="groq/compound-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=400,
                temperature=0.4
            )
            llm_text = response.choices[0].message.content.strip()
            if llm_text:
                return {
                    "headline": f"Career Mentor Guidance for {target_role}",
                    "full_text": llm_text,
                    "is_llm_generated": True,
                    "llm_provider": "Groq (groq/compound-mini)"
                }
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}. Attempting fallback providers.")

    # 2. Gemini Fallback
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=SYSTEM_PROMPT + "\n\n" + user_prompt
            )
            if response.text and response.text.strip():
                return {
                    "headline": f"Career Mentor Guidance for {target_role}",
                    "full_text": response.text.strip(),
                    "is_llm_generated": True,
                    "llm_provider": "Gemini"
                }
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")

    # 3. OpenAI Fallback
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )
            if response.choices[0].message.content:
                return {
                    "headline": f"Career Mentor Guidance for {target_role}",
                    "full_text": response.choices[0].message.content.strip(),
                    "is_llm_generated": True,
                    "llm_provider": "OpenAI"
                }
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}")

    return generate_deterministic_fallback_mentor_summary(comparison)
