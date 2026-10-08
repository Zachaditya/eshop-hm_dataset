/** Storefront asset configuration and same-origin backend proxy destinations. */
import type { NextConfig } from "next";

/**
 * Resolve the upstream API without using a relative public proxy path recursively.
 * Params: None.
 * @returns The configured HTTP API URL, local development URL, or production API URL.
 */
function backendOrigin(): string {
  const configured = process.env.API_BASE_URL?.trim() || process.env.NEXT_PUBLIC_API_BASE?.trim() || "";
  if (/^https?:\/\//.test(configured)) {
    return new URL(configured).toString().replace(/\/+$/, "");
  }
  return process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:8000"
    : "https://eshop-hmdataset-production.up.railway.app";
}

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

  /**
   * Proxy cookie-based browser requests through the storefront's own host.
   * Params: None.
   * @returns The backend rewrite used for authentication, carts, and order history.
   */
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${backendOrigin()}/:path*`,
      },
    ];
  },
};

export default nextConfig;
