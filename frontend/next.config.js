/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  experimental: {
    outputFileTracingIncludes: {
      '/': ['./node_modules/react-force-graph-3d/**/*'],
    },
  },
}

module.exports = nextConfig

