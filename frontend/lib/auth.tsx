'use client';

/**
 * Real authentication for DataVerse AI.
 *
 * Signup requires confirmation through Supabase's email link. Authenticated
 * access tokens are stored and sent as Bearer headers so the server can enforce
 * per-user data ownership.
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { API_BASE_URL } from './apiConfig';

const STORAGE_KEY = 'dataverse.session';
const TOKEN_KEY = 'dataverse.token';
const REFRESH_TOKEN_KEY = 'dataverse.refreshToken';
const ALLOW_ANONYMOUS_WORKSPACE = process.env.NODE_ENV !== 'production';

export type AuthSession = {
  name: string;
  email: string | null;
  createdAt: string;
};

type Credentials = { email: string; password: string; name?: string };

type AuthContextValue = {
  session: AuthSession | null;
  loading: boolean;
  signIn: (input: Credentials) => Promise<AuthSession>;
  signUp: (input: Credentials & { name: string }) => Promise<{ email: string }>;
  resendSignupConfirmation: (email: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const readSession = (): AuthSession | null => {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthSession;
    if (!parsed || typeof parsed.name !== 'string') return null;
    return parsed;
  } catch {
    return null;
  }
};

const persistToken = (token: string | null) => {
  if (typeof window === 'undefined') return;
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage may be unavailable */
  }
};

const writeSession = (session: AuthSession | null) => {
  if (typeof window === 'undefined') return;
  try {
    if (session) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage may be unavailable */
  }
};

export const isValidEmail = (email: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

type AuthApiResponse = {
  token: string;
  refresh_token?: string | null;
  expires_in?: number | null;
  user: { id: string; email: string | null; name: string; guest: boolean };
};

const createAnonymousSession = (): AuthSession => ({
  name: 'Guest',
  email: null,
  createdAt: new Date().toISOString(),
});

const persistRefreshToken = (token: string | null) => {
  if (typeof window === 'undefined') return;
  try {
    if (token) window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
    else window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    /* storage may be unavailable */
  }
};

async function authRequest<T>(path: string, body?: Record<string, unknown>): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    // ngrok-skip-browser-warning: ngrok's free tier intercepts browser
    // requests with an HTML warning page unless this header is present.
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '1' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = 'Authentication failed';
    try {
      detail = (await res.json())?.detail || detail;
    } catch {
      /* non-JSON error */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);

  const commit = useCallback((response: AuthApiResponse): AuthSession => {
    persistToken(response.token);
    if (response.refresh_token) persistRefreshToken(response.refresh_token);
    const next: AuthSession = {
      name: response.user.name,
      email: response.user.email,
      createdAt: new Date().toISOString(),
    };
    writeSession(next);
    setSession(next);
    return next;
  }, []);

  useEffect(() => {
    let cancelled = false;
    const restore = async () => {
      const storedSession = readSession();
      const token = window.localStorage.getItem(TOKEN_KEY);
      const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
      if (!token) {
        if (storedSession) {
          if (!cancelled) setSession(storedSession);
          if (!cancelled) setLoading(false);
          return;
        }
        if (ALLOW_ANONYMOUS_WORKSPACE) {
          const anonymousSession = createAnonymousSession();
          writeSession(anonymousSession);
          if (!cancelled) setSession(anonymousSession);
          if (!cancelled) setLoading(false);
          return;
        }
        if (!cancelled) setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${token}`, 'ngrok-skip-browser-warning': '1' },
        });
        if (response.ok) {
          if (!cancelled) setSession(storedSession);
          return;
        }
        if (!refreshToken) throw new Error('Session expired');
        const refreshed = await authRequest<AuthApiResponse>('/auth/refresh', { refresh_token: refreshToken });
        if (!cancelled) commit(refreshed);
      } catch {
        persistToken(null);
        persistRefreshToken(null);
        writeSession(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void restore();
    return () => { cancelled = true; };
  }, [commit]);

  const signIn = useCallback<AuthContextValue['signIn']>(async ({ email, password }) => {
    return commit(await authRequest<AuthApiResponse>('/auth/login', { email: email.trim(), password }));
  }, [commit]);

  const signUp = useCallback<AuthContextValue['signUp']>(async ({ name, email, password }) => {
    return authRequest<{ email: string }>('/auth/signup', {
      name: name.trim(),
      email: email.trim(),
      password,
    });
  }, []);

  const resendSignupConfirmation = useCallback<AuthContextValue['resendSignupConfirmation']>(async (email) => {
    await authRequest<{ sent: boolean }>('/auth/resend-signup', { email: email.trim() });
  }, []);

  const signOut = useCallback(() => {
    persistToken(null);
    persistRefreshToken(null);
    writeSession(null);
    setSession(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ session, loading, signIn, signUp, resendSignupConfirmation, signOut }),
    [session, loading, signIn, signUp, resendSignupConfirmation, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
