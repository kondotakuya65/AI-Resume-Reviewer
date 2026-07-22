"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { AnalysisSummary, api } from "@/lib/api";

export default function HistoryPage() {
  const [items, setItems] = useState<AnalysisSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listAnalyses()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load history"));
  }, []);

  return (
    <>
      <SiteHeader />
      <main className="page">
        <h1>Analysis history</h1>
        <p className="lead">Recent reviews for this guest session.</p>
        {error && <p className="error">{error}</p>}
        <div className="stack">
          {items.length === 0 && !error && <p className="muted">No analyses yet. Start a review first.</p>}
          {items.map((item) => (
            <Link key={item.id} href={`/review?analysis=${item.id}`} className="panel" style={{ display: "block" }}>
              <strong>{item.target_role || "Untitled review"}</strong>
              <p className="muted" style={{ margin: "0.35rem 0 0" }}>
                {item.status} · Overall {item.overall_score ?? "—"} · Match {item.job_match_score ?? "—"}% · ATS{" "}
                {item.ats_score ?? "—"} · {new Date(item.created_at).toLocaleString()}
              </p>
            </Link>
          ))}
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
