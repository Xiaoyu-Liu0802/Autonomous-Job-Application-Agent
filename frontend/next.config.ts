import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the project root so Next doesn't infer it from a stray
  // package-lock.json in a parent directory.
  turbopack: { root: __dirname },
};

export default nextConfig;
