import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SignalGraph",
  description: "Credibility-adjusted traction for open-source investing",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header style={{ borderBottom: "1px solid var(--border)", background: "var(--panel)" }}>
          <div style={{ maxWidth: 1100, margin: "0 auto", padding: "16px 20px", display: "flex", gap: 16, alignItems: "baseline" }}>
            <a href="/" style={{ fontWeight: 800, letterSpacing: "-0.02em" }}>
              SignalGraph
            </a>
            <span className="muted" style={{ fontSize: 13 }}>
              Credibility-adjusted traction
            </span>
          </div>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
