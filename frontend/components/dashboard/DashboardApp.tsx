'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'motion/react';
import {
  Menu, History, Database, Bot, Table, AlertTriangle,
  Paperclip, ArrowRight, BarChart2, BrainCircuit,
  Brain, CheckCircle2, TrendingUp, FileSpreadsheet, Eye,
  CloudUpload, FileText, Home, LogOut,
} from 'lucide-react';
import {
  API_BASE_URL,
  BACKEND_START_COMMAND,
  analyzeSession,
  cleanDataset,
  checkBackendHealth,
  createSession,
  getSession,
  listDatasets,
  listSessions,
  openProgressStream,
  renarrateReport,
  streamQuery,
  uploadDataset,
  DataVerseApiError,
  type ChartPayload,
  type ChatEvent,
  type ChatSessionSummary,
  type ProgressEvent,
  type ProgressStreamHandle,
  type RecentDataset,
  type TablePayload,
  type UploadResponse,
} from '@/lib/dataverse-api';
import { useAuth } from '@/lib/auth';
import { ThinkingTrace, reduceProgress, type ThinkingStep } from '@/components/ThinkingTrace';
import { DropZone } from '@/components/DropZone';
import { GlassCard } from './GlassCard';
import { KpiCard } from './KpiCard';
import { Composer } from './Composer';
import { VerificationPanel } from './VerificationPanel';
import { QualityDoctorPanel } from './QualityDoctorPanel';
import { formatCell, formatNumber } from '@/lib/dashboard-format';
import type { Kpi, AuditEntry, QualityDiagnosis } from '@/lib/dataverse-api';
import { buildVerifiedReportHtml } from '@/lib/verified-report';
import ReactMarkdown from 'react-markdown';

// --- Shared Constants & Types ---
type ViewState = 'analyze' | 'report';
type ChatRole = 'user' | 'assistant' | 'system';

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  events?: ChatEvent[];
  liveSteps?: ThinkingStep[];
  narrationProvider?: string;
  kpis?: Kpi[];
  auditTrail?: AuditEntry[];
  qualityDoctor?: QualityDiagnosis;
  charts?: ChartPayload[];
  tables?: TablePayload[];
  recommendations?: string[];
  suggestions?: string[];
  report?: {
    report_id: string;
    html_url?: string;
    pdf_url?: string;
  } | null;
  xai?: {
    status?: string;
    method?: string;
    global_feature_importance?: Array<{ feature: string; importance: number }>;
    top_features?: string[];
    local_explanations?: Array<{ sample_index: number; top_contributors: Array<{ feature: string; shap_value: number }> }>;
    plain_english_explanation?: string;
    warnings?: string[];
  } | null;
  isLoading?: boolean;
};

type DatasetSummary = UploadResponse & {
  originalFileSize?: number;
};

type BackendConnectionStatus = 'checking' | 'connected' | 'disconnected';

const datasetFromRecent = (item: RecentDataset): DatasetSummary => {
  const columns = Array.isArray(item.columns)
    ? item.columns as Array<{ name?: string; dtype?: string } | string>
    : [];
  const schemaProfile = item.schema_profile as ({ dataset_type?: string; semantic_map?: { dataset_type?: string } } | undefined);
  const semanticMap = item.semantic_map as ({ dataset_type?: string } | undefined);
  return {
    session_id: item.session_id,
    success: true,
    message: 'Dataset loaded from saved session.',
    is_retail: false,
    dataset_id: item.id,
    dataset_filename: item.filename || item.original_filename || 'Untitled dataset',
    dataset_rows: item.row_count,
    dataset_cols: item.column_count,
    column_names: columns.map((column) => typeof column === 'string' ? column : column.name || ''),
    column_dtypes: columns.map((column) => typeof column === 'string' ? '' : column.dtype || ''),
    dataset_profile: item.schema_profile as DatasetSummary['dataset_profile'],
    dataset_type: semanticMap?.dataset_type ?? schemaProfile?.semantic_map?.dataset_type ?? schemaProfile?.dataset_type,
    created_at: item.created_at,
  };
};

const isNumericType = (dtype?: string) => {
  const normalized = dtype?.toLowerCase() ?? '';
  return ['int', 'float', 'double', 'number', 'decimal'].some((needle) => normalized.includes(needle));
};

const keyedLabel = (scope: string, label: string | undefined, index: number) =>
  `${scope}-${label || 'item'}-${index}`;

const isInvalidChartLabel = (value: unknown) => {
  const normalized = String(value ?? '').trim().toLowerCase();
  return !normalized || ['n/a', 'na', 'nan', 'none', 'null'].includes(normalized);
};

const validateChartPayload = (chart: ChartPayload) => {
  const data = Array.isArray(chart.data) ? chart.data.filter((row): row is Record<string, unknown> => !!row && typeof row === 'object') : [];
  const xKey = chart.x_key;
  const yKey = chart.y_key;
  if (!data.length || !xKey || !yKey) return { data: [], values: [], valid: false };
  const values: number[] = [];
  for (const row of data) {
    if (!(xKey in row) || !(yKey in row) || isInvalidChartLabel(row[xKey])) {
      return { data: [], values: [], valid: false };
    }
    const value = Number(row[yKey]);
    if (!Number.isFinite(value)) {
      return { data: [], values: [], valid: false };
    }
    values.push(value);
  }
  if (!values.length || values.every((value) => value === 0)) return { data: [], values: [], valid: false };
  return { data, values, valid: true };
};

const datasetTypeOf = (dataset: DatasetSummary | null) => dataset?.dataset_type || String(dataset?.dataset_profile?.dataset_type || 'generic');

const datasetTypeLabel = (dataset: DatasetSummary | null) => {
  const type = datasetTypeOf(dataset);
  return type.split('_').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
};

const datasetSuggestions = (dataset: DatasetSummary | null) => {
  const type = datasetTypeOf(dataset);
  const semantic = (dataset?.dataset_profile?.semantic_columns ?? {}) as Record<string, unknown>;
  if (type === 'business_leads') {
    return [
      semantic.country ? 'Which countries have the most businesses?' : null,
      semantic.industry ? 'Which industries are most common?' : null,
      'Which businesses look like the highest-value leads?',
      semantic.employee_range ? 'Segment businesses by employee range.' : null,
      semantic.revenue_range ? 'Segment businesses by yearly revenue range.' : null,
      'Create an outreach strategy for these leads.',
      semantic.website ? 'Which businesses have no website?' : null,
    ].filter(Boolean) as string[];
  }
  if (type === 'sales') {
    return [
      semantic.product ? 'What are the top products?' : null,
      semantic.product && semantic.date ? 'Which products are trending?' : null,
      semantic.revenue && semantic.date ? 'Show revenue by month.' : null,
      semantic.category ? 'Which category performs best?' : null,
    ].filter(Boolean) as string[];
  }
  return ['Summarize this dataset.', 'Which columns have missing values?', 'Show unique values by column.', 'Find important patterns.'];
};

const backendUnavailableMessage = () => (
  `Backend is not running. Start FastAPI on port 8000 or update NEXT_PUBLIC_DATAVERSE_API_URL. Using API URL: ${API_BASE_URL}. Command: ${BACKEND_START_COMMAND}`
);

const isBackendConnectionError = (error: unknown) => (
  error instanceof DataVerseApiError
    ? error.status === 0
    : error instanceof Error && error.message.toLowerCase().includes('backend is not running')
);

// --- Components ---

