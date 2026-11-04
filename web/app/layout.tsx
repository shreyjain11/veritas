import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Inter, Source_Serif_4 } from "next/font/google";
import type { ReactNode } from "react";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const serif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

const DESCRIPTION =
  "Check whether frontier models are benchmark maxxing. Veritas audits score robustness, protocol dependence, exposure-consistent signals, controls, uncertainty, and provenance.";

export const metadata: Metadata = {
  metadataBase: new URL("https://veritas.jainshrey.com"),
  title: "Veritas — frontier-model benchmark integrity auditor",
  description: DESCRIPTION,
  applicationName: "Veritas",
  openGraph: {
    type: "website",
    siteName: "Veritas",
    title: "Veritas — frontier-model benchmark integrity auditor",
    description: DESCRIPTION,
    url: "/",
  },
  twitter: {
    card: "summary_large_image",
    title: "Veritas — frontier-model benchmark integrity auditor",
    description: DESCRIPTION,
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf9f6" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0c0f" },
  ],
  colorScheme: "light dark",
};

// Runs before first paint so a saved light/dark choice never flashes the other theme.
const THEME_SCRIPT = `try{var t=localStorage.getItem("veritas-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${serif.variable} ${plexMono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
