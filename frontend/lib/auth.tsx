'use client';

/**
 * Real authentication for DataVerse AI.
 *
 * Sign up / log in / continue-as-guest call the backend auth API, which returns
 * a signed JWT. The token is stored in localStorage and sent as a Bearer header
 * on every API request (see dataverse-api.ts), so the server can enforce
 * per-user data ownership. The stored session is derived from the verified user.
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { API_BASE_URL } from './apiConfig';

const STORAGE_KEY = 'dataverse.session';
const TOKEN_KEY = 'dataverse.token';

export type AuthSession = {
  name: string;
  email: string | null;
  guest: boolean;
  createdAt: string;
};

type Credentials = { email: string; password: string; name?: string };

type AuthContextValue = {
  session: AuthSession | null;
  loading: boolean;
  signIn: (input: Credentials) => Promise<AuthSession>;
  signUp: (input: Credentials & { name: string }) => Promise<AuthSession>;
  continueAsGuest: () => Promise<AuthSession>;
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
  user: { id: string; email: string | null; name: string; guest: boolean };
};

async function authRequest(path: string, body?: Record<string, unknown>): Promise<AuthApiResponse> {
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
  return (await res.json()) as AuthApiResponse;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSession(readSession());
    setLoading(false);
  }, []);

  const commit = useCallback((response: AuthApiResponse): AuthSession => {
    persistToken(response.token);
    const next: AuthSession = {
      name: response.user.name,
      email: response.user.email,
      guest: response.user.guest,
      createdAt: new Date().toISOString(),
    };
    writeSession(next);
    setSession(next);
    return next;
  }, []);

  const signIn = useCallback<AuthContextValue['signIn']>(async ({ email, password }) => {
    return commit(await authRequest('/auth/login', { email: email.trim(), password }));
  }, [commit]);

  const signUp = useCallback<AuthContextValue['signUp']>(async ({ name, email, password }) => {
    return commit(await authRequest('/auth/signup', { name: name.trim(), email: email.trim(), password }));
  }, [commit]);

  const continueAsGuest = useCallback<AuthContextValue['continueAsGuest']>(async () => {
    return commit(await authRequest('/auth/guest'));
  }, [commit]);

  const signOut = useCallback(() => {
    persistToken(null);
    writeSession(null);
    setSession(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ session, loading, signIn, signUp, continueAsGuest, signOut }),
    [session, loading, signIn, signUp, continueAsGuest, signOut],
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
