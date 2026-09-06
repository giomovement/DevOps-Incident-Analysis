import type { NextConfig } from 'next';

const apiOrigin = process.env.API_ORIGIN?.replace(/\/+$/, '');

const nextConfig: NextConfig = {
  async rewrites() {
    if (!apiOrigin) return [];
    return [
      { source: '/api/v1/:path*', destination: `${apiOrigin}/api/v1/:path*` },
      { source: '/health', destination: `${apiOrigin}/health` },
    ];
  },
};

export default nextConfig;
