// `next dev` needs eval for React Fast Refresh; without it the dev site never hydrates.
// Production keeps the strict policy.
const scriptSrc =
  process.env.NODE_ENV === "development" ? "'self' 'unsafe-inline' 'unsafe-eval'" : "'self' 'unsafe-inline'";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // pin the trace root to web/ (multiple lockfiles exist on this machine).
  outputFileTracingRoot: import.meta.dirname,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          {
            key: "Content-Security-Policy",
            value: `default-src 'self'; script-src ${scriptSrc}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`,
          },
        ],
      },
    ];
  },
};

export default nextConfig;
