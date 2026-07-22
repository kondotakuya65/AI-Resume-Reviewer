import pytest

from app.services.scoring import compute_scores
from app.services.resume_extractor import detect_ats_issues, extract_text_from_bytes, normalize_text


def test_compute_scores_clamps_and_sums():
    result = compute_scores(
        {
            "content_quality": 30,
            "job_relevance": 21,
            "achievements": 8,
            "skills_match": 13,
            "readability": 8,
            "ats_compatibility": 7,
            "skill_match_pct": 71,
            "experience_match_pct": 80,
            "keyword_match_pct": 75,
            "responsibility_match_pct": 70,
        },
        ats_heuristic={"ats_score": 7},
    )
    assert result["content_quality"] == 25
    assert result["overall_score"] == sum(
        [
            result["content_quality"],
            result["job_relevance"],
            result["achievements"],
            result["skills_match"],
            result["readability"],
            result["ats_compatibility"],
        ]
    )
    assert 0 <= result["job_match_score"] <= 100
    assert 0 <= result["ats_score"] <= 100


def test_normalize_and_extract_txt():
    data = b"Hello\r\n\r\nWorld\n\n\nExtra"
    text = extract_text_from_bytes(data, "resume.txt", "text/plain")
    assert "Hello" in text
    assert "World" in text
    assert normalize_text("a  \n\n\nb") == "a\n\nb"


def test_ats_inconsistent_dates():
    text = "Software Engineer Jan 2020 - Dec 2021\nDeveloper 03/2018 - 2019\n" + ("word " * 100)
    result = detect_ats_issues(text)
    assert any("Inconsistent date" in i for i in result["issues"])
    assert result["ats_score"] <= 10
