from typing import Any


CATEGORY_MAX = {
    "content_quality": 25,
    "job_relevance": 25,
    "achievements": 15,
    "skills_match": 15,
    "readability": 10,
    "ats_compatibility": 10,
}


def clamp(value: Any, lo: int, hi: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = lo
    return max(lo, min(hi, n))


def compute_scores(llm_scores: dict[str, Any], ats_heuristic: dict[str, Any] | None = None) -> dict[str, int]:
    """Backend-owned scoring: clamp category scores and derive totals."""
    categories = {
        key: clamp(llm_scores.get(key, 0), 0, max_v) for key, max_v in CATEGORY_MAX.items()
    }

    # Blend heuristic ATS (0-10) with LLM ats_compatibility
    if ats_heuristic is not None:
        heuristic = clamp(ats_heuristic.get("ats_score", 7), 0, 10)
        categories["ats_compatibility"] = round((categories["ats_compatibility"] + heuristic) / 2)

    overall = sum(categories.values())
    skill_pct = clamp(llm_scores.get("skill_match_pct", categories["skills_match"] * 100 // 15), 0, 100)
    exp_pct = clamp(llm_scores.get("experience_match_pct", 70), 0, 100)
    keyword_pct = clamp(llm_scores.get("keyword_match_pct", 70), 0, 100)
    resp_pct = clamp(llm_scores.get("responsibility_match_pct", 70), 0, 100)
    job_match = round((skill_pct + exp_pct + keyword_pct + resp_pct) / 4)
    ats_score = round(categories["ats_compatibility"] * 10)  # present as /100

    return {
        **categories,
        "overall_score": overall,
        "job_match_score": job_match,
        "ats_score": ats_score,
        "skill_match_pct": skill_pct,
        "experience_match_pct": exp_pct,
        "keyword_match_pct": keyword_pct,
        "responsibility_match_pct": resp_pct,
    }
