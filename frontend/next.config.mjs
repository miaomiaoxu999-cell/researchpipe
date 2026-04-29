/** @type {import('next').NextConfig} */
// Server-side rewrite target — always the internal backend on the same host.
// Distinct from NEXT_PUBLIC_RP_BACKEND_URL (which is the public URL the browser sees).
const BACKEND = process.env.RP_BACKEND_INTERNAL_URL || "http://127.0.0.1:3725";

const nextConfig = {
  // Skip ESLint during builds — dev / lint commands still run it.
  // (Project has pre-existing soft errors that don't affect runtime.)
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    return [
      { source: "/downloads/:path*", destination: `${BACKEND}/downloads/:path*` },
      // Production: same-domain API access (frontend proxies /v1/* to backend).
      // Avoids needing a separate api.rp.zgen.xin subdomain or CORS for the agent UI.
      { source: "/v1/:path*", destination: `${BACKEND}/v1/:path*` },
      { source: "/healthz", destination: `${BACKEND}/healthz` },
      { source: "/openapi.json", destination: `${BACKEND}/openapi.json` },
    ];
  },
};

export default nextConfig;
