import type { Metadata } from 'next'
import { Hanken_Grotesk, Inter, Inter_Tight } from 'next/font/google'
import Script from 'next/script'
import './globals.css'

const hanken = Hanken_Grotesk({
  subsets: ['latin'],
  variable: '--font-hanken',
  weight: ['400', '500', '600', '700', '800', '900'],
})

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  weight: ['400', '500', '600', '700'],
})

const interTight = Inter_Tight({
  subsets: ['latin'],
  variable: '--font-inter-tight',
  weight: ['400', '500', '600', '700', '800'],
})

export const metadata: Metadata = {
  title: 'SagePontus — AI Red Flag Screening for Physical Therapists',
  description:
    'SagePontus catches the red flags PTAs miss before they become your malpractice lawsuit. Chrome extension for any browser-based EMR.',
  icons: {
    icon: `${process.env.NEXT_PUBLIC_ASSET_BASE ?? ''}/favicon.png`,
    apple: `${process.env.NEXT_PUBLIC_ASSET_BASE ?? ''}/apple-icon.png`,
  },
}

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: 'SagePontus',
  applicationCategory: 'HealthApplication',
  operatingSystem: 'All',
  browserRequirements: 'Requires Google Chrome',
  description:
    "Real-time compliance and red flag screening software for physical therapy clinics, built on Goodman's 6 criteria.",
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'USD',
    description: 'Free during private beta',
  },
  creator: {
    '@type': 'Organization',
    name: 'SagePontus',
    url: 'https://sagepontus.com',
    email: 'contact@sagepontus.com',
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'customer support',
      email: 'contact@sagepontus.com',
    },
    address: {
      '@type': 'PostalAddress',
      streetAddress: 'Startup Venture Campus, 100 Middlefield Rd.',
      addressLocality: 'Menlo Park',
      addressRegion: 'CA',
      postalCode: '94025',
      addressCountry: 'US',
    },
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${hanken.variable} ${inter.variable} ${interTight.variable}`} suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="font-hanken antialiased">
        {children}
        {process.env.NODE_ENV === 'production' && process.env.NEXT_PUBLIC_LINKEDIN_PARTNER_ID && (
          <Script id="linkedin-insight" strategy="afterInteractive">{`
            _linkedin_partner_id = "${process.env.NEXT_PUBLIC_LINKEDIN_PARTNER_ID}";
            window._linkedin_data_partner_ids = window._linkedin_data_partner_ids || [];
            window._linkedin_data_partner_ids.push(_linkedin_partner_id);
            (function(l) {
              if (!l) { window.lintrk = function(a,b) { window.lintrk.q.push([a,b]) }; window.lintrk.q = [] }
              var s = document.getElementsByTagName("script")[0];
              var b = document.createElement("script");
              b.type = "text/javascript"; b.async = true;
              b.src = "https://snap.licdn.com/li.lms-analytics/insight.min.js";
              s.parentNode.insertBefore(b, s);
            })(window.lintrk);
          `}</Script>
        )}
      </body>
    </html>
  )
}
