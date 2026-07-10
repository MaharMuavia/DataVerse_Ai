import Link from 'next/link';
import type { Metadata } from 'next';
import {
  Database, BrainCircuit, FileText, ShieldCheck, TrendingUp, Sparkles,
  Table, AlertTriangle, GitCompare, Gauge, ArrowRight, LineChart,
} from 'lucide-react';
import { MarketingShell } from '@/components/site/MarketingShell';

export const metadata: Metadata = {
  title: 'Features — DataVerse AI',
  description: 'Deterministic metrics, EDA, predictions, explainable AI, and compact reports.',
};

const CAPABILITIES = [
  {
    icon: Database,
    title: 'Automatic profiling',
    body: 'Row/column counts, dtype inference, semantic column mapping, and a per-column quality profile the moment you upload.',
  },
  {
    icon: AlertTriangle,
    title: 'Data quality scan',
    body: 'Missing-value severity, duplicate detection, constant and high-cardinality columns, and IQR-based outlier flags.',
  },
  {
    icon: TrendingUp,
    title: 'Business metrics & EDA',
    body: 'Revenue, margins, top categories/products, trends, and seasonality — all computed deterministically in Pandas.',
  },
  {
    icon: LineChart,
    title: 'Trends & correlations',
    body: 'Period-over-period movement, volatility, anomaly points, and a Pearson correlation matrix with strong-pair detection.',
  },
  {
    icon: Gauge,
    title: 'Prediction & model evaluation',
    body: 'An optional Ridge / RandomForest model with a real held-out evaluation — R², RMSE, MAE, or accuracy and F1.',
  },
  {
    icon: BrainCircuit,
    title: 'Explainable AI (SHAP)',
    body: 'Global feature importance and plain-English explanations so a prediction is never a black box.',
  },
  {
    icon: GitCompare,
    title: 'Data-leakage analysis',
    body: 'Flags suspicious near-perfect correlations and target leakage, with financial scale-effects handled correctly.',
  },
  {
    icon: FileText,
    title: 'Compact, de-duplicated report',
    body: 'A 1–2 page HTML/PDF with KPIs, charts, recommendations, and XAI — every fact appears exactly once.',
  },
];

export default function FeaturesPage() {
  return (
    <MarketingShell>
      <section className="mx-auto max-w-5xl px-5 pt-20 pb-10 text-center sm:px-6">
        <span className="inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-3.5 py-1 text-xs font-semibold uppercase tracking-wide text-violet-600">
          <Sparkles size={13} /> Capabilities
        </span>
        <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-extrabold tracking-tight sm:text-5xl">
          Everything you need to understand a dataset
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-[#475569]">
          From the first upload to a downloadable executive report — here is what runs
          under the hood, all grounded in deterministic computation.
        </p>
      </section>

      <section className="mx-auto max-w-6xl px-5 pb-16 sm:px-6">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((cap) => (
            <div key={cap.title} className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
              <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 text-white">
                <cap.icon size={20} />
              </div>
              <h3 className="mt-4 text-base font-bold">{cap.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[#64748B]">{cap.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* What's in the report */}
      <section className="bg-white">
        <div className="mx-auto max-w-5xl px-5 py-16 sm:px-6">
          <div className="mb-10 text-center">
            <h2 className="text-3xl font-bold tracking-tight">What&apos;s inside the report</h2>
            <p className="mt-3 text-[#64748B]">Concise by design — and free of repeated content.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              ['Dataset snapshot', 'Filename, shape, detected type, and the important columns.'],
              ['Key metrics', 'The headline KPIs — surfaced once, never repeated downstream.'],
              ['Data quality', 'Quality score, missing values, duplicates, and the top warning.'],
              ['Important insights', 'The highest-signal findings, ranked and de-duplicated.'],
              ['Charts', 'Up to two auto-selected visualisations with takeaways.'],
              ['Model performance evaluation', 'R²/RMSE/MAE or accuracy/F1 with a plain-English read and leakage note.'],
              ['Recommendations', 'At most three concrete, prioritised next steps.'],
              ['Explainable AI', 'SHAP feature importance — always the final section.'],
            ].map(([title, body]) => (
              <div key={title} className="flex items-start gap-3 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-4">
                <Table size={16} className="mt-0.5 shrink-0 text-violet-500" />
                <div>
                  <h4 className="text-sm font-semibold text-[#0F172A]">{title}</h4>
                  <p className="mt-0.5 text-xs leading-relaxed text-[#64748B]">{body}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-10 flex items-center justify-center gap-3 rounded-2xl border border-emerald-100 bg-emerald-50/50 px-6 py-5">
            <ShieldCheck size={20} className="shrink-0 text-emerald-500" />
            <p className="text-sm text-[#475569]">
              Works fully offline in <span className="font-semibold">Mock mode</span> with no API keys —
              the LLM is optional and only refines wording.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-5 py-16 text-center sm:px-6">
        <h2 className="text-2xl font-bold tracking-tight">Try it on your own data</h2>
        <div className="mt-6">
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-violet-500 to-blue-500 px-7 py-3.5 text-base font-bold text-white shadow-lg shadow-violet-500/25 transition-all hover:brightness-110 active:scale-95"
          >
            Open the workspace <ArrowRight size={18} />
          </Link>
        </div>
      </section>
    </MarketingShell>
  );
}
