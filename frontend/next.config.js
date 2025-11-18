/** @type {import('next').NextConfig} */
const disableLint = process.env.NEXT_IGNORE_LINT === '1';
const disableTsc  = process.env.NEXT_IGNORE_TSC  === '1';

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  eslint:     { ignoreDuringBuilds: disableLint },
  typescript: { ignoreBuildErrors:  disableTsc  },
  experimental: {
    outputFileTracingIncludes: {
      '/': ['./node_modules/react-force-graph-3d/**/*'],
    },
  },
  swcMinify: true,
};

module.exports = nextConfig;
