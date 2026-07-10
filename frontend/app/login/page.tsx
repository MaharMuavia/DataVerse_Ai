'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowRight, UserRound } from 'lucide-react';
import { AuthShell } from '@/components/site/AuthShell';
import { useAuth, isValidEmail } from '@/lib/auth';

export default function LoginPage() {
  const router = useRouter();
  const { signIn, continueAsGuest } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!isValidEmail(email)) {
      setError('Enter a valid email address.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setBusy(true);
    try {
      await signIn({ email, password });
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid email or password.');
    } finally {
      setBusy(false);
    }
  };

  const handleGuest = async () => {
    setBusy(true);
    try {
      await continueAsGuest();
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start a guest session.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Welcome back" subtitle="Log in to open your analysis workspace.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[#334155]">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setError(null); }}
            placeholder="you@company.com"
            className="w-full rounded-xl border border-[#E2E8F0] bg-white px-4 py-2.5 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-500/20"
            autoComplete="email"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[#334155]">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(null); }}
            placeholder="••••••••"
            className="w-full rounded-xl border border-[#E2E8F0] bg-white px-4 py-2.5 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-500/20"
            autoComplete="current-password"
          />
        </div>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:brightness-110 active:scale-95 disabled:opacity-60"
        >
          Log in <ArrowRight size={16} />
        </button>
      </form>

      <div className="my-5 flex items-center gap-3 text-xs text-[#94A3B8]">
        <span className="h-px flex-1 bg-[#E2E8F0]" /> or <span className="h-px flex-1 bg-[#E2E8F0]" />
      </div>

      <button
        onClick={handleGuest}
        disabled={busy}
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-4 py-2.5 text-sm font-semibold text-[#334155] transition-colors hover:bg-[#F1F5F9] disabled:opacity-60"
      >
        <UserRound size={16} /> Continue as guest
      </button>

      <p className="mt-6 text-center text-sm text-[#64748B]">
        New here?{' '}
        <Link href="/signup" className="font-semibold text-violet-600 hover:text-violet-700">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}
