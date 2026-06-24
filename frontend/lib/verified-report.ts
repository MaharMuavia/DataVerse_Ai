import type { Kpi, AuditEntry, KpiProvenance } from '@/lib/dataverse-api';

const esc = (value: unknown): string =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

const fmt = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'number') return new Intl.NumberFormat('en-US', { maximumFractionDigits: 4 }).format(value);
  return esc(value);
};

function receiptHtml(prov: KpiProvenance): string {
  const columns = prov.sample_rows?.length ? Object.keys(prov.sample_rows[0]) : [];
  const chips = [prov.operation, ...prov.source_columns]
    .map((c) => `<span class="chip">${esc(c)}</span>`)
    .join('');
  const table = columns.length
    ? `<table><thead><tr>${columns.map((c) => `<th>${esc(c)}</th>`).join('')}</tr></thead>` +
      `<tbody>${prov.sample_rows
        .map((row) => `<tr>${columns.map((c) => `<td>${fmt(row[c])}</td>`).join('')}</tr>`)
        .join('')}</tbody></table>`
    : '';
  return (
    `<div class="receipt"><p class="formula">${esc(prov.formula_plain)}</p>` +
    `<div class="chips">${chips}</div>${table}` +
    `<p class="verified">&#10003; Verified deterministically from your rows (${esc(prov.row_count)} rows)</p></div>`
  );
}

export type VerifiedReportInput = {
  title?: string;
  answer?: string;
  kpis?: Kpi[];
  audit?: AuditEntry[];
};

export function buildVerifiedReportHtml({ title, answer, kpis = [], audit = [] }: VerifiedReportInput): string {
  const heading = esc(title || 'DataVerse Verified Report');
  const generated = new Date().toLocaleString();

  const kpiCards = kpis
    .map(
      (k) =>
        `<div class="kpi"><div class="kpi-label">${esc(k.label)}</div>` +
        `<div class="kpi-value">${fmt(k.value)}</div>` +
        `${k.provenance ? receiptHtml(k.provenance) : ''}</div>`,
    )
    .join('');

  const auditRows = audit
    .map(
      (e) =>
        `<details class="audit-item"><summary><span class="cat">${esc(e.category)}</span> ` +
        `<span class="audit-label">${esc(e.label || e.metric_key || '')}</span>` +
        `<span class="audit-value">${fmt(e.value)}</span></summary>${receiptHtml(e)}</details>`,
    )
    .join('');

  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${heading}</title>
<style>
  :root { color-scheme: light; }
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; color: #0f172a; background: #f8fafc; margin: 0; padding: 32px; }
  .wrap { max-width: 860px; margin: 0 auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 32px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .meta { color: #64748b; font-size: 12px; margin-bottom: 20px; }
  .badge { display: inline-flex; gap: 6px; align-items: center; background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; border-radius: 999px; padding: 3px 10px; font-size: 11px; font-weight: 600; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .05em; color: #64748b; margin: 28px 0 10px; }
  .answer { font-size: 14px; line-height: 1.6; color: #334155; white-space: pre-wrap; }
  .kpis { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
  .kpi { border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; }
  .kpi-label { font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: #64748b; font-weight: 600; }
  .kpi-value { font-size: 20px; font-weight: 800; margin: 6px 0; }
  .receipt { border: 1px solid #ede9fe; background: #f5f3ff66; border-radius: 8px; padding: 10px; font-size: 11px; color: #475569; margin-top: 8px; }
  .formula { font-weight: 500; color: #334155; margin: 0 0 6px; }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; }
  .chip { background: #fff; border: 1px solid #ede9fe; border-radius: 5px; padding: 1px 6px; font-family: ui-monospace, monospace; font-size: 10px; color: #6d28d9; }
  .receipt table { width: 100%; border-collapse: collapse; font-size: 10px; }
  .receipt th { text-align: left; color: #94a3b8; padding: 2px 8px 2px 0; }
  .receipt td { padding: 2px 8px 2px 0; border-top: 1px solid #ede9fe; }
  .verified { color: #059669; margin: 6px 0 0; }
  .audit-item { border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 12px; margin-bottom: 8px; }
  .audit-item summary { cursor: pointer; display: flex; gap: 8px; align-items: center; font-size: 13px; }
  .cat { background: #f1f5f9; color: #64748b; border-radius: 4px; padding: 1px 6px; font-size: 9px; font-weight: 700; text-transform: uppercase; }
  .audit-label { flex: 1; color: #334155; font-weight: 500; }
  .audit-value { font-weight: 700; }
</style></head>
<body><div class="wrap">
  <h1>${heading}</h1>
  <div class="meta">Generated ${esc(generated)}</div>
  <span class="badge">&#10003; Every number below is verifiable</span>
  ${answer ? `<h2>Summary</h2><div class="answer">${esc(answer)}</div>` : ''}
  ${kpiCards ? `<h2>Key metrics &mdash; with receipts</h2><div class="kpis">${kpiCards}</div>` : ''}
  ${auditRows ? `<h2>Full audit trail (${audit.length})</h2>${auditRows}` : ''}
</div></body></html>`;
}
