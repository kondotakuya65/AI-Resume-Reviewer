import json
import re
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings


class LLMClient(Protocol):
    model_name: str

    async def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict[str, Any]:
        ...


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("LLM did not return valid JSON")
        return json.loads(match.group(0))


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model_name = settings.ollama_model

    async def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        # Keep per-call timeout bounded so slow local models fall back instead of hanging forever
        timeout = httpx.Timeout(90.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
        return _extract_json(content)


class OpenAIClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model_name = settings.openai_model

    async def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        return _extract_json(content)


class AnthropicClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        self.api_key = settings.anthropic_api_key
        self.model_name = settings.anthropic_model

    async def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "max_tokens": 4096,
            "temperature": 0.2,
            "system": system + "\nAlways respond with a single valid JSON object only.",
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = "".join(part.get("text", "") for part in data.get("content", []) if part.get("type") == "text")
        return _extract_json(content)


class MockLLMClient:
    """Deterministic fallback when providers are unreachable (portfolio demos / tests)."""

    model_name = "mock-llm"

    async def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict[str, Any]:
        lower = (system + user).lower()
        if "parse the resume" in lower or "extract structured resume" in lower:
            return {
                "name": "Daniel Chen",
                "contact": {"email": "daniel@example.com", "location": "Seattle, WA"},
                "summary": "Software engineer with experience building web applications.",
                "skills": ["Python", "FastAPI", "React", "AWS", "PostgreSQL"],
                "experience": [
                    {
                        "title": "Full-Stack Developer",
                        "company": "Nimbus Labs",
                        "dates": "2021 - Present",
                        "bullets": [
                            "Developed backend APIs using FastAPI.",
                            "Worked on React frontend features.",
                            "Maintained PostgreSQL databases.",
                        ],
                    },
                    {
                        "title": "Software Engineer",
                        "company": "BrightApps",
                        "dates": "01/2019 - 2021",
                        "bullets": [
                            "Built internal tools with Python.",
                            "Deployed services on AWS.",
                        ],
                    },
                ],
                "education": [{"degree": "B.S. Computer Science", "school": "State University", "dates": "2018"}],
                "certifications": [],
                "projects": [
                    {
                        "name": "Inventory API",
                        "description": "Built a FastAPI service for inventory tracking.",
                    }
                ],
            }
        if "parse the job" in lower or "extract job requirements" in lower:
            return {
                "required_skills": ["Python", "FastAPI", "React", "AWS", "PostgreSQL", "Docker", "CI/CD"],
                "preferred_skills": ["Next.js", "pytest", "Terraform"],
                "experience_requirements": "5+ years software engineering",
                "education_requirements": "Bachelor's degree or equivalent",
                "responsibilities": [
                    "Design and ship full-stack features",
                    "Own CI/CD and containerized deployments",
                    "Mentor teammates and communicate clearly",
                ],
                "industry_keywords": ["microservices", "REST", "cloud", "observability"],
                "seniority_level": "senior",
            }
        if "compare" in lower or "category scores" in lower or "recommendations" in lower:
            return {
                "content_quality": 18,
                "job_relevance": 20,
                "achievements": 7,
                "skills_match": 12,
                "readability": 8,
                "ats_compatibility": 7,
                "skill_match_pct": 71,
                "experience_match_pct": 80,
                "keyword_match_pct": 75,
                "responsibility_match_pct": 70,
                "strengths": [
                    "Strong Python and FastAPI experience",
                    "Relevant AWS cloud background",
                    "Clear employment history",
                ],
                "weaknesses": [
                    "Achievements are not quantified",
                    "Docker is missing",
                    "Professional summary is generic",
                ],
                "missing_keywords": ["Docker", "CI/CD", "pytest", "Automated testing", "Team leadership"],
                "matched_skills": ["Python", "FastAPI", "AWS", "PostgreSQL", "React"],
                "recommendations": [
                    {
                        "priority": "critical",
                        "section": "skills",
                        "message": "Add Docker if you have practical experience with it.",
                    },
                    {
                        "priority": "critical",
                        "section": "skills",
                        "message": "Mention CI/CD tools or pipelines you have used.",
                    },
                    {
                        "priority": "important",
                        "section": "experience",
                        "message": "Add measurable outcomes to your latest two positions.",
                    },
                    {
                        "priority": "important",
                        "section": "summary",
                        "message": "Rewrite the professional summary to target Senior Full-Stack Developer.",
                    },
                    {
                        "priority": "optional",
                        "section": "formatting",
                        "message": "Normalize date formats across all roles.",
                    },
                    {
                        "priority": "optional",
                        "section": "summary",
                        "message": "Shorten the professional summary to three focused lines.",
                    },
                ],
            }
        if "rewrite" in lower:
            original = ""
            m = re.search(r"Original text:\n([\s\S]+?)(?:\n\n|$)", user)
            if m:
                original = m.group(1).strip()
            if "fastapi" in original.lower():
                return {
                    "rewritten_text": (
                        "Designed and deployed 18 FastAPI endpoints supporting more than "
                        "30,000 monthly requests, reducing average response time by 35%."
                    )
                }
            if "summary" in lower or "professional summary" in original.lower() or len(original) > 80:
                return {
                    "rewritten_text": (
                        "Senior-leaning full-stack engineer with 5+ years building Python/FastAPI "
                        "backends and React frontends on AWS and PostgreSQL. Known for shipping "
                        "reliable APIs and collaborating across product and infrastructure teams."
                    )
                }
            return {
                "rewritten_text": (
                    f"Led delivery of {original.rstrip('.')} with measurable impact on reliability, "
                    "latency, and stakeholder outcomes."
                )
            }
        return {"result": "ok"}


def get_llm_client(settings: Settings | None = None, *, allow_mock: bool = True) -> LLMClient:
    settings = settings or get_settings()
    try:
        if settings.llm_provider == "openai":
            return OpenAIClient(settings)
        if settings.llm_provider == "anthropic":
            return AnthropicClient(settings)
        return OllamaClient(settings)
    except ValueError:
        if allow_mock:
            return MockLLMClient()
        raise


async def safe_complete_json(
    client: LLMClient, system: str, user: str, schema: dict | None = None
) -> dict[str, Any]:
    """Call LLM; fall back to mock on connection/provider errors for demo resilience."""
    try:
        return await client.complete_json(system, user, schema)
    except Exception:
        mock = MockLLMClient()
        return await mock.complete_json(system, user, schema)
