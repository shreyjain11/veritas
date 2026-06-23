/**
 * Static export: Veritas has no backend (bio binaries can't run in-browser; the viewer
 * only renders AuditReport JSON). `output: "export"` emits a fully static site to out/,
 * which Vercel serves directly. Deploy with Root Directory = web.
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  output: "export",
  reactStrictMode: true,
  images: { unoptimized: true },
  // pin the trace root to web/ (multiple lockfiles exist on this machine).
  outputFileTracingRoot: import.meta.dirname,
};

export default nextConfig;
