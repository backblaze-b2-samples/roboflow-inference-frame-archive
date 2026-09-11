import type { NextConfig } from "next";

// Allow `next/image` to optimize remote previews coming from Backblaze B2.
// Presigned download URLs use the bucket-specific S3 hostname pattern:
//   <bucket>.s3.<region>.backblazeb2.com    (path-style and virtual-host)
//   s3.<region>.backblazeb2.com             (path-style)
// One wildcard covers every region + bucket, so this config drops in
// without per-deployment tweaks.
const nextConfig: NextConfig = {
  transpilePackages: ["@roboflow-inference-frame-archive/shared"],
  // Next.js 16's dev-server cross-origin protection 403s asset requests
  // (e.g. /_next/static/chunks/*) whose Origin isn't localhost. The app's
  // own Playwright verify config defaults baseURL to 127.0.0.1, which is a
  // *different* origin than localhost as far as this check is concerned —
  // without this, shadcn Select dropdowns silently fail to open there.
  allowedDevOrigins: ["localhost", "127.0.0.1"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.backblazeb2.com",
      },
    ],
  },
};

export default nextConfig;
