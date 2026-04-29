/** @type {import('next').NextConfig} */
const BACKEND = process.env.NEXT_PUBLIC_RP_BACKEND_URL || "http://localhost:3725";

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
