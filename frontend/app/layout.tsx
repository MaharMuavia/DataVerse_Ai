import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth';

export const metadata: Metadata = {
  title: 'DataVerse AI — Two-Agent Dataset Analyst',
  description:
    'Upload a CSV or Excel file and get a compact, deterministic business report with metrics, EDA, predictions, and explainable AI.',
  icons: {
    icon: '/icon.svg',
    shortcut: '/icon.svg',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="light">
      <body className="font-sans antialiased bg-[#F8FAFC] text-[#0F172A] selection:bg-[#2563EB]/20" suppressHydrationWarning>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
