/** @type {import('next').NextConfig} */
const BACKEND = process.env.NEXT_PUBLIC_RP_BACKEND_URL || "http://localhost:3725";

const nextConfig = {
  // Skip ESLint during builds — dev / lint commands still run it.
  // (Project has pre-existing soft errors that don't affect runtime.)
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    return [
      { source: "/downloads/:path*", destination: `${BACKEND}/downloads/:path*` },
    ];
  },
};

export default nextConfig;
