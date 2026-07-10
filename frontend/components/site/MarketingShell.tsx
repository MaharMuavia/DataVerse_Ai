import React from 'react';
import { SiteHeader } from './SiteHeader';
import { SiteFooter } from './SiteFooter';

/** Page chrome shared by the public marketing pages (Home, Features, About). */
export function MarketingShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-[#F8FAFC] text-[#0F172A]">
      <SiteHeader />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  );
}
