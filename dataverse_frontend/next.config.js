/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    swcMinify: false,
    forceSwcTransforms: false,
  },
  swcMinify: false,
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8001/:path*',
      },
    ]
  },
}

module.exports = nextConfig
