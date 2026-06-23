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
};

export default nextConfig;
