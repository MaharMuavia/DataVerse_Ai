import Link from 'next/link';
import {
  ArrowRight, Database, BrainCircuit, ShieldCheck, FileText,
  UploadCloud, Sparkles, BarChart3, CheckCircle2,
  ReceiptText, ScrollText, BadgeCheck, SlidersHorizontal, Stethoscope, FileCheck2,
} from 'lucide-react';
import { MarketingShell } from '@/components/site/MarketingShell';

const STATS = [
  { value: '100%', label: 'Deterministic metrics' },
  { value: 'SHA-256', label: 'Reproducibility certificate' },
  { value: '2', label: 'Page executive report' },
  { value: '0', label: 'Numbers invented by the LLM' },
];

const STEPS = [
  {
    icon: UploadCloud,
    title: 'Upload & ask',
    body: 'Drop in a CSV or Excel file and ask questions in plain English — total sales, hot products, sales by region, trends, predictions.',
  },
  {
    icon: BarChart3,
    title: 'Analyse',
    body: 'Two specialised agents profile the data, compute KPIs, EDA and trends deterministically, train an optional model, and explain it with SHAP.',
  },
  {
    icon: BadgeCheck,
    title: 'Verify & report',
    body: 'Every number carries a receipt and a cryptographic certificate. Export a 2-page executive report where each figure can be independently re-verified.',
  },
];

const TRUST_STACK = [
  {
    icon: ReceiptText,
    title: 'Show-the-math receipts',
    body: 'Click any KPI to see its exact formula, source columns, row count, and the real rows behind it.',
    unique: false,
  },
  {
    icon: ScrollText,
    title: 'Full audit trail',
    body: 'Receipts for every statistic, correlation, trend, and model metric — downloadable as one JSON log.',
    unique: false,
  },
  {
    icon: BadgeCheck,
    title: 'Reproducibility certificate',
    body: 'SHA-256 fingerprints of your data and results. One click re-runs the pipeline and proves every number reproduces exactly.',
    unique: true,
  },
  {
    icon: SlidersHorizontal,
    title: 'Verified what-if',
    body: 'Nudge a lever like “+10% price” and watch KPIs recompute deterministically — each hypothetical keeps its own receipt.',
    unique: true,
  },
  {
    icon: Stethoscope,
    title: 'Data Quality Doctor',
    body: 'Detects duplicates, missing values, and type issues — then applies one-click deterministic fixes with a before/after diff.',
    unique: false,
  },
  {
    icon: FileCheck2,
    title: 'Verified report export',
    body: 'A self-contained report where every KPI embeds its receipt and the certificate travels with the file.',
    unique: false,
  },
];

