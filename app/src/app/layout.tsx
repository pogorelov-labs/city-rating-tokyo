import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Script from 'next/script';
import VisitorIdentify from '@/components/VisitorIdentify';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'Tokyo Neighborhood Explorer - Find Your Perfect Area',
  description:
    'Interactive map of Tokyo neighborhoods rated by food, nightlife, transport, rent, safety, parks, and more. Find the best area to live in Greater Tokyo.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full`}>
      <body className="h-full font-sans antialiased">
        {children}
        {process.env.NEXT_PUBLIC_UMAMI_URL && process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID && (
          <Script
            src={`${process.env.NEXT_PUBLIC_UMAMI_URL}/script.js`}
            data-website-id={process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID}
            strategy="afterInteractive"
          />
        )}
        <VisitorIdentify />
      </body>
    </html>
  );
}
