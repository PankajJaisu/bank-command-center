import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Expose environment variables to the client at runtime.
  // This setup ensures that the variable is available both during build and in the browser.
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api",
    NEXT_PUBLIC_API_TIMEOUT: process.env.NEXT_PUBLIC_API_TIMEOUT,
    NEXT_PUBLIC_ENABLE_DEBUG: process.env.NEXT_PUBLIC_ENABLE_DEBUG,
  },

  webpack: (config, { isServer }) => {
    // This part is for PDF viewer compatibility and is correct.
    if (!isServer) {
      config.resolve = config.resolve || {};
      config.resolve.fallback = config.resolve.fallback || {};
      config.resolve.fallback.canvas = false;
      config.resolve.fallback.encoding = false;
    }
    return config;
  },

  // Configure for Docker deployment
  output: 'standalone',
};

export default nextConfig;
