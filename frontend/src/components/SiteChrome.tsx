import Link from "next/link";

const DISCLAIMER =
  "This analysis is AI-generated guidance and does not guarantee interviews, employment, or acceptance by applicant tracking systems.";

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link href="/" className="brand">
        Resume<span>Signal</span>
      </Link>
      <nav>
        <Link href="/review">Review</Link>
        <Link href="/history">History</Link>
      </nav>
    </header>
  );
}

export function SiteFooter({ disclaimer = DISCLAIMER }: { disclaimer?: string }) {
  return (
    <footer className="site-footer">
      <p>{disclaimer}</p>
    </footer>
  );
}