const ResultTable = ({ table }: { table: TablePayload }) => (
  <GlassCard className="overflow-hidden border-[#CBD5E1]/20">
    <div className="flex items-center gap-3 px-4 py-3 border-b border-[#E2E8F0]/40 bg-[#F8FAFC]/40">
      <Table size={16} className="text-violet-300" />
      <span className="text-sm font-medium text-[#0F172A]">{table.title}</span>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead className="bg-[#FFFFFF] text-[#64748B]">
          <tr>
            {table.columns.map((column, columnIndex) => (
              <th key={keyedLabel('table-column', column, columnIndex)} className="px-4 py-3 font-semibold whitespace-nowrap">{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.slice(0, 10).map((row, index) => (
            <tr key={index} className="border-t border-[#E2E8F0]/30 text-[#0F172A]">
              {table.columns.map((column, columnIndex) => (
                <td key={keyedLabel(`table-cell-${index}`, column, columnIndex)} className="px-4 py-3 whitespace-nowrap">{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </GlassCard>
);

const SimpleChart = ({ chart }: { chart: ChartPayload }) => {
  const yKey = chart.y_key;
  const validated = validateChartPayload(chart);
  const data = validated.data;
  const values = validated.values;
  const max = Math.max(...values.map((value) => Math.abs(value)), 1);
  const colors = ['#8b5cf6', '#3b82f6', '#0ea5e9', '#10b981', '#f59e0b', '#f43f5e', '#14b8a6', '#a855f7'];
  const labelOf = (row: Record<string, unknown>) => formatCell(row[chart.x_key]);

  if (!validated.valid || !yKey) {
    return (
      <GlassCard className="p-4 border-amber-500/20">
        <div className="flex items-center gap-3">
          <AlertTriangle size={16} className="text-amber-300" />
          <span className="text-sm text-[#64748B]">{chart.title || 'Chart'} has no displayable data.</span>
        </div>
      </GlassCard>
    );
  }

  if (chart.type === 'confusion_matrix') {
    const actualLabels = Array.from(new Set(data.map((row) => formatCell(row.actual)))).sort();
    const predictedLabels = Array.from(new Set(data.map((row) => formatCell(row.predicted)))).sort();
    const countByPair = new Map(data.map((row) => [`${formatCell(row.actual)}|${formatCell(row.predicted)}`, Number(row.count) || 0]));
    const largest = Math.max(...Array.from(countByPair.values()), 1);
    return (
      <GlassCard className="p-4 border-blue-500/20">
        <div className="flex items-center gap-3 mb-4">
          <BarChart2 size={16} className="text-blue-400" />
          <span className="text-sm font-medium text-[#0F172A]">{chart.title}</span>
        </div>
        <div className="overflow-x-auto">
          <div
            className="grid gap-1 min-w-max text-[10px]"
            style={{ gridTemplateColumns: `120px repeat(${predictedLabels.length}, minmax(48px, 1fr))` }}
          >
            <div className="text-[#64748B]">Actual \ Predicted</div>
            {predictedLabels.map((label) => <div key={label} className="text-[#64748B] truncate" title={label}>{label}</div>)}
            {actualLabels.map((actual) => (
              <React.Fragment key={actual}>
                <div className="text-[#64748B] truncate py-2" title={actual}>{actual}</div>
                {predictedLabels.map((predicted) => {
                  const count = countByPair.get(`${actual}|${predicted}`) ?? 0;
                  const opacity = 0.18 + (count / largest) * 0.72;
                  return (
                    <div
                      key={`${actual}-${predicted}`}
                      className="rounded-md py-2 text-center font-mono text-[#0F172A]"
                      style={{ backgroundColor: `rgba(59, 130, 246, ${opacity})` }}
                    >
                      {formatCell(count)}
                    </div>
                  );
                })}
              </React.Fragment>
            ))}
          </div>
        </div>
      </GlassCard>
    );
  }

  if ((chart.type === 'pie' || chart.type === 'donut') && yKey) {
    const total = values.reduce((sum, value) => sum + Math.max(0, value), 0) || 1;
    const radius = 58;
    const circumference = 2 * Math.PI * radius;
    const rawSegments = data.slice(0, 8).map((row, index) => {
      const value = Math.max(0, Number(row[yKey]) || 0);
      const dash = (value / total) * circumference;
      return { row, index, dash };
    });
    const segments = rawSegments.reduce<{ offset: number; items: Array<{ index: number; dash: number; offset: number }> }>(
      (acc, segment) => ({
        offset: acc.offset - segment.dash,
        items: [...acc.items, { index: segment.index, dash: segment.dash, offset: acc.offset }],
      }),
      { offset: 25, items: [] },
    ).items;
    return (
      <GlassCard className="p-4 border-violet-500/20">
        <div className="flex items-center gap-3 mb-4">
          <BarChart2 size={16} className="text-violet-300" />
          <span className="text-sm font-medium text-[#0F172A]">{chart.title}</span>
        </div>
        <div className="grid md:grid-cols-[180px_1fr] gap-4 items-center">
          <svg viewBox="0 0 160 160" className="w-44 h-44 mx-auto">
            <circle cx="80" cy="80" r={radius} fill="none" stroke="#F1F5F9" strokeWidth="24" />
            {segments.map(({ index, dash, offset }) => (
                <circle
                  key={index}
                  cx="80"
                  cy="80"
                  r={radius}
                  fill="none"
                  stroke={colors[index % colors.length]}
                  strokeWidth="24"
                  strokeDasharray={`${dash} ${circumference - dash}`}
                  strokeDashoffset={offset}
                  transform="rotate(-90 80 80)"
                  className="transition-all"
                />
            ))}
            {chart.type === 'donut' && <circle cx="80" cy="80" r="36" fill="#FFFFFF" />}
          </svg>
          <div className="space-y-2">
            {data.slice(0, 8).map((row, index) => {
              const value = Number(row[yKey]) || 0;
              return (
                <div key={index} className="flex items-center gap-2 text-xs">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: colors[index % colors.length] }} />
                  <span className="text-[#64748B] truncate" title={labelOf(row)}>{labelOf(row)}</span>
                  <span className="ml-auto font-mono text-[#0F172A]">{((Math.max(0, value) / total) * 100).toFixed(1)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      </GlassCard>
    );
  }

  if (chart.type === 'line' && yKey) {
    const width = 520;
    const height = 180;
    const min = Math.min(...values, 0);
    const span = Math.max(max - min, 1);
    const groups = new Map<string, Record<string, unknown>[]>();
    data.forEach((row) => {
      const key = chart.series_key ? formatCell(row[chart.series_key]) : 'Trend';
      groups.set(key, [...(groups.get(key) ?? []), row]);
    });
    const lines = [...groups.entries()].slice(0, 6).map(([series, rows], seriesIndex) => {
      const points = rows.map((row, index) => {
        const value = Number(row[yKey]) || 0;
        const x = rows.length === 1 ? width / 2 : (index / (rows.length - 1)) * width;
        const y = height - (((value - min) / span) * (height - 24) + 12);
        return `${x},${Math.max(8, Math.min(height - 8, y))}`;
      }).join(' ');
      return { series, points, color: colors[seriesIndex % colors.length] };
    });

    return (
      <GlassCard className="p-4 border-blue-500/20">
        <div className="flex items-center gap-3 mb-4">
          <BarChart2 size={16} className="text-blue-400" />
          <span className="text-sm font-medium text-[#0F172A]">{chart.title}</span>
        </div>
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-48 overflow-visible">
          {lines.map((line) => (
            <polyline key={line.series} fill="none" stroke={line.color} strokeWidth="3" points={line.points} />
          ))}
        </svg>
        {chart.series_key ? (
          <div className="flex flex-wrap gap-3 mb-3 text-[10px] text-[#64748B]">
            {lines.map((line) => (
              <span key={line.series} className="inline-flex items-center gap-1">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: line.color }} />
                {line.series}
              </span>
            ))}
          </div>
        ) : null}
        <div className="flex justify-between gap-3 text-[10px] text-[#64748B]">
          {data.slice(0, 6).map((row, index) => <span key={index} className="truncate" title={labelOf(row)}>{labelOf(row)}</span>)}
        </div>
      </GlassCard>
    );
  }

  if (yKey) {
    return (
      <GlassCard className="p-4 border-blue-500/20">
        <div className="flex items-center gap-3 mb-4">
          <BarChart2 size={16} className="text-blue-400" />
          <span className="text-sm font-medium text-[#0F172A]">{chart.title}</span>
        </div>
        <div className="space-y-3">
          {data.slice(0, 10).map((row, index) => {
            const raw = Number(row[yKey]) || 0;
            const width = `${Math.max(4, Math.min(100, Math.abs(raw) / max * 100))}%`;
            return (
              <div key={index} className="grid grid-cols-[minmax(96px,180px)_1fr_72px] items-center gap-3">
                <span className="text-xs text-[#64748B] truncate" title={labelOf(row)}>{labelOf(row)}</span>
                <div className="h-2.5 rounded-full bg-[#F1F5F9] overflow-hidden">
                  <div className="h-full rounded-full" style={{ width, background: raw < 0 ? '#f43f5e' : `linear-gradient(90deg, ${colors[index % colors.length]}, #60a5fa)` }} />
                </div>
                <span className="text-xs font-mono text-[#0F172A] text-right">{formatCell(raw)}</span>
              </div>
            );
          })}
        </div>
      </GlassCard>
    );
  }

  return null;
};

// --- Views ---

const AnalyzeWorkspaceView = ({
  dataset,
  uploadStatus,
  backendStatus,
  isQuerying,
  messages,
  recentDatasets,
  onUpload,
  onSubmit,
  onNavigateToReport,
  onSelectRecentDataset,
  onRenarrate,
  onCopyAsMarkdown,
  onApplyFixes,
  isCleaning,
}: {
  dataset: DatasetSummary | null;
  uploadStatus: string | null;
  backendStatus: BackendConnectionStatus;
  isQuerying: boolean;
  messages: ChatMessage[];
  recentDatasets: RecentDataset[];
  onUpload: (file: File) => void;
  onSubmit: (query: string) => void;
  onNavigateToReport: () => void;
  onSelectRecentDataset: (sessionId: string) => void;
  onRenarrate: (messageId: string, reportId: string) => Promise<void> | void;
  onCopyAsMarkdown: (message: ChatMessage) => void;
  onApplyFixes: (fixIds: string[]) => void;
  isCleaning: boolean;
}) => {
  const assistantMessages = messages.filter((m) => m.role === 'assistant');
  const latestAssistant = assistantMessages.at(-1);
  const kpis = latestAssistant?.kpis ?? [];
  const charts = latestAssistant?.charts ?? [];

  const isUploading = uploadStatus?.toLowerCase().includes('upload') ||
                      uploadStatus?.toLowerCase().includes('parsing') ||
                      uploadStatus?.toLowerCase().includes('profiling');

  const profile = dataset?.dataset_profile as Record<string, unknown> | undefined;
  const quality = (profile?.quality ?? {}) as Record<string, unknown>;
  const datasetType = dataset ? datasetTypeLabel(dataset) : 'Generic';
  const previewRows = (profile?.preview_rows ?? []) as Array<Record<string, unknown>>;
  const previewColumns = (profile?.preview_columns ?? []) as string[];
  const semanticColumns = Object.entries((profile?.semantic_columns ?? {}) as Record<string, unknown>).filter(([, col]) => col !== null && col !== undefined);
  const numericColumns = dataset ? dataset.column_names.filter((name, idx) => isNumericType(dataset.column_dtypes[idx])) : [];

  const suggestedQuestions = datasetSuggestions(dataset);

  return (
    <div className="flex-1 w-full mx-auto px-4 md:px-8 pb-32 pt-24 overflow-y-auto overflow-x-hidden custom-scrollbar bg-[#F8FAFC]">
      <div className="max-w-[1000px] mx-auto space-y-8">

        {/* Header Block */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center shadow-lg">
               <Bot size={20} className="text-white" />
             </div>
             <div>
               <h1 className="text-xl md:text-2xl font-bold text-[#0F172A]">Analyze Workspace</h1>
               <p className="text-sm text-[#64748B]">{dataset?.dataset_filename || 'No dataset uploaded yet'}</p>
             </div>
          </div>
          {dataset && latestAssistant && (
            <button
              onClick={onNavigateToReport}
              className="flex items-center gap-2 bg-gradient-to-r from-violet-500 to-blue-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold hover:brightness-110 active:scale-95 transition-all shadow-[0_0_15px_rgba(139,92,246,0.3)]"
            >
              View Report & XAI <ArrowRight size={16} />
            </button>
          )}
        </div>

        {/* Upload State */}
        {!dataset && (
          <div className="space-y-6">
            <DropZone
              isUploading={!!isUploading}
              uploadStatus={uploadStatus}
              backendStatus={backendStatus}
              onUpload={onUpload}
            />

            {/* Recent Datasets */}
            {recentDatasets.length > 0 && !isUploading && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Reload Recent Sessions</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {recentDatasets.slice(0, 4).map((recent) => (
                    <GlassCard
                      key={recent.id}
                      onClick={() => onSelectRecentDataset(recent.session_id)}
                      className="p-4 bg-white border-[#E2E8F0] hover:bg-[#F8FAFC]"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-500">
                          <Table size={16} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-[#0F172A] truncate">{recent.filename}</p>
                          <p className="text-xs text-[#64748B] mt-0.5">{formatNumber(recent.row_count)} rows &bull; {recent.column_count} cols</p>
                        </div>
                      </div>
                    </GlassCard>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Loading / Agent processing state */}
        {dataset && isQuerying && !latestAssistant && (
          <GlassCard className="p-6 border-[#E2E8F0] bg-white">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center text-violet-500">
                <BrainCircuit size={16} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-[#0F172A]">DatasetAgent &amp; AnalystAgent working</h3>
                <p className="text-xs text-[#64748B] mt-0.5">Profiling · EDA · metrics · modeling · XAI · narration</p>
              </div>
            </div>
            <ThinkingTrace
              steps={
                [...messages].reverse().find((message) => message.isLoading && Array.isArray(message.liveSteps))?.liveSteps
                  ?? []
              }
              title="Live progress"
              active
            />
          </GlassCard>
        )}

        {/* Workspace Panels */}
        {dataset && (
          <div className="space-y-8">
            {/* Row 1: Profile & Quality */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

              {/* Profile Card */}
              <GlassCard className="p-6 bg-white border-[#E2E8F0]">
                <h3 className="text-sm font-semibold text-[#0F172A] uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Database size={16} className="text-violet-500" /> Dataset Profile
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#F8FAFC] rounded-lg p-3 border border-[#E2E8F0]/50">
                    <p className="text-[11px] text-[#64748B] uppercase font-semibold">Row Count</p>
                    <p className="text-2xl font-bold text-violet-600 mt-1">{formatNumber(dataset.dataset_rows)}</p>
                  </div>
                  <div className="bg-[#F8FAFC] rounded-lg p-3 border border-[#E2E8F0]/50">
                    <p className="text-[11px] text-[#64748B] uppercase font-semibold">Column Count</p>
                    <p className="text-2xl font-bold text-violet-600 mt-1">{formatNumber(dataset.dataset_cols)}</p>
                  </div>
                  <div className="bg-[#F8FAFC] rounded-lg p-3 border border-[#E2E8F0]/50">
                    <p className="text-[11px] text-[#64748B] uppercase font-semibold">Numeric Columns</p>
                    <p className="text-lg font-semibold text-[#0F172A] mt-1">{numericColumns.length}</p>
                  </div>
                  <div className="bg-[#F8FAFC] rounded-lg p-3 border border-[#E2E8F0]/50">
                    <p className="text-[11px] text-[#64748B] uppercase font-semibold">Type Classification</p>
                    <p className="text-xs font-semibold text-blue-600 mt-1.5 truncate" title={datasetType}>{datasetType}</p>
                  </div>
                </div>

                {/* Column mapping */}
                <div className="mt-4 pt-4 border-t border-[#E2E8F0]">
                  <p className="text-xs font-semibold text-[#64748B] mb-2 uppercase">Semantic Mappings</p>
                  <div className="flex flex-wrap gap-2">
                    {semanticColumns.length ? semanticColumns.map(([role, col]) => (
                      <span key={role} className="text-[10px] bg-emerald-500/10 text-emerald-700 border border-emerald-500/20 rounded px-2.5 py-1 font-mono">
                        {role}: {String(col)}
                      </span>
                    )) : (
                      <span className="text-xs text-[#64748B]">No custom business mapping needed.</span>
                    )}
                  </div>
                </div>
              </GlassCard>

              {/* Quality summary Card */}
              <GlassCard className="p-6 bg-white border-[#E2E8F0]">
                <h3 className="text-sm font-semibold text-[#0F172A] uppercase tracking-wider mb-4 flex items-center gap-2">
                  <AlertTriangle size={16} className="text-amber-500" /> Data Quality Scan
                </h3>
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-[#F8FAFC] rounded-lg p-3 border border-[#E2E8F0]/50 text-center">
                    <p className="text-[10px] text-[#64748B] uppercase font-semibold">Score</p>
                    <p className="text-2xl font-bold text-emerald-500 mt-1">{quality.quality_score !== undefined ? `${quality.quality_score}%` : 'N/A'}</p>
                  </div>
                  <div className="bg-[#F8FAFC] rounded-lg p-3 border border-[#E2E8F0]/50 text-center">
                    <p className="text-[10px] text-[#64748B] uppercase font-semibold">Missing Cells</p>
                    <p className="text-xl font-bold text-[#0F172A] mt-1.5">{formatCell(quality.missing_cells ?? 0)}</p>
                  </div>
                  <div className="bg-[#F8FAFC] rounded-lg p-3 border border-[#E2E8F0]/50 text-center">
                    <p className="text-[10px] text-[#64748B] uppercase font-semibold">Duplicate Rows</p>
                    <p className="text-xl font-bold text-[#0F172A] mt-1.5">{formatCell(quality.duplicate_rows ?? 0)}</p>
                  </div>
                </div>

                {/* Warnings */}
                <div className="mt-4 pt-4 border-t border-[#E2E8F0] space-y-2">
                  <p className="text-xs font-semibold text-[#64748B] uppercase">Findings & Warnings</p>
                  {Array.isArray(quality.warnings) && quality.warnings.length > 0 ? (
                    <div className="space-y-1.5 max-h-[80px] overflow-y-auto custom-scrollbar">
                      {quality.warnings.slice(0, 3).map((warning, index) => (
                        <div key={index} className="text-xs text-[#64748B] flex items-start gap-1.5">
                          <span className="w-1.5 h-1.5 bg-amber-500 rounded-full mt-1.5 shrink-0" />
                          <span>{String(warning)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs text-emerald-600 flex items-center gap-1.5 font-medium">
                      <CheckCircle2 size={12} /> No critical data quality issues found!
                    </div>
                  )}
                </div>
              </GlassCard>

            </div>

            {/* Row 2: KPIs */}
            {kpis.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Key Business KPIs</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {kpis.slice(0, 4).map((kpi, idx) => (
                    <KpiCard key={idx} kpi={kpi} />
                  ))}
                </div>
              </div>
            )}

            {/* Row 3: Charts */}
            {charts.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Visualizations (Max 2 Charts)</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {charts.slice(0, 2).map((chart, idx) => (
                    <SimpleChart key={idx} chart={chart} />
                  ))}
                </div>
              </div>
            )}

            {/* Row 4: Dataset Preview */}
            {previewRows.length > 0 && (
              <GlassCard className="overflow-hidden border-[#E2E8F0] bg-white">
                <div className="flex items-center gap-3 px-5 py-4 border-b border-[#E2E8F0]/40">
                  <FileSpreadsheet size={16} className="text-blue-500" />
                  <span className="text-sm font-semibold text-[#0F172A]">Dataset Sample View</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F8FAFC] text-[#64748B] border-b border-[#E2E8F0]/40">
                      <tr>
                        {previewColumns.map((col, idx) => (
                          <th key={idx} className="px-4 py-3 font-semibold whitespace-nowrap">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewRows.map((row, rowIdx) => (
                        <tr key={rowIdx} className="border-b border-[#E2E8F0]/30 hover:bg-[#F8FAFC]/50 last:border-b-0">
                          {previewColumns.map((col, colIdx) => (
                            <td key={colIdx} className="px-4 py-3 text-[#334155] whitespace-nowrap font-medium">
                              {formatCell(row[col])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </GlassCard>
            )}

            {/* AnalystAgent Insights / Chat Response */}
            {latestAssistant && (
              <GlassCard className="p-6 bg-white border-[#E2E8F0] space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center text-violet-500">
                      <Brain size={16} />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-[#0F172A]">AnalystAgent Insights</h3>
                      <p className="text-[10px] text-[#64748B]">Interactive query response</p>
                    </div>
                  </div>
                  {latestAssistant.narrationProvider && (
                    <span
                      className={`text-[10px] px-2 py-1 rounded-full font-semibold uppercase tracking-wider border ${
                        latestAssistant.narrationProvider === 'deterministic'
                          ? 'bg-slate-100 text-slate-600 border-slate-200'
                          : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      }`}
                      title={
                        latestAssistant.narrationProvider === 'deterministic'
                          ? 'Narration generated deterministically from computed facts (no LLM).'
                          : `Narration polished by ${latestAssistant.narrationProvider.toUpperCase()}. All numbers come from the deterministic pipeline.`
                      }
                    >
                      {latestAssistant.narrationProvider === 'deterministic'
                        ? 'Deterministic'
                        : `${latestAssistant.narrationProvider} polished`}
                    </span>
                  )}
                </div>
                {latestAssistant.isLoading && latestAssistant.liveSteps && latestAssistant.liveSteps.length > 0 && (
                  <ThinkingTrace steps={latestAssistant.liveSteps} title="Thinking" active />
                )}
                <div className="dv-markdown text-sm text-[#334155] leading-relaxed">
                  <ReactMarkdown>{latestAssistant.content}</ReactMarkdown>
                </div>
                {latestAssistant.content && !latestAssistant.isLoading && (
                  <div className="flex items-center gap-2 pt-2 border-t border-[#E2E8F0]">
                    <button
                      onClick={() => onCopyAsMarkdown(latestAssistant)}
                      className="text-[11px] text-[#64748B] hover:text-violet-600 border border-[#E2E8F0] hover:border-violet-200 px-2.5 py-1 rounded-lg transition-all flex items-center gap-1"
                    >
                      Copy as markdown
                    </button>
                    {(latestAssistant.kpis?.length || latestAssistant.auditTrail?.length) ? (
                      <button
                        onClick={() => {
                          const html = buildVerifiedReportHtml({
                            title: dataset?.dataset_filename ? `Verified report — ${dataset.dataset_filename}` : undefined,
                            answer: latestAssistant.content,
                            kpis: latestAssistant.kpis,
                            audit: latestAssistant.auditTrail,
                          });
                          const blob = new Blob([html], { type: 'text/html' });
                          const url = URL.createObjectURL(blob);
                          const link = document.createElement('a');
                          link.href = url;
                          link.download = `verified-report-${Date.now()}.html`;
                          link.click();
                          URL.revokeObjectURL(url);
                        }}
                        className="text-[11px] text-violet-600 hover:text-violet-700 border border-violet-200 hover:bg-violet-50 px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 font-semibold"
                      >
                        Export verified report
                      </button>
                    ) : null}
                    {latestAssistant.report?.report_id && (
                      <button
                        onClick={() => onRenarrate(latestAssistant.id, latestAssistant.report!.report_id)}
                        className="text-[11px] text-violet-600 hover:text-violet-700 border border-violet-200 hover:bg-violet-50 px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 font-semibold"
                      >
                        Re-narrate with GPT
                      </button>
                    )}
                  </div>
                )}
              </GlassCard>
            )}

            {/* Tables from streamed queries */}
            {latestAssistant?.tables && latestAssistant.tables.length > 0 && (
              <div className="space-y-3">
                {latestAssistant.tables.slice(0, 3).map((table, idx) => (
                  <ResultTable key={idx} table={table} />
                ))}
              </div>
            )}

            {/* Data Quality Doctor: detect issues + one-click deterministic fixes */}
            {latestAssistant?.qualityDoctor && (
              <QualityDoctorPanel
                diagnosis={latestAssistant.qualityDoctor}
                onApply={onApplyFixes}
                isApplying={isCleaning}
              />
            )}

            {/* Verification panel: every number with a downloadable receipt */}
            {latestAssistant?.auditTrail && latestAssistant.auditTrail.length > 0 && (
              <VerificationPanel audit={latestAssistant.auditTrail} />
            )}

            {/* Query Section */}
            <Composer onSubmit={onSubmit} isQuerying={isQuerying} suggestedQuestions={suggestedQuestions} />

          </div>
        )}

      </div>
    </div>
  );
};

const resolveReportUrl = (url?: string) => {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const trimmedUrl = url.startsWith('/') ? url : `/${url}`;
  return `${API_BASE_URL}${trimmedUrl}`;
};

const ReportXAIPageView = ({
  dataset,
  messages,
}: {
  dataset: DatasetSummary | null;
  messages: ChatMessage[];
}) => {
  const assistantMessages = messages.filter((m) => m.role === 'assistant');
  const latestWithReport = [...assistantMessages].reverse().find(
    (m) => m.report?.html_url || m.xai?.plain_english_explanation
  );

  const report = latestWithReport?.report;
  const xai = latestWithReport?.xai;

  const resolvedHtmlUrl = resolveReportUrl(report?.html_url);
  const resolvedPdfUrl = resolveReportUrl(report?.pdf_url);

  return (
    <div className="flex-1 w-full mx-auto px-4 md:px-8 pb-32 pt-24 overflow-y-auto overflow-x-hidden custom-scrollbar bg-[#F8FAFC]">
      <div className="max-w-[1000px] mx-auto space-y-8 animate-fade-in">

        {/* Header Block */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E2E8F0]/50 pb-4">
          <div className="flex items-center gap-3">
             <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
               <FileText size={20} className="text-white" />
             </div>
             <div>
               <h1 className="text-xl md:text-2xl font-bold text-[#0F172A]">Compiled Report & XAI Analysis</h1>
               <p className="text-sm text-[#64748B]">{dataset?.dataset_filename || 'Dataset Report'}</p>
             </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {resolvedHtmlUrl && (
              <a
                href={resolvedHtmlUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 bg-white text-[#0F172A] border border-[#E2E8F0] px-4 py-2.5 rounded-xl text-sm font-semibold hover:bg-[#F8FAFC] transition-all shadow-sm"
              >
                <Eye size={15} /> Open HTML Report
              </a>
            )}
            {resolvedPdfUrl && (
              <a
                href={resolvedPdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 bg-gradient-to-r from-violet-500 to-blue-500 text-white px-4 py-2.5 rounded-xl text-sm font-semibold hover:brightness-110 active:scale-95 transition-all shadow-[0_0_15px_rgba(139,92,246,0.3)]"
              >
                <CloudUpload size={15} /> Download PDF
              </a>
            )}
          </div>
        </div>

        {/* HTML Report Iframe Section */}
        {resolvedHtmlUrl ? (
          <GlassCard className="p-0 border-[#E2E8F0] bg-white overflow-hidden shadow-sm h-[650px] flex flex-col">
            <div className="bg-[#F8FAFC] border-b border-[#E2E8F0]/60 px-5 py-3 flex items-center justify-between">
              <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Executive Report Preview</span>
              <span className="text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">Compacted 1-2 Pages</span>
            </div>
            <iframe
              src={resolvedHtmlUrl}
              className="w-full flex-1 border-0 bg-white"
              title="Compiled Business Report"
            />
          </GlassCard>
        ) : (
          <GlassCard className="p-10 border-[#E2E8F0] bg-white text-center py-16">
            <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-slate-100">
              <FileText size={20} className="text-slate-400" />
            </div>
            <h3 className="text-base font-bold text-[#0F172A]">No Report Available</h3>
            <p className="text-sm text-[#64748B] mt-1 max-w-sm mx-auto">Upload a dataset and trigger the analysis workflow to generate the compiled report.</p>
          </GlassCard>
        )}

        {/* Explainable AI (XAI) Section */}
        {xai && (
          <GlassCard className="p-6 bg-white border-[#E2E8F0] space-y-6 shadow-sm">
            <div className="flex items-center gap-3 border-b border-[#E2E8F0]/50 pb-4">
              <div className="w-10 h-10 rounded-xl bg-violet-50 flex items-center justify-center text-violet-500 border border-violet-100">
                <BrainCircuit size={20} />
              </div>
              <div>
                <h3 className="font-bold text-[#0F172A] text-lg">Explainable AI (XAI) Analysis</h3>
                <span className="text-[10px] bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">AnalystAgent SHAP Engine</span>
              </div>
            </div>

            {xai.plain_english_explanation && (
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-[#64748B] uppercase tracking-wider">Plain English Explanation</h4>
                <p className="text-sm text-[#334155] leading-relaxed whitespace-pre-line bg-[#F8FAFC] border border-[#E2E8F0]/50 rounded-xl p-4">
                  {xai.plain_english_explanation}
                </p>
              </div>
            )}

            {xai.global_feature_importance && xai.global_feature_importance.length > 0 && (
              <div className="space-y-4 pt-2">
                <h4 className="text-xs font-bold text-[#64748B] uppercase tracking-wider flex items-center gap-2">
                  <TrendingUp size={14} className="text-violet-500" /> Global Feature Importance (SHAP)
                </h4>
                <div className="space-y-3 bg-[#F8FAFC]/50 border border-[#E2E8F0]/30 rounded-xl p-4">
                  {xai.global_feature_importance.map((item, idx) => (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-xs font-semibold text-[#0F172A]">
                        <span>{item.feature}</span>
                        <span className="font-mono text-[#64748B]">{(item.importance * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-[#E2E8F0] h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-violet-500 to-blue-500 h-full rounded-full"
                          style={{ width: `${Math.min(item.importance * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </GlassCard>
        )}

      </div>
    </div>
  );
};


// --- Dashboard Shell ---

export function DashboardApp() {
  const router = useRouter();
  const { session, signOut } = useAuth();
  const [currentView, setCurrentView] = useState<ViewState>('analyze');
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [, setSessions] = useState<ChatSessionSummary[]>([]);
  const [recentDatasets, setRecentDatasets] = useState<RecentDataset[]>([]);
  const [dataset, setDataset] = useState<DatasetSummary | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const [isCleaning, setIsCleaning] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<BackendConnectionStatus>('checking');
  const activeRequestRef = useRef(0);

  const userInitials = (session?.name || 'Guest')
    .split(' ')
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();

  const nextRequestToken = () => {
    activeRequestRef.current += 1;
    return activeRequestRef.current;
  };

  const isStaleRequest = (token: number) => token !== activeRequestRef.current;

  const refreshBackendStatus = async () => {
    setBackendStatus('checking');
    const health = await checkBackendHealth();
    setBackendStatus(health.connected ? 'connected' : 'disconnected');
    return health.connected;
  };

  const refreshSidebar = async () => {
    try {
      const [nextSessions, nextDatasets] = await Promise.all([listSessions(), listDatasets()]);
      setSessions(nextSessions);
      setRecentDatasets(nextDatasets);
    } catch {
      // Local development can start before the backend. Keep a clean workspace.
    }
  };

  useEffect(() => {
    let cancelled = false;
    checkBackendHealth()
      .then((health) => {
        if (!cancelled) setBackendStatus(health.connected ? 'connected' : 'disconnected');
      })
      .catch(() => {
        if (!cancelled) setBackendStatus('disconnected');
      });
    Promise.all([listSessions(), listDatasets()])
      .then(([nextSessions, nextDatasets]) => {
        if (!cancelled) {
          setSessions(nextSessions);
          setRecentDatasets(nextDatasets);
        }
      })
      .catch(() => {
        // Backend may not be running yet; keep workspace empty.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleNewChat = async () => {
    setIsMobileSidebarOpen(false);
    const token = nextRequestToken();
    setDataset(null);
    setMessages([]);
    setUploadStatus(null);
    setIsQuerying(false);
    setCurrentSessionId(null);
    setCurrentView('analyze');
    try {
      await refreshBackendStatus();
      const session = await createSession();
      if (isStaleRequest(token)) return;
      setCurrentSessionId(session.id);
      await refreshSidebar();
    } catch {
      if (isStaleRequest(token)) return;
      setCurrentSessionId(null);
    }
  };

  const loadSession = async (sessionId: string) => {
    setIsMobileSidebarOpen(false);
    const token = nextRequestToken();
    const detail = await getSession(sessionId);
    if (isStaleRequest(token)) return;
    setCurrentSessionId(detail.id);
    const active = detail.datasets.find((item) => item.id === detail.active_dataset_id) ?? detail.datasets[0];
    setDataset(active ? datasetFromRecent(active) : null);
    setMessages(detail.messages.filter((item): item is typeof item & { role: ChatRole } => item.role !== 'agent').map((item) => ({
      id: item.id,
      role: item.role,
      content: item.content,
      events: Array.isArray(item.payload?.agents)
        ? (item.payload.agents as Array<{ name: string; status: string; summary?: string }>).map((agent) => ({
          step: agent.name,
          message: `${agent.name}: ${agent.status}${agent.summary ? ` - ${agent.summary}` : ''}`,
        }))
        : undefined,
      kpis: item.payload?.kpis as ChatMessage['kpis'],
      auditTrail: item.payload?.audit_trail as ChatMessage['auditTrail'],
      qualityDoctor: item.payload?.quality_doctor as ChatMessage['qualityDoctor'],
      charts: item.payload?.charts as ChartPayload[] | undefined,
      tables: item.payload?.tables as TablePayload[] | undefined,
      recommendations: item.payload?.recommendations as string[] | undefined,
      report: item.payload?.report as ChatMessage['report'],
      xai: item.payload?.xai as ChatMessage['xai'],
    })));
    setCurrentView('analyze');
    await refreshSidebar();
  };

  const handleUpload = async (file: File) => {
    const token = nextRequestToken();
    setUploadStatus(`Uploading file: ${file.name}...`);
    const uploadMessageId = crypto.randomUUID();
    let progressHandle: ProgressStreamHandle | null = null;
    try {
      const backendReady = await refreshBackendStatus();
      if (!backendReady) {
        throw new Error(backendUnavailableMessage());
      }
      const sessionId = currentSessionId || (await createSession()).id;
      if (isStaleRequest(token)) return;
      setCurrentSessionId(sessionId);

      setMessages((current) => [
        ...current,
        {
          id: uploadMessageId,
          role: 'assistant',
          content: `Working on ${file.name}…`,
          liveSteps: [],
          isLoading: true,
        },
      ]);

      progressHandle = openProgressStream(
        sessionId,
        (event: ProgressEvent) => {
          if (isStaleRequest(token)) return;
          setMessages((current) => current.map((msg) => (
            msg.id === uploadMessageId
              ? { ...msg, liveSteps: reduceProgress(msg.liveSteps ?? [], event) }
              : msg
          )));
        },
      );

      setUploadStatus(`Parsing dataset and profiling columns: ${file.name}...`);
      const uploaded = await uploadDataset(file, sessionId, { autoAnalyze: false, generateReport: false, runXai: false });
      if (isStaleRequest(token)) return;
      const nextDataset = { ...uploaded, originalFileSize: file.size };
      setDataset(nextDataset);
      setUploadStatus(`Uploaded to backend: ${file.name}. Starting analysis...`);
      const systemMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'system',
        content: `${uploaded.dataset_filename || file.name} is ready: ${formatNumber(uploaded.dataset_rows)} rows, ${formatNumber(uploaded.dataset_cols)} columns, ${datasetTypeLabel(nextDataset)} dataset type.`,
      };
      setMessages((current) => [...current, systemMessage]);
      await refreshSidebar();
      void runAnalysis(
        sessionId,
        uploaded.dataset_id,
        'Generate a full analysis report with charts, business metrics, prediction readiness, XAI, recommendations, and limitations.',
        {
          addUserMessage: false,
          loadingText: 'Running full analysis…',
          onCompleteStatus: `Analysis complete: ${file.name}`,
          reuseMessageId: uploadMessageId,
          progressHandle,
        },
      );
      progressHandle = null;
    } catch (error) {
      progressHandle?.close();
      if (isStaleRequest(token)) return;
      if (isBackendConnectionError(error)) setBackendStatus('disconnected');
      const message = error instanceof Error ? error.message : 'Upload failed';
      setUploadStatus(message);
      setMessages((current) => current.map((msg) => (
        msg.id === uploadMessageId
          ? { ...msg, content: `Upload failed: ${message}`, isLoading: false }
          : msg
      )));
    }
  };

  const runAnalysis = async (
    sessionId: string,
    datasetId: string,
    query: string,
    options: {
      addUserMessage?: boolean;
      loadingText?: string;
      initialEvents?: ChatEvent[];
      onCompleteStatus?: string;
      reuseMessageId?: string;
      progressHandle?: ProgressStreamHandle | null;
    } = {},
  ) => {
    const token = nextRequestToken();
    const assistantId = options.reuseMessageId ?? crypto.randomUUID();
    setCurrentView('analyze');
    setIsQuerying(true);
    setMessages((current) => {
      if (options.reuseMessageId) {
        return current.map((msg) => (
          msg.id === assistantId
            ? { ...msg, content: options.loadingText || msg.content, isLoading: true }
            : msg
        ));
      }
      return [
        ...current,
        ...(options.addUserMessage === false ? [] : [{ id: crypto.randomUUID(), role: 'user' as const, content: query }]),
        {
          id: assistantId,
          role: 'assistant' as const,
          content: options.loadingText || 'Running analysis…',
          liveSteps: [] as ThinkingStep[],
          events: options.initialEvents,
          isLoading: true,
        },
      ];
    });

    let progressHandle: ProgressStreamHandle | null = options.progressHandle ?? null;
    if (!progressHandle) {
      progressHandle = openProgressStream(
        sessionId,
        (event: ProgressEvent) => {
          if (isStaleRequest(token)) return;
          setMessages((current) => current.map((msg) => (
            msg.id === assistantId
              ? { ...msg, liveSteps: reduceProgress(msg.liveSteps ?? [], event) }
              : msg
          )));
        },
      );
    }

    try {
      const backendReady = await refreshBackendStatus();
      if (!backendReady) {
        throw new Error(backendUnavailableMessage());
      }
      const result = await analyzeSession(sessionId, datasetId, query);
      if (isStaleRequest(token)) return;
      setMessages((current) => current.map((message) => (
        message.id === assistantId
          ? {
              ...message,
              content: result.answer || 'Analysis complete.',
              events: (result.agents ?? []).flatMap((agent) => [
                { step: agent.name, message: `${agent.name}: ${agent.status}${agent.summary ? ` - ${agent.summary}` : ''}` },
                ...(agent.steps ?? []).map((step) => ({
                  step: agent.name,
                  message: `${agent.name} / ${step.name}: ${step.status}`,
                })),
              ]),
              kpis: result.kpis,
              auditTrail: result.audit_trail,
              qualityDoctor: result.quality_doctor,
              tables: result.tables,
              charts: result.charts,
              recommendations: result.recommendations,
              report: result.report,
              xai: result.xai as ChatMessage['xai'],
              narrationProvider: result.narration_provider,
              isLoading: false,
            }
          : message
      )));
      if (options.onCompleteStatus) {
        setUploadStatus(options.onCompleteStatus);
      }
      await refreshSidebar();
    } catch (error) {
      if (isStaleRequest(token)) return;
      if (isBackendConnectionError(error)) setBackendStatus('disconnected');
      const message = error instanceof Error ? error.message : 'Analysis failed';
      setMessages((current) => current.map((item) => (
        item.id === assistantId
          ? { ...item, content: `Analysis failed: ${message}`, events: [{ step: 'error', message }], isLoading: false }
          : item
      )));
    } finally {
      progressHandle?.close();
      if (!isStaleRequest(token)) setIsQuerying(false);
    }
  };

  const handleSubmit = async (query: string) => {
    if (!dataset || !currentSessionId) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Please upload a CSV or Excel dataset first, then I can analyze it through the backend.',
        },
      ]);
      setCurrentView('analyze');
      return;
    }

    const token = nextRequestToken();
    const sessionId = currentSessionId;
    const assistantId = crypto.randomUUID();
    setCurrentView('analyze');
    setIsQuerying(true);
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: 'user', content: query },
      {
        id: assistantId,
        role: 'assistant',
        content: 'Running backend analysis...',
        events: [],
        liveSteps: [],
        isLoading: true,
      },
    ]);

    const progressHandle = openProgressStream(
      sessionId,
      (event: ProgressEvent) => {
        if (isStaleRequest(token)) return;
        setMessages((current) => current.map((msg) => (
          msg.id === assistantId
            ? { ...msg, liveSteps: reduceProgress(msg.liveSteps ?? [], event) }
            : msg
        )));
      },
    );

    try {
      const backendReady = await refreshBackendStatus();
      if (!backendReady) {
        throw new Error(backendUnavailableMessage());
      }
      const events = await streamQuery(sessionId, query, dataset.dataset_id, (event) => {
        if (isStaleRequest(token)) return;
        setMessages((current) => current.map((message) => {
          if (message.id !== assistantId) {
            return message;
          }

          const nextTables = event.table
            ? [...(message.tables ?? []), event.table]
            : message.tables;
          const nextCharts = event.chart
            ? [...(message.charts ?? []), event.chart]
            : message.charts;
          const nextRecommendations = event.recommendations ?? message.recommendations;

          return {
            ...message,
            content: event.step === 'narration' || event.step === 'error' ? event.message : message.content,
            events: [...(message.events ?? []), event],
            tables: nextTables,
            charts: nextCharts,
            recommendations: nextRecommendations,
            suggestions: event.suggestions ?? message.suggestions,
          };
        }));
      });
      if (isStaleRequest(token)) return;

      const narrative = [...events].reverse().find((event) => event.step === 'narration')?.message;
      setMessages((current) => current.map((message) => (
        message.id === assistantId
          ? { ...message, content: narrative || message.content || 'Analysis complete.', isLoading: false }
          : message
      )));
      const detail = await getSession(sessionId);
      if (isStaleRequest(token)) return;
      const lastAssistant = [...detail.messages].reverse().find((item) => item.role === 'assistant');
      if (lastAssistant) {
        setMessages((current) => current.map((message) => (
          message.id === assistantId
            ? {
                ...message,
                report: lastAssistant.payload?.report as ChatMessage['report'],
                kpis: lastAssistant.payload?.kpis as ChatMessage['kpis'],
                auditTrail: lastAssistant.payload?.audit_trail as ChatMessage['auditTrail'],
                qualityDoctor: lastAssistant.payload?.quality_doctor as ChatMessage['qualityDoctor'],
                charts: lastAssistant.payload?.charts as ChartPayload[] | undefined,
                tables: lastAssistant.payload?.tables as TablePayload[] | undefined,
                recommendations: lastAssistant.payload?.recommendations as string[] | undefined,
                xai: lastAssistant.payload?.xai as ChatMessage['xai'],
              }
            : message
        )));
      }
      await refreshSidebar();
    } catch (error) {
      if (isStaleRequest(token)) return;
      if (isBackendConnectionError(error)) setBackendStatus('disconnected');
      const message = error instanceof Error ? error.message : 'Analysis failed';
      setMessages((current) => current.map((item) => (
        item.id === assistantId
          ? { ...item, content: `Analysis failed: ${message}`, isLoading: false }
          : item
      )));
    } finally {
      progressHandle?.close();
      if (!isStaleRequest(token)) setIsQuerying(false);
    }
  };

  const handleApplyFixes = async (fixIds: string[]) => {
    if (!dataset || !currentSessionId || !fixIds.length || isCleaning) return;
    setIsCleaning(true);
    const token = nextRequestToken();
    const sessionId = currentSessionId;
    const datasetId = dataset.dataset_id;
    const assistantId = crypto.randomUUID();
    setCurrentView('analyze');
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: 'user', content: `Apply ${fixIds.length} data quality fix${fixIds.length === 1 ? '' : 'es'}` },
      { id: assistantId, role: 'assistant', content: 'Cleaning the dataset and re-analyzing…', events: [], liveSteps: [], isLoading: true },
    ]);
    try {
      const result = await cleanDataset(sessionId, datasetId, fixIds);
      if (isStaleRequest(token)) return;
      const summary = result.cleaning_summary;
      const content = summary
        ? `**Dataset cleaned.** Applied ${summary.applied.length} fix(es):\n\n- ${summary.applied.join('\n- ')}\n\nRows ${summary.before.rows} → ${summary.after.rows} · columns ${summary.before.columns} → ${summary.after.columns} · missing cells ${summary.before.missing_cells} → ${summary.after.missing_cells}.\n\n${result.answer || ''}`
        : (result.answer || 'Dataset cleaned.');
      setMessages((current) => current.map((message) => (
        message.id === assistantId
          ? {
              ...message,
              content,
              kpis: result.kpis,
              auditTrail: result.audit_trail,
              qualityDoctor: result.quality_doctor,
              tables: result.tables,
              charts: result.charts,
              recommendations: result.recommendations,
              xai: result.xai as ChatMessage['xai'],
              narrationProvider: result.narration_provider,
              isLoading: false,
            }
          : message
      )));
      await refreshSidebar();
    } catch (error) {
      if (isStaleRequest(token)) return;
      const message = error instanceof Error ? error.message : 'Cleaning failed';
      setMessages((current) => current.map((item) => (
        item.id === assistantId ? { ...item, content: `Cleaning failed: ${message}`, isLoading: false } : item
      )));
    } finally {
      if (!isStaleRequest(token)) setIsCleaning(false);
    }
  };

  const handleRenarrate = async (messageId: string, reportId: string) => {
    if (!currentSessionId) {
      setUploadStatus('No active session for re-narration');
      return;
    }
    setUploadStatus('Re-narrating with GPT…');
    try {
      const refreshed = await renarrateReport(currentSessionId, reportId);
      setMessages((current) => current.map((m) => (
        m.id === messageId
          ? {
              ...m,
              report: {
                report_id: refreshed.report_id,
                html_url: refreshed.html_url,
                pdf_url: refreshed.pdf_url,
              },
              narrationProvider: refreshed.narration_provider || m.narrationProvider,
            }
          : m
      )));
      setUploadStatus(`Report re-narrated (${refreshed.narration_provider || 'llm'})`);
    } catch (error) {
      setUploadStatus(error instanceof Error ? error.message : 'Re-narration failed');
    }
  };

  const handleCopyAsMarkdown = (message: ChatMessage) => {
    const lines = [
      `# ${dataset?.dataset_filename || 'Analysis'}`,
      '',
      message.content,
    ];
    if (message.recommendations?.length) {
      lines.push('', '## Recommendations', ...message.recommendations.map((r) => `- ${r}`));
    }
    if (message.kpis?.length) {
      lines.push('', '## KPIs');
      for (const kpi of message.kpis) {
        lines.push(`- **${kpi.label}**: ${kpi.value ?? '—'}`);
      }
    }
    void navigator.clipboard.writeText(lines.join('\n'));
    setUploadStatus('Copied analysis to clipboard');
  };

  const hasReport = messages.some((m) => m.role === 'assistant' && (m.report?.html_url || m.xai?.plain_english_explanation));

  const handleSignOut = () => {
    signOut();
    router.push('/');
  };

  return (
    <div className="flex h-screen w-full bg-[#F8FAFC] text-[#0F172A] font-sans overflow-hidden">

      {/* --- Mobile Sidebar Backdrop --- */}
      {isMobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-[#0F172A]/40 z-40 md:hidden"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      {/* --- Desktop & Mobile Sidebar --- */}
      <aside className={`bg-[#FFFFFF] w-[280px] h-full rounded-r-2xl border-r border-[#E2E8F0]/30 shadow-2xl flex-col py-6 shrink-0 z-50 md:flex md:relative ${isMobileSidebarOpen ? 'flex fixed inset-y-0 left-0' : 'hidden'}`}>
        <div className="px-6 mb-6 mt-2">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center text-white text-sm font-bold shadow-inner">
              {userInitials || 'GA'}
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-[#0F172A] tracking-wide truncate">{session?.name || 'Guest Analyst'}</h2>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[10px] font-medium text-[#64748B] bg-[#E2E8F0] px-2 py-0.5 rounded-full truncate max-w-[160px]">
                  {session?.guest ? 'Guest Mode' : session?.email || (currentSessionId ? `Session ${currentSessionId.slice(0, 8)}` : 'Signed in')}
                </span>
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto space-y-6 px-3 pb-4 sidebar-scrollbar">

          <div className="space-y-1">
            <button
              onClick={() => { setCurrentView('analyze'); setIsMobileSidebarOpen(false); }}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 ${currentView === 'analyze' ? 'bg-violet-500/15 text-violet-600 font-medium' : 'text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A]'}`}
            >
              <Bot size={18} />
              <span className="text-sm">Analyze Workspace</span>
            </button>
            <button
              onClick={() => { if (hasReport) { setCurrentView('report'); setIsMobileSidebarOpen(false); } }}
              disabled={!hasReport}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 ${!hasReport ? 'opacity-40 cursor-not-allowed text-[#94A3B8]' : currentView === 'report' ? 'bg-violet-500/15 text-violet-600 font-medium' : 'text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A]'}`}
            >
              <FileText size={18} />
              <span className="text-sm">Report & XAI Page</span>
            </button>
            <Link
              href="/"
              className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A] transition-all duration-200"
            >
              <Home size={18} />
              <span className="text-sm">Back to Home</span>
            </Link>
          </div>

          {recentDatasets.length > 0 && (
            <div>
               <div className="px-4 text-[11px] font-semibold text-[#64748B] uppercase tracking-wider mb-2">
                  Recent Datasets
               </div>
               <div className="space-y-1">
                  {recentDatasets.slice(0, 5).map((item) => (
                    <button
                      key={item.id}
                      onClick={() => loadSession(item.session_id)}
                      className="w-full flex items-center gap-3 px-4 py-2 rounded-xl text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A] transition-all text-sm group"
                    >
                       <Table size={16} className="text-violet-400/70 group-hover:text-violet-400 shrink-0"/>
                       <span className="truncate text-left">{item.filename}</span>
                    </button>
                  ))}
               </div>
            </div>
          )}
        </nav>

        <div className="px-4 mt-auto border-t border-[#E2E8F0]/30 pt-4 space-y-1">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A] transition-all duration-200 text-sm font-semibold"
          >
            <History size={18} />
            <span>Reset Workspace</span>
          </button>
          <button
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-rose-500 hover:bg-rose-50 transition-all duration-200 text-sm font-semibold"
          >
            <LogOut size={18} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col relative h-full min-w-0">

        {/* --- Top Header Overlay --- */}
        <header className="absolute top-0 w-full z-40 bg-[#F8FAFC]/70 backdrop-blur-xl border-b border-[#E2E8F0]/30 shadow-sm flex items-center justify-between px-4 md:px-8 h-16">
          <div className="flex items-center gap-4">
            <button onClick={() => setIsMobileSidebarOpen(true)} className="md:hidden text-[#64748B] hover:text-[#0F172A]">
              <Menu size={24} />
            </button>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-500 to-blue-500">DataVerse AI</h1>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-8">
             <button onClick={() => setCurrentView('analyze')} className={`text-sm font-medium transition-colors relative ${currentView === 'analyze' ? 'text-violet-500' : 'text-[#64748B] hover:text-[#0F172A]'}`}>
                Workspace
                {currentView === 'analyze' && <span className="absolute -bottom-5 left-0 w-full h-[2px] bg-violet-500 rounded-t-full shadow-[0_0_10px_rgba(139,92,246,0.8)]"></span>}
             </button>
             <button
                onClick={() => { if (hasReport) setCurrentView('report'); }}
                disabled={!hasReport}
                className={`text-sm font-medium transition-colors relative ${!hasReport ? 'opacity-40 cursor-not-allowed' : currentView === 'report' ? 'text-violet-500' : 'text-[#64748B] hover:text-[#0F172A]'}`}
             >
                Report & XAI
                {currentView === 'report' && <span className="absolute -bottom-5 left-0 w-full h-[2px] bg-violet-500 rounded-t-full shadow-[0_0_10px_rgba(139,92,246,0.8)]"></span>}
             </button>
          </nav>
        </header>

        {/* --- Main Content Area --- */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentView}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full flex flex-col"
          >
            {currentView === 'analyze' && (
              <AnalyzeWorkspaceView
                dataset={dataset}
                uploadStatus={uploadStatus}
                backendStatus={backendStatus}
                isQuerying={isQuerying}
                messages={messages}
                recentDatasets={recentDatasets}
                onUpload={handleUpload}
                onSubmit={handleSubmit}
                onNavigateToReport={() => setCurrentView('report')}
                onSelectRecentDataset={loadSession}
                onRenarrate={handleRenarrate}
                onCopyAsMarkdown={handleCopyAsMarkdown}
                onApplyFixes={handleApplyFixes}
                isCleaning={isCleaning}
              />
            )}
            {currentView === 'report' && (
              <ReportXAIPageView
                dataset={dataset}
                messages={messages}
              />
            )}
          </motion.div>
        </AnimatePresence>

        {/* --- Mobile Bottom Nav --- */}
        <nav className="md:hidden fixed bottom-6 left-1/2 -translate-x-1/2 w-[calc(100%-32px)] max-w-sm rounded-[2rem] z-50 bg-[#FFFFFF]/90 backdrop-blur-2xl border border-[#E2E8F0]/50 shadow-[0px_8px_32px_rgba(109,59,215,0.08)] flex items-center justify-between px-2 py-2">
           <Link href="/" className="p-3.5 rounded-full transition-all duration-300 flex items-center justify-center text-[#64748B] hover:text-[#0F172A]">
              <Home size={20} />
           </Link>
           <button onClick={() => setCurrentView('analyze')} className={`p-3.5 rounded-full transition-all duration-300 flex items-center justify-center ${currentView === 'analyze' ? 'bg-gradient-to-r from-violet-500 to-blue-500 text-white shadow-lg scale-105' : 'text-[#64748B] hover:text-[#0F172A]'}`}>
              <Bot size={20} />
           </button>
           <button
              onClick={() => { if (hasReport) setCurrentView('report'); }}
              disabled={!hasReport}
              className={`p-3.5 rounded-full transition-all duration-300 flex items-center justify-center ${!hasReport ? 'opacity-30 cursor-not-allowed text-gray-300' : currentView === 'report' ? 'bg-gradient-to-r from-violet-500 to-blue-500 text-white shadow-lg scale-105' : 'text-[#64748B] hover:text-[#0F172A]'}`}
           >
              <FileText size={20} />
           </button>
        </nav>

      </div>
    </div>
  );
}