export default function HomePage() {
  return (
    <MarketingShell>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute -top-24 left-1/4 h-96 w-96 rounded-full bg-violet-500/15 blur-[120px]" />
        <div className="pointer-events-none absolute top-10 right-1/4 h-96 w-96 rounded-full bg-blue-500/15 blur-[120px]" />

        <div className="relative mx-auto max-w-5xl px-5 pb-20 pt-20 text-center sm:px-6 sm:pt-28">
          <span className="inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-3.5 py-1 text-xs font-semibold uppercase tracking-wide text-violet-600">
            <Sparkles size={13} /> The Verifiable AI Data Analyst
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-extrabold leading-tight tracking-tight sm:text-6xl">
            The AI analyst that{' '}
            <span className="bg-gradient-to-r from-violet-500 to-blue-500 bg-clip-text text-transparent">
              proves its numbers
            </span>
            , not just states them.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-[#475569]">
            Chat with any CSV or Excel file — total sales, top products, sales by region,
            predictions with explainable AI. Every answer is computed deterministically,
            carries a click-to-verify receipt, and is sealed with a cryptographic
            reproducibility certificate. LLM analysts can hallucinate; DataVerse can’t.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/signup"
              className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-violet-500 to-blue-500 px-7 py-3.5 text-base font-bold text-white shadow-xl shadow-violet-500/25 transition-all hover:brightness-110 active:scale-95"
            >
              Get started free <ArrowRight size={19} />
            </Link>
            <Link
              href="/features"
              className="flex items-center gap-2 rounded-2xl border border-[#E2E8F0] bg-white px-7 py-3.5 text-base font-semibold text-[#334155] transition-all hover:bg-[#F1F5F9]"
            >
              See how it works
            </Link>
          </div>
          <p className="mt-4 text-xs text-[#94A3B8]">No credit card. Continue as guest from the login page.</p>

          {/* Stats */}
          <div className="mx-auto mt-16 grid max-w-3xl grid-cols-2 gap-4 sm:grid-cols-4">
            {STATS.map((stat) => (
              <div key={stat.label} className="rounded-2xl border border-[#E2E8F0] bg-white/70 p-5 backdrop-blur">
                <div className="bg-gradient-to-r from-violet-600 to-blue-600 bg-clip-text text-3xl font-extrabold text-transparent">
                  {stat.value}
                </div>
                <div className="mt-1 text-xs font-medium text-[#64748B]">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-6xl px-5 py-16 sm:px-6">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight">From file to report in three steps</h2>
          <p className="mt-3 text-[#64748B]">A clean division of duties keeps results fast, reliable, and reproducible.</p>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <div key={step.title} className="relative rounded-2xl border border-[#E2E8F0] bg-white p-7 shadow-sm">
              <span className="absolute right-6 top-6 text-5xl font-black text-[#F1F5F9]">{i + 1}</span>
              <div className="grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 text-white shadow-sm">
                <step.icon size={22} />
              </div>
              <h3 className="mt-5 text-lg font-bold">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[#64748B]">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Trust stack */}
      <section className="mx-auto max-w-6xl px-5 py-16 sm:px-6">
        <div className="mb-12 text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3.5 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-600">
            <ShieldCheck size={13} /> The Trust Stack
          </span>
          <h2 className="mt-4 text-3xl font-bold tracking-tight">Six layers of proof no other analyst offers</h2>
          <p className="mt-3 text-[#64748B]">
            ChatGPT and Julius give you numbers you have to trust. DataVerse gives you numbers you can check.
          </p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {TRUST_STACK.map((feature) => (
            <div key={feature.title} className="relative rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
              {feature.unique && (
                <span className="absolute right-4 top-4 rounded-full bg-emerald-500 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                  ★ Unique
                </span>
              )}
              <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 text-white shadow-sm">
                <feature.icon size={20} />
              </div>
              <h3 className="mt-4 text-base font-bold">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[#64748B]">{feature.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Two-agent highlight */}
      <section className="bg-white">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:px-6">
          <div className="mb-12 text-center">
            <h2 className="text-3xl font-bold tracking-tight">Powered by exactly two agents</h2>
            <p className="mt-3 text-[#64748B]">No sprawling agent swarm — just clear ownership and deterministic computation.</p>
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-2xl border border-violet-100 bg-violet-50/40 p-7">
              <div className="flex items-center gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-xl border border-violet-100 bg-white text-violet-500">
                  <Database size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold">DatasetAgent</h3>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-violet-600">Data core</span>
                </div>
              </div>
              <ul className="mt-5 space-y-2.5 text-sm text-[#475569]">
                <li className="flex items-center gap-2"><CheckCircle2 size={15} className="text-violet-500" /> Secure upload &amp; CSV/XLSX parsing</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={15} className="text-violet-500" /> Header normalisation &amp; type profiling</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={15} className="text-violet-500" /> Quality scan: missing values &amp; duplicates</li>
              </ul>
            </div>
            <div className="rounded-2xl border border-blue-100 bg-blue-50/40 p-7">
              <div className="flex items-center gap-3">
                <div className="grid h-11 w-11 place-items-center rounded-xl border border-blue-100 bg-white text-blue-500">
                  <BrainCircuit size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-bold">AnalystAgent</h3>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Analytics &amp; XAI</span>
                </div>
              </div>
              <ul className="mt-5 space-y-2.5 text-sm text-[#475569]">
                <li className="flex items-center gap-2"><CheckCircle2 size={15} className="text-blue-500" /> Semantic KPI mapping &amp; EDA</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={15} className="text-blue-500" /> Optional prediction &amp; model evaluation</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={15} className="text-blue-500" /> SHAP-grounded explainable AI</li>
              </ul>
            </div>
          </div>

          <div className="mt-10 flex items-center justify-center gap-3 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] px-6 py-5 text-center">
            <ShieldCheck size={20} className="shrink-0 text-emerald-500" />
            <p className="text-sm text-[#475569]">
              <span className="font-semibold text-[#0F172A]">Deterministic-first guarantee:</span> every metric you see is
              computed in Pandas / scikit-learn. The LLM only polishes narration — it can never invent a number.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-5xl px-5 py-20 sm:px-6">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-violet-600 to-blue-600 px-8 py-14 text-center text-white shadow-2xl">
          <div className="pointer-events-none absolute -right-10 -top-10 h-48 w-48 rounded-full bg-white/10 blur-2xl" />
          <h2 className="text-3xl font-extrabold tracking-tight">Ready to analyse your data?</h2>
          <p className="mx-auto mt-3 max-w-xl text-white/80">
            Spin up the workspace, upload a dataset, and download a polished report in minutes.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/signup"
              className="rounded-2xl bg-white px-7 py-3.5 text-base font-bold text-violet-700 shadow-lg transition-all hover:bg-violet-50 active:scale-95"
            >
              Create your workspace
            </Link>
            <Link
              href="/login"
              className="rounded-2xl border border-white/40 px-7 py-3.5 text-base font-semibold text-white transition-all hover:bg-white/10"
            >
              Continue as guest
            </Link>
          </div>
        </div>
      </section>
    </MarketingShell>
  );
}
