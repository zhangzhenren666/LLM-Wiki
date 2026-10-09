/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@wiki/ui', '@wiki/types', '@wiki/config'],
  // ESLint 统一在 Monorepo 根目录通过 `pnpm lint` 执行
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
