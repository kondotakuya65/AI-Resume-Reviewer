import { Suspense } from "react";
import ReviewClient from "./ReviewClient";

export default function Page() {
  return (
    <Suspense fallback={<main className="page"><p>Loading…</p></main>}>
      <ReviewClient />
    </Suspense>
  );
}
