'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowRight, MailCheck } from 'lucide-react';
import { AuthShell } from '@/components/site/AuthShell';
import { useAuth, isValidEmail } from '@/lib/auth';

export default function SignupPage() {
  const { signUp, resendSignupConfirmation } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [verificationEmail, setVerificationEmail] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (name.trim().length < 2) {
      setError('Enter your name.');
      return;
    }
    if (!isValidEmail(email)) {
      setError('Enter a valid email address.');
      return;
    }
    if (password.length < 12) {
      setError('Password must be at least 12 characters.');
      return;
    }
    if (!/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/\d/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
      setError('Use uppercase, lowercase, a number, and a special character.');
      return;
    }
    setBusy(true);
    try {
      const result = await signUp({ name, email, password });
      setVerificationEmail(result.email);
      setPassword('');
      setNotice(`We sent a confirmation link to ${result.email}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create your account.');
    } finally {
      setBusy(false);
    }
  };

  const handleResend = async () => {
    if (!verificationEmail) return;
    setBusy(true);
    setError(null);
    try {
      await resendSignupConfirmation(verificationEmail);
      setNotice('A new confirmation link was sent.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not resend the confirmation link.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Create your workspace" subtitle="Sign up to start analysing datasets.">
      {verificationEmail ? (
        <div className="space-y-4">
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">
            <MailCheck className="mb-2" size={22} />
            Open the email sent to <span className="font-semibold">{verificationEmail}</span> and click the confirmation link. You can then log in securely.
          </div>
          {notice && <p className="text-sm text-emerald-700">{notice}</p>}
          {error && <p role="alert" className="text-sm text-rose-600">{error}</p>}
          <button
            type="button"
            onClick={handleResend}
            disabled={busy}
            className="w-full text-sm font-semibold text-violet-600 hover:text-violet-700 disabled:opacity-60"
          >
            Resend confirmation link
          </button>
          <Link
            href="/login"
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:brightness-110"
          >
            Go to login <ArrowRight size={16} />
          </Link>
        </div>
      ) : (
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[#334155]">Full name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => { setName(e.target.value); setError(null); }}
            placeholder="Alex Analyst"
            className="w-full rounded-xl border border-[#E2E8F0] bg-white px-4 py-2.5 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-500/20"
            autoComplete="name"
          />
        </div>
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
            placeholder="At least 12 characters"
            className="w-full rounded-xl border border-[#E2E8F0] bg-white px-4 py-2.5 text-sm outline-none transition focus:border-violet-400 focus:ring-2 focus:ring-violet-500/20"
            autoComplete="new-password"
          />
        </div>

        {error && <p role="alert" className="text-sm text-rose-600">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-500 to-blue-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:brightness-110 active:scale-95 disabled:opacity-60"
        >
          Create account <ArrowRight size={16} />
        </button>
      </form>
      )}

      <p className="mt-6 text-center text-sm text-[#64748B]">
        Already have an account?{' '}
        <Link href="/login" className="font-semibold text-violet-600 hover:text-violet-700">
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}
