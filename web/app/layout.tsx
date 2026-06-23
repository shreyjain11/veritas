import type { ReactNode } from "react";

export const metadata = {
  title: "Veritas",
  description: "A model-agnostic, post-hoc leakage & robustness auditor for sequence models.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
