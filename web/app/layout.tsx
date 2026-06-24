import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Inter } from "next/font/google";
import type { ReactNode } from "react";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

const DESCRIPTION =
  "A model-agnostic, post-hoc leakage & robustness auditor for sequence-based biological predictors. See how much reported performance survives once train/test homology is removed.";

export const metadata: Metadata = {
  metadataBase: new URL("https://veritas-viewer.vercel.app"),
  title: "Veritas — leakage & robustness auditor",
  description: DESCRIPTION,
  applicationName: "Veritas",
  openGraph: {
    type: "website",
    siteName: "Veritas",
    title: "Veritas — leakage & robustness auditor",
    description: DESCRIPTION,
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "Veritas — leakage & robustness auditor",
    description: DESCRIPTION,
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0c0f",
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${plexMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
