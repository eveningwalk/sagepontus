import type { Metadata } from 'next'
import { Hanken_Grotesk } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const hanken = Hanken_Grotesk({
  subsets: ['latin'],
  variable: '--font-hanken',
  weight: ['400', '500', '600', '700', '800', '900'],
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={hanken.variable} suppressHydrationWarning>
      <body className="font-hanken antialiased">
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
