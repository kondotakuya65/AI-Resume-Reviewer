import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResumeSignal — AI Resume Reviewer",
  description:
    "Upload a resume, paste a job description, and get explainable scores, ATS guidance, and rewrite suggestions.",
  icons: {
    icon: [{ url: "/fav.png", type: "image/png" }],
    shortcut: "/fav.png",
    apple: "/fav.png",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
