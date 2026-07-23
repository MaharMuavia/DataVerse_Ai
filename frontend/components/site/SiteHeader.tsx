'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import { Sparkles, Menu, X, LayoutDashboard, LogOut } from 'lucide-react';
import { useAuth } from '@/lib/auth';

const NAV_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/features', label: 'Features' },
  { href: '/about', label: 'About' },
];

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { session, signOut } = useAuth();
  const [open, setOpen] = useState(false);

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#E2E8F0]/70 bg-white/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 shadow-sm">
            <Sparkles size={17} className="text-white" />
          </span>
          <span className="bg-gradient-to-r from-violet-600 to-blue-600 bg-clip-text text-lg font-extrabold tracking-tight text-transparent">
            DataVerse AI
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-colors ${
                isActive(link.href)
                  ? 'text-violet-600'
                  : 'text-[#475569] hover:text-[#0F172A]'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          {session ? (
            <>
              <Link
                href="/dashboard"
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:brightness-110 active:scale-95"
              >
                <LayoutDashboard size={15} /> Dashboard
              </Link>
              <button
                onClick={() => {
                  signOut();
                  router.push('/');
                }}
                className="flex items-center gap-1.5 rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm font-medium text-[#475569] transition-colors hover:bg-[#F1F5F9]"
                title={session.email ?? ''}
              >
                <LogOut size={15} /> Sign out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-xl px-4 py-2 text-sm font-medium text-[#475569] transition-colors hover:text-[#0F172A]"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:brightness-110 active:scale-95"
              >
                Get started
              </Link>
            </>
          )}
        </div>

        <button
          className="rounded-lg p-2 text-[#475569] md:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {open && (
        <div className="border-t border-[#E2E8F0]/70 bg-white px-5 py-3 md:hidden">
          <nav className="flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className={`rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive(link.href) ? 'bg-violet-50 text-violet-600' : 'text-[#475569]'
                }`}
              >
                {link.label}
              </Link>
            ))}
            <div className="mt-2 flex gap-2">
              {session ? (
                <Link
                  href="/dashboard"
                  onClick={() => setOpen(false)}
                  className="flex-1 rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 px-4 py-2 text-center text-sm font-semibold text-white"
                >
                  Dashboard
                </Link>
              ) : (
                <>
                  <Link
                    href="/login"
                    onClick={() => setOpen(false)}
                    className="flex-1 rounded-xl border border-[#E2E8F0] px-4 py-2 text-center text-sm font-medium text-[#475569]"
                  >
                    Log in
                  </Link>
                  <Link
                    href="/signup"
                    onClick={() => setOpen(false)}
                    className="flex-1 rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 px-4 py-2 text-center text-sm font-semibold text-white"
                  >
                    Get started
                  </Link>
                </>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
