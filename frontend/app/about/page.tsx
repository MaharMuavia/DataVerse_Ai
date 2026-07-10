import Link from 'next/link';
import type { Metadata } from 'next';
import { Target, Layers, ShieldCheck, Cpu, ArrowRight, Workflow } from 'lucide-react';
import { MarketingShell } from '@/components/site/MarketingShell';

export const metadata: Metadata = {
  title: 'About — DataVerse AI',
  description: 'How the two-agent dataset analyst works and the principles behind it.',
};

const PRINCIPLES = [
  {
    icon: ShieldCheck,
    title: 'Deterministic-first',
    body: 'Any number a user sees is computed with Pandas or scikit-learn. The LLM is optional and only polishes narration — it can never fabricate a metric.',
  },
  {
    icon: Layers,
    title: 'Exactly two agents',
    body: 'A DatasetAgent owns ingestion and integrity; an AnalystAgent owns analysis and explanation. No sprawling swarm, no hidden state.',
  },
  {
    icon: Target,
    title: 'Concise by design',
    body: 'Reports stay 1–2 pages: at most two charts, three recommendations, and a hard rule that no fact is ever repeated twice.',
  },
  {
    icon: Cpu,
    title: 'Runs anywhere',
    body: 'No database, Supabase, or API keys required. With nothing configured it falls back to local storage and offline Mock mode.',
  },
];

const PIPELINE = [
  ['Upload & validate', 'Secure file handling, CSV/XLSX parsing, header normalisation.'],
  ['Profile & quality', 'Type inference, semantic mapping, missing/duplicate/outlier scan.'],
  ['Metrics & EDA', 'Business metrics, trends, correlations — all deterministic.'],
  ['Predict & explain', 'Optional model + SHAP, gated on enough rows; skipped with a reason otherwise.'],
  ['Compose & render', 'De-duplicated sections assembled into a compact HTML/PDF report.'],
];

const STACK = [
  ['Backend', 'FastAPI · Pandas · scikit-learn · SHAP · ReportLab'],
  ['Frontend', 'Next.js 15 · React 19 · Tailwind v4'],
  ['Persistence', 'Local filesystem by default · optional Supabase'],
  ['LLM', 'Optional narration polish only · offline Mock mode'],
];

export default function AboutPage() {
  return (
    <MarketingShell>
      <section className="mx-auto max-w-4xl px-5 pt-20 pb-12 text-center sm:px-6">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          A dataset analyst you can{' '}
          <span className="bg-gradient-to-r from-violet-500 to-blue-500 bg-clip-text text-transparent">trust</span>.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-[#475569]">
          DataVerse AI was built around a simple idea: an AI data analyst is only useful
          if its numbers are correct. So every figure is computed deterministically, and
          the language model is kept on a short leash — it explains results, it never
          generates them.
        </p>
      </section>

      {/* Principles */}
      <section className="mx-auto max-w-6xl px-5 pb-16 sm:px-6">
        <div className="grid gap-5 sm:grid-cols-2">
          {PRINCIPLES.map((p) => (
            <div key={p.title} className="rounded-2xl border border-[#E2E8F0] bg-white p-7 shadow-sm">
              <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 text-white">
                <p.icon size={20} />
              </div>
              <h3 className="mt-4 text-lg font-bold">{p.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[#64748B]">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pipeline */}
      <section className="bg-white">
        <div className="mx-auto max-w-4xl px-5 py-16 sm:px-6">
          <div className="mb-10 flex items-center justify-center gap-2 text-center">
            <Workflow size={20} className="text-violet-500" />
            <h2 className="text-3xl font-bold tracking-tight">How a request flows</h2>
          </div>
          <ol className="relative space-y-6 border-l-2 border-[#E2E8F0] pl-8">
            {PIPELINE.map(([title, body], i) => (
              <li key={title} className="relative">
                <span className="absolute -left-[41px] grid h-7 w-7 place-items-center rounded-full bg-gradient-to-br from-violet-500 to-blue-500 text-xs font-bold text-white">
                  {i + 1}
                </span>
                <h3 className="text-base font-semibold text-[#0F172A]">{title}</h3>
                <p className="mt-1 text-sm text-[#64748B]">{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Stack */}
      <section className="mx-auto max-w-5xl px-5 py-16 sm:px-6">
        <h2 className="mb-8 text-center text-3xl font-bold tracking-tight">Built with</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {STACK.map(([title, body]) => (
            <div key={title} className="rounded-2xl border border-[#E2E8F0] bg-white p-6">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-600">{title}</h3>
              <p className="mt-2 text-sm font-medium text-[#334155]">{body}</p>
            </div>
          ))}
        </div>

        <div className="mt-12 text-center">
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-violet-500 to-blue-500 px-7 py-3.5 text-base font-bold text-white shadow-lg shadow-violet-500/25 transition-all hover:brightness-110 active:scale-95"
          >
            Get started <ArrowRight size={18} />
          </Link>
        </div>
      </section>
    </MarketingShell>
  );
}
