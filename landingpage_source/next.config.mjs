/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    const djangoUrl = process.env.DJANGO_API_URL || 'http://localhost:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${djangoUrl}/accounts/api/:path*`,
      },
    ]
  },
}

export default nextConfig
