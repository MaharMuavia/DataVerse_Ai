'use client';

import React, { useCallback, useState } from 'react';
import { AlertTriangle, CloudUpload, FileSpreadsheet, Loader2 } from 'lucide-react';

const ACCEPTED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];

function hasAcceptedExtension(name: string): boolean {
  const lower = name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function formatBytes(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

type Props = {
  isUploading: boolean;
  uploadStatus: string | null;
  backendStatus: 'checking' | 'connected' | 'disconnected';
  onUpload: (file: File) => void;
};

export function DropZone({ isUploading, uploadStatus, backendStatus, onUpload }: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const [rejectionReason, setRejectionReason] = useState<string | null>(null);

  const validateAndUpload = useCallback(
    (file: File | undefined) => {
      if (!file) return;
      if (!hasAcceptedExtension(file.name)) {
        setRejectionReason(`Only ${ACCEPTED_EXTENSIONS.join(', ')} files are supported.`);
        return;
      }
      setRejectionReason(null);
      onUpload(file);
    },
    [onUpload],
  );

  const onDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!isUploading) setIsDragging(true);
  }, [isUploading]);

  const onDragLeave = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragging(false);
      if (isUploading) return;
      const file = event.dataTransfer.files?.[0];
      validateAndUpload(file);
    },
    [isUploading, validateAndUpload],
  );

  const disconnected = backendStatus === 'disconnected';

  return (
    <div
      onDragOver={onDragOver}
      onDragEnter={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={`rounded-2xl border-2 border-dashed transition-all p-10 flex flex-col items-center justify-center text-center animate-fade-in ${
        isDragging
          ? 'border-violet-500 bg-violet-50/60 scale-[1.01]'
          : disconnected
          ? 'border-rose-300 bg-rose-50/40'
          : 'border-[#E2E8F0] bg-white'
      }`}
    >
      {isUploading ? (
        <div className="flex flex-col items-center py-6">
          <Loader2 size={36} className="animate-spin text-violet-500 mb-3" />
          <h3 className="text-lg font-semibold text-[#0F172A]">Processing dataset</h3>
          <p className="text-sm text-[#64748B] mt-2 max-w-sm">
            {uploadStatus || 'Uploading…'}
          </p>
        </div>
      ) : (
        <>
          <div
            className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 border ${
              isDragging
                ? 'bg-violet-100 border-violet-200'
                : 'bg-violet-50 border-violet-100'
            }`}
          >
            <CloudUpload
              size={32}
              className={isDragging ? 'text-violet-700' : 'text-violet-500'}
            />
          </div>
          <h2 className="text-xl font-bold text-[#0F172A] mb-2">
            {isDragging ? 'Drop the file to upload' : 'Upload a dataset to start'}
          </h2>
          <p className="text-sm text-[#64748B] max-w-md mb-6 leading-relaxed">
            Drop a CSV or Excel file here, or pick one from your computer. The system will profile
            columns, check data quality, and produce a concise business report.
          </p>
          <label
            className={`px-6 py-3 rounded-xl text-sm font-semibold transition-all cursor-pointer shadow-lg shadow-violet-500/20 inline-flex items-center gap-2 ${
              disconnected
                ? 'bg-slate-300 text-white cursor-not-allowed'
                : 'bg-gradient-to-r from-violet-500 to-blue-500 text-white hover:brightness-110 active:scale-95'
            }`}
          >
            <FileSpreadsheet size={16} /> Select file
            <input
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(',')}
              className="hidden"
              disabled={disconnected}
              onChange={(event) => {
                validateAndUpload(event.target.files?.[0]);
                event.target.value = '';
              }}
            />
          </label>
          <p className="text-[11px] text-[#94A3B8] mt-3">
            Accepted: {ACCEPTED_EXTENSIONS.join(', ')} · up to a few hundred MB
          </p>
          {rejectionReason && (
            <p className="text-xs text-rose-600 mt-3 flex items-center gap-1.5">
              <AlertTriangle size={12} /> {rejectionReason}
            </p>
          )}
          {disconnected && (
            <p className="text-xs text-rose-600 mt-3 flex items-center gap-1.5">
              <AlertTriangle size={12} /> Backend is not reachable. Start FastAPI on port 8000 to upload.
            </p>
          )}
        </>
      )}
      {!isUploading && uploadStatus && !rejectionReason && !disconnected && (
        <p className="text-[11px] text-[#64748B] mt-3 max-w-md">
          {uploadStatus.length > 200 ? `${uploadStatus.slice(0, 200)}…` : uploadStatus} · most
          recent file: {formatRecentSize(uploadStatus)}
        </p>
      )}
    </div>
  );
}

function formatRecentSize(status: string | null): string {
  if (!status) return 'N/A';
  const match = status.match(/(\d+(?:\.\d+)?)\s*(B|KB|MB|GB)/i);
  if (!match) return 'N/A';
  return `${match[1]} ${match[2].toUpperCase()}`;
}

// Exported so consumers can format dataset previews consistently.
export { formatBytes };
