import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Configure env before importing app modules
TMP = Path(__file__).resolve().parent / "_tmp"
TMP.mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{(TMP / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(TMP / "uploads")
os.environ["LLM_PROVIDER"] = "ollama"
# Ensure tests never wait on a real Ollama instance
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9"

from app.core.config import get_settings

get_settings.cache_clear()

from app.db.session import engine, init_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.llm import MockLLMClient  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db(monkeypatch):
    from app.services.llm import MockLLMClient

    monkeypatch.setattr(
        "app.services.analysis.get_llm_client",
        lambda settings=None, allow_mock=True: MockLLMClient(),
    )
    init_db()
    yield
    # cleanup tables between tests
    from app.db.session import Base

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.mark.asyncio
async def test_mock_llm_parse_and_compare():
    client = MockLLMClient()
    resume = await client.complete_json("Parse the resume", "resume text")
    assert "skills" in resume
    jd = await client.complete_json("Parse the job description", "job text")
    assert "required_skills" in jd
    compare = await client.complete_json("Compare and category scores recommendations", "data")
    assert len(compare["recommendations"]) >= 5
    rewrite = await client.complete_json(
        "Rewrite experience bullet",
        "Original text:\nDeveloped backend APIs using FastAPI.\n",
    )
    assert "30,000" in rewrite["rewritten_text"]


@pytest.mark.asyncio
async def test_health_and_upload_flow():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "disclaimer" in body

        files = {"file": ("daniel.txt", b"Daniel Chen\nPython FastAPI React AWS PostgreSQL\n" + b"experience " * 40, "text/plain")}
        up = await ac.post("/api/resumes/upload", files=files)
        assert up.status_code == 200, up.text
        resume_id = up.json()["id"]

        jd = await ac.post(
            "/api/job-descriptions",
            json={"title": "Senior Full-Stack", "raw_text": "Need Python FastAPI React AWS PostgreSQL Docker CI/CD " * 3},
        )
        assert jd.status_code == 200, jd.text

        analysis = await ac.post(
            "/api/analyses",
            json={
                "resume_id": resume_id,
                "job_description_id": jd.json()["id"],
                "target_role": "Senior Full-Stack Developer",
                "experience_level": "senior",
            },
        )
        assert analysis.status_code == 200, analysis.text
        data = analysis.json()
        assert data["status"] in {"running", "pending", "completed"}

        # Background task finishes after the POST response is built
        for _ in range(30):
            if data["status"] in {"completed", "failed"}:
                break
            polled = await ac.get(f"/api/analyses/{data['id']}")
            assert polled.status_code == 200
            data = polled.json()

        assert data["status"] == "completed", data.get("error_message")
        assert data["scores"]["overall_score"] > 0
        assert len(data["recommendations"]) >= 5

        rewrite = await ac.post(
            "/api/rewrites",
            json={
                "analysis_id": data["id"],
                "section_type": "experience_bullet",
                "original_text": "Developed backend APIs using FastAPI.",
            },
        )
        assert rewrite.status_code == 200, rewrite.text
        assert "FastAPI" in rewrite.json()["rewritten_text"]

        export = await ac.get(f"/api/analyses/{data['id']}/export")
        assert export.status_code == 200
        assert "Overall" in export.json()["markdown"]

        deleted = await ac.delete(f"/api/resumes/{resume_id}")
        assert deleted.status_code == 200
