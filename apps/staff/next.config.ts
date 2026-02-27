import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@municipal/ui"],
  async rewrites() {
    return [
      {
        source: "/backend-api/:path*",
        destination: "http://localhost:8080/api/:path*",
      },
    ];
  },
};

export default nextConfig;
