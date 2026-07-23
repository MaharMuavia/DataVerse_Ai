import Link from 'next/link';
import { Sparkles } from 'lucide-react';

export function SiteFooter() {
  return (
    <footer className="border-t border-[#E2E8F0]/70 bg-white">
      <div className="mx-auto max-w-7xl px-5 py-12 sm:px-6">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <div className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-violet-500 to-blue-500">
                <Sparkles size={16} className="text-white" />
              </span>
              <span className="bg-gradient-to-r from-violet-600 to-blue-600 bg-clip-text text-lg font-extrabold text-transparent">
                DataVerse AI
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-[#64748B]">
              A two-agent dataset analyst. Upload a spreadsheet and get a compact,
              deterministic business report with metrics, EDA, predictions, and
              explainable AI, without the numbers ever being invented.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-10 sm:grid-cols-3">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Product</h4>
              <ul className="mt-3 space-y-2 text-sm text-[#475569]">
                <li><Link href="/features" className="hover:text-violet-600">Features</Link></li>
                <li><Link href="/about" className="hover:text-violet-600">About</Link></li>
                <li><Link href="/dashboard" className="hover:text-violet-600">Dashboard</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Account</h4>
              <ul className="mt-3 space-y-2 text-sm text-[#475569]">
                <li><Link href="/login" className="hover:text-violet-600">Log in</Link></li>
                <li><Link href="/signup" className="hover:text-violet-600">Sign up</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8]">Built with</h4>
              <ul className="mt-3 space-y-2 text-sm text-[#475569]">
                <li>FastAPI + Pandas</li>
                <li>scikit-learn + SHAP</li>
                <li>Next.js + Tailwind</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-10 border-t border-[#E2E8F0]/70 pt-6 text-center text-xs text-[#94A3B8]">
          &copy; {new Date().getFullYear()} DataVerse AI · Two-Agent Dataset Analyst. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
