import React from 'react';
import Link from 'next/link';
import { Sparkles, ShieldCheck, CheckCircle2 } from 'lucide-react';

/** Two-pane shell for the login / signup screens. */
export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-violet-600 to-blue-600 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -right-16 -top-16 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 -left-10 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <Link href="/" className="relative flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/15">
            <Sparkles size={18} />
          </span>
          <span className="text-xl font-extrabold tracking-tight">DataVerse AI</span>
        </Link>

        <div className="relative max-w-md">
          <h2 className="text-3xl font-extrabold leading-tight">
            Spreadsheets in. Executive reports out.
          </h2>
          <ul className="mt-8 space-y-4 text-white/90">
            <li className="flex items-start gap-3">
              <CheckCircle2 size={20} className="mt-0.5 shrink-0" />
              <span>Deterministic metrics, EDA, and predictions. The LLM never invents numbers.</span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 size={20} className="mt-0.5 shrink-0" />
              <span>Explainable AI with SHAP feature importance in every report.</span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 size={20} className="mt-0.5 shrink-0" />
              <span>Compact 1–2 page reports with no repeated content.</span>
            </li>
          </ul>
        </div>

        <p className="relative flex items-center gap-2 text-sm text-white/70">
          <ShieldCheck size={16} /> Secure accounts powered by Supabase Auth.
        </p>
      </div>

      {/* Form panel */}
      <div className="flex flex-col items-center justify-center px-5 py-12 sm:px-8">
        <div className="w-full max-w-sm">
          <Link href="/" className="mb-8 flex items-center gap-2 lg:hidden">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-violet-500 to-blue-500">
              <Sparkles size={16} className="text-white" />
            </span>
            <span className="bg-gradient-to-r from-violet-600 to-blue-600 bg-clip-text text-lg font-extrabold text-transparent">
              DataVerse AI
            </span>
          </Link>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="mt-1.5 text-sm text-[#64748B]">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  );
}
