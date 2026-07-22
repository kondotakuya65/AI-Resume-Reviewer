"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { AnalysisResponse, api } from "@/lib/api";
import { DEMO_BULLET, DEMO_JD, DEMO_RESUME } from "@/lib/demo";

type Step = "upload" | "job" | "results";

export default function ReviewClient() {
  const router = useRouter();
  const params = useSearchParams();
  const demoMode = params.get("demo") === "1";

  const [step, setStep] = useState<Step>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [preview, setPreview] = useState("");
  const [jdText, setJdText] = useState(demoMode ? DEMO_JD : "");
  const [targetRole, setTargetRole] = useState("Senior Full-Stack Developer");
  const [experienceLevel, setExperienceLevel] = useState("senior");
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [rewriteOriginal, setRewriteOriginal] = useState(DEMO_BULLET);
  const [rewriteResult, setRewriteResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [disclaimer, setDisclaimer] = useState(
    "This analysis is AI-generated guidance and does not guarantee interviews, employment, or acceptance by applicant tracking systems."
  );

  useEffect(() => {
    api.health().then((h) => setDisclaimer(h.disclaimer)).catch(() => undefined);
    if (demoMode) {
      const blob = new Blob([DEMO_RESUME], { type: "text/plain" });
      setFile(new File([blob], "daniel_resume.txt", { type: "text/plain" }));
      setPreview(DEMO_RESUME.slice(0, 400) + "...");
      setJdText(DEMO_JD);
    }
  }, [demoMode]);

  useEffect(() => {
    const analysisId = params.get("analysis");
    if (!analysisId) return;
    api
      .getAnalysis(analysisId)
      .then((result) => {
        setAnalysis(result);
        setResumeId(result.resume_id);
        setDisclaimer(result.disclaimer);
        setStep("results");
      })
      .catch(() => undefined);
  }, [params]);

  const groupedRecs = useMemo(() => {
    const groups = { critical: [], important: [], optional: [] } as Record<
      string,
      AnalysisResponse["recommendations"]
    >;
    for (const r of analysis?.recommendations || []) {
      groups[r.priority]?.push(r);
    }
    return groups;
  }, [analysis]);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Choose a PDF, DOCX, or TXT resume.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.uploadResume(file);
      setResumeId(res.id);
      setPreview(res.extracted_text_preview);
      setStep("job");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function onAnalyze(e: FormEvent) {
    e.preventDefault();
    if (!resumeId) {
      setError("Upload a resume first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      let jobId: string | undefined;
      if (jdText.trim().length >= 20) {
        const jd = await api.createJobDescription(jdText, targetRole);
        jobId = jd.id;
      }
      const result = await api.createAnalysis({
        resume_id: resumeId,
        job_description_id: jobId,
        target_role: targetRole,
        experience_level: experienceLevel,
      });
      setAnalysis(result);
      setDisclaimer(result.disclaimer);
      setStep("results");
      router.replace(`/review?analysis=${result.id}${demoMode ? "&demo=1" : ""}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRewrite() {
    if (!analysis) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.rewrite({
        analysis_id: analysis.id,
        section_type: "experience_bullet",
        original_text: rewriteOriginal,
        instruction: "Add measurable impact and stronger action verbs",
      });
      setRewriteResult(res.rewritten_text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rewrite failed");
    } finally {
      setBusy(false);
    }
  }

  async function onExport() {
    if (!analysis) return;
    setBusy(true);
    try {
      const res = await api.exportAnalysis(analysis.id);
      const blob = new Blob([res.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `resume-signal-${analysis.id}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteResume() {
    if (!resumeId) return;
    setBusy(true);
    try {
      await api.deleteResume(resumeId);
      setResumeId(null);
      setFile(null);
      setAnalysis(null);
      setPreview("");
      setStep("upload");
      router.replace(demoMode ? "/review?demo=1" : "/review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <SiteHeader />
      <main className="page">
        <h1>Resume review</h1>
        <p className="lead">
          Continue as a guest — we store a session cookie so you can revisit analysis history on this
          browser.
        </p>

        {error && <p className="error">{error}</p>}

        {step === "upload" && (
          <form className="panel stack" onSubmit={onUpload}>
            <label>
              Upload resume (PDF, DOCX, TXT)
              <input
                type="file"
                accept=".pdf,.docx,.txt,application/pdf,text/plain"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            {preview && (
              <div>
                <p className="muted">Extract preview</p>
                <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{preview}</pre>
              </div>
            )}
            <button className="btn btn-primary" disabled={busy} type="submit">
              {busy ? "Uploading…" : "Continue"}
            </button>
          </form>
        )}

        {step === "job" && (
          <form className="panel stack" onSubmit={onAnalyze}>
            <label>
              Target role
              <input value={targetRole} onChange={(e) => setTargetRole(e.target.value)} type="text" />
            </label>
            <label>
              Experience level
              <select value={experienceLevel} onChange={(e) => setExperienceLevel(e.target.value)}>
                <option value="junior">Junior</option>
                <option value="mid">Mid</option>
                <option value="senior">Senior</option>
                <option value="lead">Lead</option>
              </select>
            </label>
            <label>
              Job description (optional but recommended)
              <textarea value={jdText} onChange={(e) => setJdText(e.target.value)} />
            </label>
            {preview && <p className="muted">Resume loaded. Preview: {preview.slice(0, 120)}…</p>}
            <div className="cta-row">
              <button className="btn btn-secondary" type="button" onClick={() => setStep("upload")}>
                Back
              </button>
              <button className="btn btn-primary" disabled={busy} type="submit">
                {busy ? "Analyzing…" : "Run AI analysis"}
              </button>
            </div>
          </form>
        )}

        {step === "results" && analysis && (
          <div className="stack">
            <div className="score-row">
              <div className="score">
                <span className="muted">Overall</span>
                <strong>{analysis.scores?.overall_score ?? "—"}/100</strong>
              </div>
              <div className="score" style={{ animationDelay: "80ms" }}>
                <span className="muted">Job match</span>
                <strong>{analysis.scores?.job_match_score ?? "—"}%</strong>
              </div>
              <div className="score" style={{ animationDelay: "160ms" }}>
                <span className="muted">ATS guidance</span>
                <strong>{analysis.scores?.ats_score ?? "—"}/100</strong>
              </div>
            </div>

            <div className="grid-2">
              <section className="panel">
                <h2>Matched skills</h2>
                <div className="chips">
                  {(analysis.matched_skills || []).map((s) => (
                    <span className="chip" key={s}>
                      {s}
                    </span>
                  ))}
                </div>
              </section>
              <section className="panel">
                <h2>Missing keywords</h2>
                <div className="chips">
                  {(analysis.missing_keywords || []).map((s) => (
                    <span className="chip missing" key={s}>
                      {s}
                    </span>
                  ))}
                </div>
              </section>
            </div>

            <div className="grid-2">
              <section className="panel">
                <h2>Strengths</h2>
                <ul>
                  {analysis.strengths.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </section>
              <section className="panel">
                <h2>Weaknesses</h2>
                <ul>
                  {analysis.weaknesses.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </section>
            </div>

            <section className="panel stack">
              <h2>Recommendations</h2>
              {(["critical", "important", "optional"] as const).map((priority) => (
                <div key={priority} className="stack">
                  <h3 style={{ margin: 0, textTransform: "capitalize" }}>{priority}</h3>
                  {(groupedRecs[priority] || []).map((r) => (
                    <div className={`rec ${priority}`} key={r.id}>
                      <strong>{r.section}</strong> — {r.message}
                    </div>
                  ))}
                </div>
              ))}
            </section>

            <section className="panel stack">
              <h2>Rewrite a bullet</h2>
              <label>
                Original text
                <textarea value={rewriteOriginal} onChange={(e) => setRewriteOriginal(e.target.value)} />
              </label>
              <button className="btn btn-primary" type="button" disabled={busy} onClick={onRewrite}>
                {busy ? "Rewriting…" : "Generate rewrite"}
              </button>
              {rewriteResult && (
                <div className="before-after">
                  <div>
                    <p className="muted">Before</p>
                    <pre>{rewriteOriginal}</pre>
                  </div>
                  <div>
                    <p className="muted">After</p>
                    <pre>{rewriteResult}</pre>
                  </div>
                </div>
              )}
            </section>

            <div className="cta-row">
              <button className="btn btn-primary" type="button" disabled={busy} onClick={onExport}>
                Export Markdown report
              </button>
              <button className="btn btn-secondary" type="button" disabled={busy} onClick={onDeleteResume}>
                Delete uploaded resume
              </button>
            </div>
            <p className="muted">
              Model: {analysis.model_name || "n/a"} · Status: {analysis.status}
            </p>
          </div>
        )}
      </main>
      <SiteFooter disclaimer={disclaimer} />
    </>
  );
}
