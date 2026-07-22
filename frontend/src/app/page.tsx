import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/SiteChrome";

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main className="hero">
        <div className="hero-copy" style={{ animation: "fadeUp 700ms ease both" }}>
          <p className="muted" style={{ fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase" }}>
            ResumeSignal
          </p>
          <h1>See how your resume reads to the role you want.</h1>
          <p>
            Upload a resume, paste a job description, and get explainable scores, missing keywords, and
            bullet-level rewrites — not a black-box chatbot dump.
          </p>
          <div className="cta-row">
            <Link className="btn btn-primary" href="/review">
              Start a review
            </Link>
            <Link className="btn btn-secondary" href="/review?demo=1">
              Try Daniel&apos;s demo
            </Link>
          </div>
        </div>
        <div className="hero-visual" aria-hidden="true" />
      </main>
      <SiteFooter />
    </>
  );
}
