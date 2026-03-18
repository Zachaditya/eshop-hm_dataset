import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      // local dev images
      {
        protocol: "http",
        hostname: "127.0.0.1",
        port: "8000",
        pathname: "/images/**",
      },
      // production images from Railway backend
      {
        protocol: "https",
        hostname: "eshop-hmdataset-production.up.railway.app",
        pathname: "/images/**",
      },
      // product images from S3
      {
        protocol: "https",
        hostname: "zachadityaecom.s3.us-east-2.amazonaws.com",
        pathname: "/images/**",
      },
    ],
  },

  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: "https://eshop-hmdataset-production.up.railway.app/:path*",
      },
    ];
  },
};

export default nextConfig;
