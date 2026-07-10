'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { DashboardApp } from '@/components/dashboard/DashboardApp';

export default function DashboardPage() {
  const router = useRouter();
  const { session, loading } = useAuth();

  useEffect(() => {
    if (!loading && !session) {
      router.replace('/login');
    }
  }, [loading, session, router]);

  if (loading || !session) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#F8FAFC]">
        <div className="flex flex-col items-center gap-3 text-[#64748B]">
          <Loader2 size={28} className="animate-spin text-violet-500" />
          <p className="text-sm">Preparing your workspace…</p>
        </div>
      </div>
    );
  }

  return <DashboardApp />;
}
