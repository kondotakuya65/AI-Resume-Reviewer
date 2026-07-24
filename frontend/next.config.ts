import type { NextConfig } from "next";

const apiProxyTarget = process.env.API_PROXY_TARGET || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  // Allow long-running proxied API calls (analysis / Ollama). Next default is ~30s.
  experimental: {
    proxyTimeout: 600_000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
